"""
BudgetApp Telegram Bot - Main Application
Handles all user interactions and coordinates between modules
"""
import logging
import os
import time
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

from backend.app.core.settings import BOT_TOKEN, LOG_LEVEL, TEMP_PDF_FILENAME
from backend.app.repositories import db_repository as db
from backend.app.services import parser_service as parser

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL)
)

# Reduce noise from HTTP and Telegram internals
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ============================================================================
# TELEGRAM COMMAND HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the user and gives upload instructions."""
    await update.message.reply_text(
        "👋 Welcome! I am your Budget Bot.\n\n"
        "📎 **Available Commands:**\n"
        "• `/start` - Show this help message\n"
        "• `/analyze` - View monthly analysis by categories\n"
        "• _Send PDF or HTML_ - Upload your bank statement for parsing & approval\n\n"
        "💡 **How to use**: Just send your bank statement (PDF or HTML format) and I'll extract, show you the data, and wait for your approval before saving to database!"
    )


def summarize_transactions_preview(transactions, preview_size=2):
    """Return formatted preview lines for the first and last transactions."""
    if not transactions:
        return []

    total = len(transactions)
    if total <= preview_size * 2:
        return [parser.format_transaction_for_display(item) for item in transactions]

    preview = []
    for item in transactions[:preview_size]:
        preview.append(parser.format_transaction_for_display(item))

    for item in transactions[-preview_size:]:
        preview.append(parser.format_transaction_for_display(item))

    return preview


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process uploaded PDF file and extract transactions."""
    document = update.message.document
    
    # Verify the document is a PDF or HTML
    file_name_lower = document.file_name.lower()
    if not (file_name_lower.endswith('.pdf') or file_name_lower.endswith('.html') or file_name_lower.endswith('.htm')):
        await update.message.reply_text("❌ Please send a valid `.pdf` or `.html` document file.")
        return

    await update.message.reply_text("📥 Document received! Downloading and extracting data...")

    try:
        # Download document from Telegram
        tg_file = await context.bot.get_file(document.file_id)
        await tg_file.download_to_drive(custom_path=TEMP_PDF_FILENAME)
        
        # Determine file extension
        if file_name_lower.endswith('.pdf'):
            file_extension = 'pdf'
        else:
            file_extension = 'html'
        
        # Parse document (auto-detects PDF or HTML)
        parsed_data = parser.parse_file(TEMP_PDF_FILENAME)
        
        # Clean up temporary file
        if os.path.exists(TEMP_PDF_FILENAME):
            os.remove(TEMP_PDF_FILENAME)

        if not parsed_data:
            await update.message.reply_text("⚠️ No transactions found in this document.")
            return

        # Display extracted transactions preview
        response_lines = ["📋 **Extracted Statement Expenses:**\n"]
        stats = parser.get_transaction_statistics(parsed_data)

        response_lines.extend(summarize_transactions_preview(parsed_data, preview_size=2))
        
        response_lines.append(f"\n📊 **Rows Found**: {stats['count']}")
        response_lines.append(f"💰 **Total Sum**: {stats['total']:.2f} MDL")
        response_lines.append(f"📈 **Average**: {stats['average']:.2f} MDL")
        
        # Store pending transactions and file info in context
        context.user_data['pending_transactions'] = parsed_data
        context.user_data['upload_filename'] = document.file_name
        context.user_data['upload_extension'] = file_extension
        
        # Create approval buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve & Save", callback_data="approve_transactions"),
                InlineKeyboardButton("❌ Reject", callback_data="reject_transactions")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(response_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error processing PDF: {str(e)}")
        logger.error(f"PDF processing error: {str(e)}")

async def approve_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process approval and save transactions to database."""
    query = update.callback_query
    await query.answer()
    
    if 'pending_transactions' not in context.user_data:
        await query.edit_message_text("⚠️ No pending transactions found.")
        return
    
    pending_data = context.user_data['pending_transactions']
    filename = context.user_data.get('upload_filename', 'unknown')
    extension = context.user_data.get('upload_extension', 'unknown')
    
    conn = db.get_db_connection()
    
    if not conn:
        await query.edit_message_text("❌ Database connection failed!")
        return
    
    # Create or get audit_insert record
    audit_insert_id = db.get_or_create_audit_insert(conn, filename, extension)
    if not audit_insert_id:
        await query.edit_message_text("❌ Failed to create import audit record!")
        return
    
    duplicates = []
    inserted = []
    
    try:
        # Send initial processing message
        await query.edit_message_text(
            f"⏳ Processing {len(pending_data)} transactions...\n\n"
            f"0/{len(pending_data)} completed..."
        )
        
        for idx, transaction in enumerate(pending_data, 1):
            transaction['shop'] = db.sanitize_text(transaction.get('shop', ''))
            transaction['raw_text'] = db.sanitize_text(transaction.get('raw_text', ''))
            transaction_processing_date = transaction.get('processing_date') or transaction['date']

            # Check for duplicates
            if db.check_duplicate_transaction(
                conn,
                transaction['date'],
                transaction_processing_date,
                transaction['shop'],
                transaction['amount'],
                audit_insert_id,
                transaction['raw_text']
            ):
                duplicates.append(transaction)
                logger.info(f"⏭️  [{idx}/{len(pending_data)}] Skipped duplicate: {transaction['shop']}")
                
                # Update progress
                progress_msg = (
                    f"⏳ Processing {len(pending_data)} transactions...\n\n"
                    f"{idx}/{len(pending_data)} completed...\n"
                    f"✅ Inserted: {len(inserted)} | ⚠️ Duplicates: {len(duplicates)}"
                )
                
                try:
                    await query.edit_message_text(progress_msg)
                except Exception:
                    pass  # Skip if message didn't change
                continue
            
            # Find shop first by name or commercial name
            shop_id = db.find_shop_id(conn, transaction['shop'])
            if not shop_id:
                # Create shop if it doesn't exist
                shop_id = db.get_shop_id(conn, transaction['shop'])
                if not shop_id:
                    logger.warning(f"⏭️  [{idx}/{len(pending_data)}] Failed to create shop: {transaction['shop']}")
                    continue
            
            # Insert transaction (category will be determined via shops.default_category_id JOIN)
            tx_id = db.insert_transaction(
                conn,
                transaction['date'],
                transaction_processing_date,
                shop_id,
                audit_insert_id,
                transaction['amount'],
                transaction['raw_text'],
                currency=transaction.get('currency', 'MDL'),
                amount_original=transaction.get('amount_original'),
                amount_mdl=transaction.get('amount_mdl', transaction['amount'])
            )
            
            if tx_id:
                inserted.append(transaction)
                logger.info(f"✅ [{idx}/{len(pending_data)}] Inserted: {transaction['date']} | {transaction['shop']} | {transaction['amount']}")
            
            # Update progress message
            progress_msg = (
                f"⏳ Processing {len(pending_data)} transactions...\n\n"
                f"{idx}/{len(pending_data)} completed...\n"
                f"✅ Inserted: {len(inserted)} | ⚠️ Duplicates: {len(duplicates)}"
            )
            
            try:
                await query.edit_message_text(progress_msg)
            except Exception:
                pass  # Skip if message didn't change
        
        # Prepare final response (escape special characters for Markdown)
        response = ["✅ Transaction Processing Complete\n"]
        response.append(f"💾 Total Inserted: {len(inserted)} transactions")
        
        if inserted:
            response.append("\nInserted transactions:")
            for line in summarize_transactions_preview(inserted, preview_size=2):
                response.append(line)
        
        if duplicates:
            response.append(f"\n⚠️ Total Duplicates (skipped): {len(duplicates)}")
            if len(duplicates) <= 5:
                for tx in duplicates:
                    safe_shop = tx['shop'][:30].replace('_', ' ').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
                    response.append(f"  • {tx['date']} | {safe_shop} | {tx['amount']:.2f} MDL")
            else:
                response.append(f"  (showing first 5 of {len(duplicates)})")
                for tx in duplicates[:5]:
                    safe_shop = tx['shop'][:30].replace('_', ' ').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
                    response.append(f"  • {tx['date']} | {safe_shop} | {tx['amount']:.2f} MDL")
        
        # Clear pending data
        context.user_data.pop('pending_transactions', None)
        
        await query.edit_message_text(
            "\n".join(response),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error during transaction approval: {str(e)}")
        try:
            await query.edit_message_text(f"❌ Error saving transactions: {str(e)}")
        except Exception as e2:
            logger.error(f"Error sending error message: {str(e2)}")
    
    finally:
        db.close_connection(conn)

async def reject_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject the pending transactions."""
    query = update.callback_query
    await query.answer()
    
    context.user_data.pop('pending_transactions', None)
    await query.edit_message_text("❌ Transactions rejected and discarded.")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly analysis of transactions by categories."""
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    conn = db.get_db_connection()
    if not conn:
        await update.message.reply_text("❌ Database connection failed!")
        return
    
    try:
        periods = db.get_salary_cycle_periods(conn, today=date.today())
        current_start, current_end = periods['current']
        previous_start, previous_end = periods['previous']

        previous_analysis = db.get_analysis_for_period(conn, previous_start, previous_end)
        current_analysis = db.get_analysis_for_period(conn, current_start, current_end)

        if not previous_analysis and not current_analysis:
            await update.message.reply_text(
                f"📊 No transactions found between {previous_start} and {current_end}."
            )
            return

        def format_analysis_section(title, start_date, end_date, rows):
            section = [f"**{title}: {start_date} → {end_date}**"]
            if not rows:
                section.append("  • No transactions recorded")
                return section

            expense_total = 0.0
            income_total = 0.0
            for category_name, cat_type, count, total in rows:
                total_amount = float(total) if total else 0.0
                if cat_type == 'expense':
                    expense_total += total_amount
                else:
                    income_total += total_amount
                section.append(f"  • {category_name}: {count} transactions | {total_amount:.2f} MDL")

            section.append(f"  • Total Income: {income_total:.2f} MDL")
            section.append(f"  • Total Expenses: {expense_total:.2f} MDL")
            section.append(f"  • Net: {(income_total - expense_total):.2f} MDL")
            return section

        response = ["📊 **Salary-Day Based Analysis**\n"]
        response += format_analysis_section(
            "Previous salary cycle", previous_start, previous_end, previous_analysis
        )
        response.append("")
        response += format_analysis_section(
            "Current salary cycle", current_start, current_end, current_analysis
        )

        await update.message.reply_text(
            "\n".join(response),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in analyze command: {str(e)}")
        await update.message.reply_text(f"❌ Error analyzing data: {str(e)}")
    
    finally:
        db.close_connection(conn)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server started on http://0.0.0.0:{port}")
    return server


def main():
    start_health_server(8080)

    if not BOT_TOKEN:
        logger.error("Missing BOT_TOKEN variable! Bot polling is disabled until BOT_TOKEN is provided.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    
    # Callback query handlers for approval buttons
    app.add_handler(CallbackQueryHandler(approve_transactions, pattern="^approve_transactions$"))
    app.add_handler(CallbackQueryHandler(reject_transactions, pattern="^reject_transactions$"))
    
    # Message handler that triggers exclusively for Document attachments
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Bot engine listening for document uploads... Press Ctrl+C to terminate.")
    app.run_polling()

if __name__ == "__main__":
    main()

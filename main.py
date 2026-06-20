"""
BudgetApp Telegram Bot - Main Application
Handles all user interactions and coordinates between modules
"""
import logging
import os
import parser
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

import db
# Import modules
from config import BOT_TOKEN, LOG_LEVEL, TEMP_PDF_FILENAME

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL)
)
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
        
        # Parse document (auto-detects PDF or HTML)
        parsed_data = parser.parse_file(TEMP_PDF_FILENAME)
        
        # Clean up temporary file
        if os.path.exists(TEMP_PDF_FILENAME):
            os.remove(TEMP_PDF_FILENAME)

        if not parsed_data:
            await update.message.reply_text("⚠️ No transactions found in this document.")
            return

        # Display extracted transactions
        response_lines = ["📋 **Extracted Statement Expenses:**\n"]
        stats = parser.get_transaction_statistics(parsed_data)
        
        for item in parsed_data:
            response_lines.append(parser.format_transaction_for_display(item))
        
        response_lines.append(f"\n📊 **Rows Found**: {stats['count']}")
        response_lines.append(f"💰 **Total Sum**: {stats['total']:.2f} MDL")
        response_lines.append(f"📈 **Average**: {stats['average']:.2f} MDL")
        
        # Store pending transactions in context
        context.user_data['pending_transactions'] = parsed_data
        
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
    conn = db.get_db_connection()
    
    if not conn:
        await query.edit_message_text("❌ Database connection failed!")
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
            # Check for duplicates (by raw_text first, then by date+shop+amount)
            if db.check_duplicate_transaction(conn, transaction['date'], transaction['shop'], transaction['amount'], transaction['raw_text']):
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
            
            # Get or create shop
            shop_id = db.get_shop_id(conn, transaction['shop'])
            if not shop_id:
                logger.warning(f"⏭️  [{idx}/{len(pending_data)}] Failed to get/create shop: {transaction['shop']}")
                continue
            
            # Get default category or use first expense category
            category_id = db.get_default_category_for_shop(conn, shop_id)
            if not category_id:
                category_id = db.get_expense_category(conn)
            
            if not category_id:
                logger.warning(f"⏭️  [{idx}/{len(pending_data)}] No category found for {transaction['shop']}")
                continue
            
            # Insert transaction
            tx_id = db.insert_transaction(
                conn,
                transaction['date'],
                shop_id,
                category_id,
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
            for tx in inserted:
                # Escape shop name for Markdown (replace _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !)
                safe_shop = tx['shop'][:30].replace('_', ' ').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
                response.append(f"  • {tx['date']} | {safe_shop} | {tx['amount']:.2f} MDL")
        
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
        analysis = db.get_monthly_analysis(conn, current_year, current_month)
        
        if not analysis:
            await update.message.reply_text(
                f"📊 No transactions found for {current_year}-{current_month:02d}"
            )
            return
        
        # Build response
        response = [f"📊 **Monthly Analysis - {current_year}-{current_month:02d}**\n"]
        
        income_total = 0.0
        expense_total = 0.0
        
        # Process expenses
        response.append("**💸 Expenses:**")
        for category_name, cat_type, count, total in analysis:
            if cat_type == 'expense':
                total_amount = float(total) if total else 0.0
                response.append(f"  • {category_name}: {count} transactions | {total_amount:.2f} MDL")
                expense_total += total_amount
        
        response.append("")
        
        # Process income
        response.append("**💰 Income:**")
        has_income = False
        for category_name, cat_type, count, total in analysis:
            if cat_type == 'income':
                total_amount = float(total) if total else 0.0
                response.append(f"  • {category_name}: {count} transactions | {total_amount:.2f} MDL")
                income_total += total_amount
                has_income = True
        
        if not has_income:
            response.append("  • No income recorded")
        
        response.append("")
        response.append(f"📈 **Summary:**")
        response.append(f"  Total Income: {income_total:.2f} MDL")
        response.append(f"  Total Expenses: {expense_total:.2f} MDL")
        response.append(f"  Net: {income_total - expense_total:.2f} MDL")
        
        await update.message.reply_text(
            "\n".join(response),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in analyze command: {str(e)}")
        await update.message.reply_text(f"❌ Error analyzing data: {str(e)}")
    
    finally:
        db.close_connection(conn)

def main():
    if not BOT_TOKEN:
        logger.error("Missing BOT_TOKEN variable!")
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

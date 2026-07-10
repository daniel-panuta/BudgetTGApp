import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from ...repositories import db_repository
from ...services import parser_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """Upload bank statement (PDF/HTML) and return preview of transactions"""
    try:
        valid_types = {'application/pdf', 'text/html', 'application/x-html+xml'}
        if file.content_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Accept: PDF, HTML. Got: {file.content_type}"
            )
        
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Max 10MB"
            )
        
        # Save to temp file - parse_file() needs a file path
        # Use parse_file() like the bot does for better auto-detection and fallback
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        
        try:
            # parse_file() auto-detects type and has fallback (PDF → HTML if fails)
            transactions = parser_service.parse_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        if not transactions:
            return JSONResponse({
                "transactions": [],
                "message": "No transactions found in file"
            })
        
        preview = [
            {
                "date": tx.get('date', ''),
                "shop": tx.get('shop_name', ''),
                "amount": float(tx.get('amount_mdl', 0)),
                "currency": "MDL",
                "raw_text": tx.get('raw_text', '')[:100]
            }
            for tx in transactions[:50]
        ]
        
        logger.info(f"✅ Parsed {len(transactions)} transactions from {file.filename}")
        
        return JSONResponse({
            "transactions": preview,
            "total": len(transactions)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing file: {str(e)}"
        )


@router.post("/approve")
async def approve_transactions(payload: dict):
    """Approve transactions from preview and save to database"""
    conn = None
    try:
        transactions = payload.get("transactions", [])
        
        if not transactions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transactions provided"
            )
        
        logger.info(f"Processing {len(transactions)} transactions for approval")
        
        conn = db_repository.get_db_connection()
        if not conn:
            raise Exception("Failed to connect to database")
        
        added = 0
        rejected = 0
        
        for tx in transactions:
            try:
                # Extract fields
                date = tx.get('date', '')
                shop_name = tx.get('shop', '')
                amount = float(tx.get('amount', 0))
                currency = tx.get('currency', 'MDL')
                raw_text = tx.get('raw_text', '')
                
                if not date or not shop_name:
                    rejected += 1
                    continue
                
                # Check duplicate
                if db_repository.check_duplicate_transaction(conn, date, shop_name, amount):
                    logger.info(f"⏭️  Skipping duplicate: {shop_name} {amount} MDL on {date}")
                    rejected += 1
                    continue
                
                # Get or create shop
                shop_id = db_repository.get_or_create_shop(conn, shop_name)
                if not shop_id:
                    rejected += 1
                    continue
                
                # Add transaction
                tx_id = db_repository.insert_transaction(
                    conn=conn,
                    date=date,
                    shop_id=shop_id,
                    audit_insert_id=1,
                    amount=abs(amount),
                    currency=currency,
                    amount_original=abs(amount),
                    amount_mdl=abs(amount),
                    raw_text=raw_text
                )
                
                if tx_id:
                    added += 1
                else:
                    rejected += 1
                    
            except Exception as e:
                logger.warning(f"⚠️  Error processing transaction: {str(e)}")
                rejected += 1
                continue
        
        # Commit all transactions
        conn.commit()
        
        logger.info(f"✅ Saved {added} transactions, rejected {rejected}")
        
        return JSONResponse({
            "success": True,
            "added_count": added,
            "rejected_count": rejected,
            "message": f"Successfully added {added} transactions"
        })
        
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error saving transactions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving transactions: {str(e)}"
        )
    finally:
        if conn:
            db_repository.close_connection(conn)

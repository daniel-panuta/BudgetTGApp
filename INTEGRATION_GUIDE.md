# BudgetApp - Integration & Testing Guide

## 🚀 Status Curent

✅ **Frontend - 95% Ready**
- React components fully implemented with TypeScript
- CSS styling complete and responsive
- State management with hooks
- Build successful

✅ **Backend - 70% Ready**  
- Upload endpoint created (parses PDF/HTML)
- Approve endpoint skeleton created
- Integrated with existing parser_service
- Need to implement database save logic

## 📋 Pași de Testare Locală

### 1. Start Backend Local
```bash
cd /Users/danielpanuta/Personal\ Projects/BudgetApp
source .venv/bin/activate

# Setează .env cu DATABASE_URL
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend va rula pe: http://localhost:8000

### 2. Start Frontend Dev Server
```bash
cd frontend/miniapp
npm run dev
# Open http://localhost:5173
```

### 3. Testează Upload Endpoint cu curl
```bash
# Test cu PDF
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/Users/danielpanuta/Personal\ Projects/BudgetApp/extracts/06-2026/maib_05_26_22595619866.html"

# Așteptă response cu transactions preview
```

## 🔧 Cum Să Finalizezi Integrarea

### Step 1: Testează Parser Local
```python
# test_parser.py
from backend.app.services import parser_service

# Test HTML parsing
with open('extracts/06-2026/maib_05_26_22595619866.html', 'r') as f:
    html = f.read()
    txs = parser_service.parse_transactions_from_html(html)
    print(f"Found {len(txs)} transactions")
    for tx in txs[:3]:
        print(tx)
```

### Step 2: Update App.tsx cu API Base URL
```typescript
// src/App.tsx - update na început
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000'

// În handleFileSelect:
const formData = new FormData()
formData.append('file', file)

try {
  const response = await fetch(`${API_BASE}/api/v1/upload`, {
    method: 'POST',
    body: formData
  })
  const data = await response.json()
  setPreviewTxs(data.transactions)
  setStatus('preview')
} catch (error) {
  setError(error.message)
}
```

### Step 3: Implementare Approve cu DB Save
```python
# backend/app/api/routers/upload.py - Update approve endpoint

from ..repositories.db_repository import (
    check_duplicate_transaction,
    add_transaction
)

@router.post("/approve")
async def approve_transactions(payload: dict):
    transactions = payload.get("transactions", [])
    added = 0
    rejected = 0
    
    try:
        conn = db_repository.get_db_connection()
        
        for tx in transactions:
            # Check duplicate
            if check_duplicate_transaction(
                conn, 
                tx['date'], 
                tx['shop'], 
                tx['amount']
            ):
                rejected += 1
                continue
            
            # Add transaction
            add_transaction(
                conn,
                date=tx['date'],
                shop=tx['shop'],
                amount=float(tx['amount']),
                currency=tx.get('currency', 'MDL')
            )
            added += 1
        
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "added_count": added,
            "rejected_count": rejected,
            "message": f"Added {added} transactions"
        })
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_repository.close_connection(conn)
```

## 📊 Testing Workflow

1. **Upload Test** 
   - [ ] Drag PDF/HTML to upload area
   - [ ] See preview with transactions
   - [ ] Verify count matches parsed result

2. **Preview Modal Test**
   - [ ] Shows correct shop names
   - [ ] Shows correct amounts (red for expense, green for income)
   - [ ] Reject button cancels
   - [ ] Approve button triggers processing

3. **Approve Test**
   - [ ] Processing spinner shows
   - [ ] Backend processes transactions
   - [ ] Success report shows added count
   - [ ] Dashboard refreshes with new data

4. **Dashboard Test**
   - [ ] Stats cards show correct totals
   - [ ] Chart shows top categories
   - [ ] Recent transactions table updates

## 🚀 Deployment Checklist

### Local Testing Done
- [ ] Frontend loads without errors
- [ ] Backend API responds
- [ ] Upload endpoint parses files
- [ ] Approve endpoint saves to DB

### Ready for Cloud
- [ ] Update VITE_API_BASE_URL to Cloud Run URL
- [ ] Test upload with real files
- [ ] Verify database saves work
- [ ] Check for error handling

### Deploy to Cloud Run
```bash
# Rebuild și deploy backend
cd /Users/danielpanuta/Personal\ Projects/BudgetApp
./scripts/deploy_cloud_run.sh

# Rebuild și deploy frontend (Vercel)
cd frontend/miniapp
npm run build
vercel deploy --prod
```

## 🐛 Debug Tips

**Frontend Issues:**
```bash
# Check VITE_API_BASE_URL
echo $VITE_API_BASE_URL

# Check network tab in DevTools (F12)
# Filter: fetch/XHR
```

**Backend Issues:**
```bash
# Check logs
# Watch for POST /api/v1/upload requests

# Test parser directly
cd backend
python -c "from app.services import parser_service; print(parser_service.__file__)"
```

**Database Issues:**
```sql
-- Verify connection
SELECT COUNT(*) FROM transactions;

-- Check if transactions were added
SELECT * FROM transactions ORDER BY id DESC LIMIT 5;
```

## 📝 Next Priority Tasks

1. ✅ Frontend UI complete
2. ✅ Backend upload endpoint  
3. ⏳ **Connect Frontend → Backend API**
4. ⏳ **Implement database save logic**
5. ⏳ Test end-to-end workflow
6. ⏳ Deploy to production

---

**Estimated Time to MVP Complete:** 2-3 hours
- Frontend API integration: 30 min
- Backend DB save: 45 min  
- Testing: 30 min
- Deployment: 15 min
- Buffer: 30 min

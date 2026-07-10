# BudgetApp Frontend - Implementation Guide

## 🎯 Cum Funcționează Frontend-ul

### Structura
```
src/
├── App.tsx                 # Main component cu dashboard + upload
├── types/index.ts          # TypeScript types
├── hooks/useDashboard.ts   # Hook pentru fetch data
├── components/
│   ├── FileUploader.tsx    # Upload cu drag-drop
│   ├── TransactionPreview.tsx  # Modal cu preview
│   ├── Dashboard.tsx       # Stats + chart + recent txs
│   └── StatusReport.tsx    # Success/error report
└── styles.css              # Responsive dark theme
```

## 📋 Flow-ul Aplicației

1. **Upload Section** (Idle state)
   - Drag-drop area pentru PDF/HTML
   - Validare: tip, dimensiune
   
2. **Preview Modal** (Preview state)
   - Afișează tranzacții din fișier
   - Approve/Reject buttons
   
3. **Processing** (Processing state)
   - Spinner loading
   
4. **Status Report** (Success/Error state)
   - Confirmă câte au fost adăugate
   - Arată duplicates respinse
   
5. **Dashboard** (După upload sau pe load)
   - 3 stat cards: Expenses, Income, Total
   - Bar chart cu top 3 categorii
   - Tabel cu ultime 5 tranzacții

## 🔗 API Integration

Frontend conectează la:
```
API_BASE_URL = https://budgetapp-api-967298539057.europe-west1.run.app
```

### Endpoints Folosiți
- ✅ `GET /health` - Health check
- ✅ `GET /api/v1/transactions?limit=50` - Fetch recent transactions
- ⏳ `POST /api/v1/upload` - **TREBUIE IMPLEMENTAT** (TODO)
- ⏳ `POST /api/v1/preview` - **TREBUIE IMPLEMENTAT** (TODO)
- ⏳ `POST /api/v1/approve` - **TREBUIE IMPLEMENTAT** (TODO)

## 🚀 Backend Endpoints Care Trebuie Adăugate

### 1. POST /api/v1/upload
```python
# Primește: File (PDF/HTML)
# Returnează: Preview transactions
{
    "transactions": [
        {
            "date": "2026-06-30",
            "shop": "LOCAL 87",
            "amount": -387.99,
            "currency": "MDL"
        }
    ]
}
```

### 2. POST /api/v1/approve
```python
# Primește: Transactions din preview
# Returnează: Rezultatul
{
    "success": true,
    "added_count": 5,
    "rejected_count": 0,
    "message": "All transactions added successfully"
}
```

## 💾 Deployment

### Local Dev
```bash
cd frontend/miniapp
npm install
npm run dev
# Open http://localhost:5173
```

### Production (Vercel)
```bash
# Set environment variable:
VITE_API_BASE_URL=https://budgetapp-api-967298539057.europe-west1.run.app

# Deploy
npm run build
vercel deploy --prod
```

## 📊 Validare Frontend

✅ **Responsiv:**
- Desktop: Full layout
- Tablet: Adjusted grid
- Mobile: Stacked layout

✅ **Accessibility:**
- Dark theme
- High contrast buttons
- Keyboard navigation ready

✅ **Performance:**
- ~150KB gzip (React + UI)
- CSS-in-file (no external)
- Lazy loading stats

## 🔧 Cum Să Adaugi Backend Upload

### 1. Creeaza endpoint in backend/app/api/routers/upload.py

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from ...services.parser_service import parse_pdf, parse_html

router = APIRouter()

@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    # Detecteaza tip
    # Chiama parser_service
    # Returneaza preview
    pass

@router.post("/approve")
async def approve_transactions(transactions: list):
    # Salveaza in DB via db_repository
    # Returneaza rezultat
    pass
```

### 2. Incluie in backend/app/main.py

```python
from .api.routers.upload import router as upload_router
app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
```

### 3. Updateaza App.tsx handleApprove

```typescript
const handleApprove = async () => {
  setStatus('processing')
  try {
    const response = await fetch(
      `${API_BASE}/api/v1/approve`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transactions: previewTxs })
      }
    )
    const result = await response.json()
    setUploadResult(result)
    // ...
  }
}
```

## 🎨 Componentă Personalizare

Puteți modifica:
- Culori în `styles.css` (variabilele CSS)
- Icons în JSX (emoji la moment, pot fi SVG)
- Layout în responsive breakpoints
- Limite paginare în `useDashboard.ts`

## 📱 Telegram Mini App Integration

```typescript
// Deja implemented în App.tsx
const webApp = window.Telegram?.WebApp
webApp?.ready?.()  // Notifică Telegram că app e ready
webApp?.expand?.()  // Expand la full height
```

## 🐛 Debug Tips

1. **Check API connection:**
   ```
   VITE_API_BASE_URL=http://localhost:8000
   npm run dev
   ```

2. **Network tab în DevTools**
   - Verifica request-uri la API
   - Status codes

3. **Logs în console:**
   - useDashboard printe errors
   - FileUploader valida fișiere

## 📞 Support

- Error messages sunt displayed in-app
- Loading states cu spinner
- Retry-able pe most actions

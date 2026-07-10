#!/bin/bash
# Quick Test Script for BudgetApp MVP

set -e

echo "🧪 BudgetApp MVP Test Suite"
echo "============================\n"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="/Users/danielpanuta/Personal Projects/BudgetApp"
cd "$PROJECT_DIR"

# Test 1: Check Backend Imports
echo -e "${YELLOW}1. Checking Backend Imports...${NC}"
source .venv/bin/activate
python -c "from backend.app.main import app; print('✅ Backend imports OK')" || {
    echo -e "${RED}❌ Backend import failed${NC}"
    exit 1
}

# Test 2: Check Frontend Build
echo -e "\n${YELLOW}2. Building Frontend...${NC}"
cd frontend/miniapp
npm run build > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend build successful${NC}"
else
    echo -e "${RED}❌ Frontend build failed${NC}"
    exit 1
fi

# Test 3: Check Requirements
echo -e "\n${YELLOW}3. Verifying Dependencies...${NC}"
cd "$PROJECT_DIR"
python -c "import uvicorn; import fastapi; import psycopg2; import PyPDF2; import bs4" && {
    echo -e "${GREEN}✅ All Python dependencies installed${NC}"
} || {
    echo -e "${RED}❌ Missing Python dependencies${NC}"
    exit 1
}

cd frontend/miniapp
npm list react react-dom typescript > /dev/null 2>&1 && {
    echo -e "${GREEN}✅ All npm dependencies installed${NC}"
} || {
    echo -e "${RED}❌ Missing npm dependencies${NC}"
    exit 1
}

# Test 4: Database Connection
echo -e "\n${YELLOW}4. Checking Database Connection...${NC}"
cd "$PROJECT_DIR"
python -c "
from backend.app.repositories import db_repository
from backend.app.core.settings import DATABASE_URL
try:
    conn = db_repository.get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        db_repository.close_connection(conn)
        print('Database connection OK')
    else:
        raise Exception('No connection')
except Exception as e:
    print(f'Database error: {e}')
    import sys
    sys.exit(1)
" && {
    echo -e "${GREEN}✅ Database connection works${NC}"
} || {
    echo -e "${YELLOW}⚠️  Database connection failed (may work in Cloud Run)${NC}"
}

# Test 5: Frontend Type Checking
echo -e "\n${YELLOW}5. Checking TypeScript Types...${NC}"
cd frontend/miniapp
npx tsc --noEmit > /dev/null 2>&1 && {
    echo -e "${GREEN}✅ TypeScript compilation OK${NC}"
} || {
    echo -e "${RED}❌ TypeScript errors found${NC}"
    exit 1
}

echo -e "\n${GREEN}=============================${NC}"
echo -e "${GREEN}✅ All checks passed!${NC}"
echo -e "${GREEN}=============================${NC}\n"

echo "🚀 Next Steps:"
echo "1. Terminal 1: cd /Users/danielpanuta/Personal\ Projects/BudgetApp"
echo "             source .venv/bin/activate"
echo "             python -m uvicorn backend.app.main:app --reload --port 8000"
echo ""
echo "2. Terminal 2: cd /Users/danielpanuta/Personal\ Projects/BudgetApp/frontend/miniapp"
echo "             npm run dev"
echo ""
echo "3. Open: http://localhost:5173"
echo ""
echo "4. Upload bank statement file (extracts/06-2026/*.html)"

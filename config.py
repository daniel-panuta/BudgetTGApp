"""
Configuration module - loads and manages all environment variables
"""
import os
import urllib.parse

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# TELEGRAM CONFIGURATION
# ============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is required in .env file")

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# Support both DATABASE_URL (Neon) and individual parameters
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    # Parse Neon URL format: postgresql://user:password@host/dbname?sslmode=require
    try:
        parsed = urllib.parse.urlparse(DATABASE_URL)
        DB_HOST = parsed.hostname or "localhost"
        DB_PORT = parsed.port or 5432
        DB_USER = parsed.username or "postgres"
        DB_PASSWORD = parsed.password or ""
        DB_NAME = parsed.path.lstrip('/') or "budget_app"
        DB_SSLMODE = "require"  # Neon requires SSL
    except Exception as e:
        raise ValueError(f"❌ Invalid DATABASE_URL format: {str(e)}")
else:
    # Fallback to individual parameters
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "budget_app")
    DB_SSLMODE = os.getenv("DB_SSLMODE", "prefer")

# Validate database configuration
if not DB_USER or not DB_NAME:
    raise ValueError("❌ DB_USER and DB_NAME are required in .env file")

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
TEMP_PDF_FILENAME = os.getenv("TEMP_PDF_FILENAME", "temp_uploaded_statement.pdf")
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

# ============================================================================
# PDF PARSING CONFIGURATION
# ============================================================================
# Regex pattern for maib bank statements
PDF_PATTERN = os.getenv(
    "PDF_PATTERN",
    r"(\d{4}-\d{2}-\d{2})\s+(?:\d{4}-\d{2}-\d{2})\s+(.+?)\s+(-\d[\d\s.,]*\.\d{2})\s+MDL"
)

# Transactions to filter out (P2P transfers, A2A transfers, IPS, etc.)
FILTER_KEYWORDS = [
    os.getenv("FILTER_P2P_OUT", "P2P de iesire"),
    os.getenv("FILTER_A2A_IN", "A2A de intrare"),
    os.getenv("FILTER_A2A_OUT", "A2A de iesire"),
    os.getenv("FILTER_IPS", "Transfer IPS"),
    os.getenv("FILTER_DIRECT_P2P", "Direct P2P"),
]

# ============================================================================
# DATABASE CONNECTION STRING (for reference)
# ============================================================================
DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

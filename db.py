"""
Database module - all CRUD operations and database interactions
"""
import logging

import psycopg2
import psycopg2.extras

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_SSLMODE, DB_USER

logger = logging.getLogger(__name__)

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

def get_db_connection():
    """
    Create and return a database connection.
    
    Returns:
        psycopg2.connection or None if connection fails
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            sslmode=DB_SSLMODE  # Support SSL for Neon
        )
        logger.debug(f"✅ Connected to database {DB_NAME}")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return None

def close_connection(conn):
    """Close database connection."""
    try:
        if conn:
            conn.close()
            logger.debug("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing connection: {str(e)}")

# ============================================================================
# CATEGORIES CRUD
# ============================================================================

def get_all_categories(conn):
    """
    Get all categories from database.
    
    Args:
        conn: Database connection
        
    Returns:
        List of tuples: [(id, name, type), ...]
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM categories ORDER BY name")
        result = cursor.fetchall()
        logger.debug(f"Fetched {len(result)} categories")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching categories: {str(e)}")
        return []

def get_category_by_id(conn, category_id):
    """Get category by ID."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM categories WHERE id = %s", (category_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"❌ Error fetching category: {str(e)}")
        return None

def get_expense_category(conn):
    """Get first expense category (used as default)."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM categories WHERE type = 'expense' LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"❌ Error fetching expense category: {str(e)}")
        return None

# ============================================================================
# SHOPS CRUD
# ============================================================================

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_shop_name(shop_name):
    """
    Normalize shop name by removing special characters and extra spaces.
    Keep letters, numbers, spaces and preserve Unicode characters.
    
    Examples:
        "LOCAL\" 09 Dacia L6" → "LOCAL 09 Dacia L6"
        "KAUFLAND-NR1_SRL" → "KAUFLAND NR1 SRL"
        "MEGA@STORE_2" → "MEGASTORE 2"
    """
    import re

    # Normalize whitespace and punctuation
    normalized = shop_name.replace('_', ' ')
    normalized = normalized.replace('.', ' ')
    normalized = normalized.replace('/', ' ')
    normalized = normalized.replace('|', ' ')
    normalized = normalized.replace('–', ' ')
    normalized = normalized.replace('—', ' ')

    # Keep letters, numbers, dashes, and spaces for all Unicode scripts
    normalized = re.sub(r'[^\w\s-]', ' ', normalized, flags=re.UNICODE)

    # Remove extra spaces
    normalized = ' '.join(normalized.split())

    return normalized.upper()


def extract_keywords(shop_name):
    """
    Extract meaningful keywords from shop name.
    Removes common suffixes and filters short words.
    """
    common_suffixes = ['SRL', 'SA', 'LLC', 'LTD', 'CORP', 'INC', 'OOO', 'EOOD', 'AD', 'DOO']
    common_words = [
        'AND', 'THE', 'STORE', 'SHOP', 'MARKET', 'CENTER', 'MAIB', 'APP', 'CARD',
        'BANK', 'CITY', 'CHISINAU', 'MOLDOVA', 'TRANS', 'TRANSACTION', 'TRANSACTIONS',
        'OPERATION', 'OPERATIONS', 'PAYMENT', 'PAYMENTS', 'DEBIT', 'CREDIT', 'OTHER',
        'TRANSFER', 'A2A', 'P2P', 'IPS', 'PURCHASE', 'PURCHASES', 'ПОКУПКА', 'ДРУГИЕ',
        'ПРИЧИНА', 'ОПЕРАЦИИ', 'СЧЕТА', 'ПЛАТЕЖ', 'ПЕРЕВОД', 'РАЗНЫЕ', 'ДЕБИТОВЫЕ',
        'ACHITARE', 'CARDUL', 'DANIEL', 'PANUTA'
    ]
    
    normalized = normalize_shop_name(shop_name)
    words = normalized.split()
    
    keywords = [
        w for w in words
        if w not in common_suffixes
        and w not in common_words
        and len(w) > 2
    ]
    
    return keywords if keywords else [normalized]


# ============================================================================
# SHOPS CRUD
# ============================================================================

def get_shop_id_smart(conn, shop_name):
    """
    Intelligently get or create a shop by checking for partial keyword matches.
    Normalizes shop names to remove special characters and quotes.
    
    This prevents duplicate shops with similar names.
    
    Examples:
        - "LOCAL\" 09 Dacia L6" matches existing "LOCAL" shop → returns existing ID
        - "STALMA LUX NR1 SRL" matches existing "NR1" shop → returns existing ID
        - "KAUFLAND NR5" matches existing "KAUFLAND" shop → returns existing ID
        - "NEW STORE NAME" doesn't match any → creates new shop
    
    Args:
        conn: Database connection
        shop_name: Name of the shop from PDF
        
    Returns:
        Shop ID (int) or None if error
    """
    try:
        cursor = conn.cursor()
        
        # Normalize the shop name (remove quotes, special chars)
        normalized_name = normalize_shop_name(shop_name)
        logger.debug(f"Normalized shop name: '{shop_name}' → '{normalized_name}'")
        
        # 1. Try exact match first (fastest)
        cursor.execute("SELECT id FROM shops WHERE UPPER(name) = %s", (normalized_name,))
        result = cursor.fetchone()
        if result:
            logger.debug(f"✅ Found exact match for shop: {normalized_name} (ID: {result[0]})")
            return result[0]
        
        # 2. Extract keywords from normalized shop name
        keywords = extract_keywords(normalized_name)
        logger.debug(f"Extracted keywords from '{normalized_name}': {keywords}")
        
        # 3. Choose best existing shop by keyword overlap
        cursor.execute("SELECT id, name FROM shops")
        existing_shops = cursor.fetchall()
        best_match = None
        best_score = 0
        
        for shop_id, existing_name in existing_shops:
            normalized_existing = normalize_shop_name(existing_name)
            existing_keywords = set(extract_keywords(normalized_existing))
            common = set(keywords) & existing_keywords
            score = len(common)
            if score > best_score:
                best_score = score
                best_match = (shop_id, existing_name, normalized_existing, common)
        
        if best_match and best_score >= 2:
            shop_id, existing_name, normalized_existing, common = best_match
            logger.info(
                f"✅ Best partial match: '{shop_name}' → '{normalized_name}' matched with existing '{existing_name}' "
                f"(normalized: '{normalized_existing}') common keywords: {common}"
            )
            return shop_id
        
        # 4. No confident match found, create new shop with normalized name
        cursor.execute("INSERT INTO shops (name) VALUES (%s) RETURNING id", (normalized_name,))
        shop_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"✅ Created new shop: {normalized_name} (original: {shop_name}) (ID: {shop_id})")
        return shop_id
        
    except Exception as e:
        logger.error(f"❌ Error in smart shop matching: {str(e)}")
        conn.rollback()
        return None


def get_shop_id(conn, shop_name):
    """
    Get or create shop by name (uses smart matching).
    
    This is the main function - it intelligently matches similar shop names
    to prevent duplicates.
    
    Args:
        conn: Database connection
        shop_name: Name of the shop
        
    Returns:
        Shop ID (int) or None if error
    """
    return get_shop_id_smart(conn, shop_name)

def get_default_category_for_shop(conn, shop_id):
    """
    Get the default category for a shop.
    
    Args:
        conn: Database connection
        shop_id: Shop ID
        
    Returns:
        Category ID (int) or None
    """
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT default_category_id FROM shops WHERE id = %s",
            (shop_id,)
        )
        result = cursor.fetchone()
        
        if result and result[0]:
            logger.debug(f"Shop {shop_id} has default category: {result[0]}")
            return result[0]
        
        logger.debug(f"Shop {shop_id} has no default category")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting default category for shop: {str(e)}")
        return None

def update_shop_default_category(conn, shop_id, category_id):
    """Update shop's default category."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE shops SET default_category_id = %s WHERE id = %s",
            (category_id, shop_id)
        )
        conn.commit()
        logger.info(f"✅ Updated shop {shop_id} default category to {category_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating shop category: {str(e)}")
        conn.rollback()
        return False

# ============================================================================
# TRANSACTIONS CRUD
# ============================================================================

def check_duplicate_transaction(conn, date, shop_name, amount, raw_text):
    """
    Check if transaction already exists using multiple methods:
    1. (date + shop + amount) - for similar transactions
    2. raw_text - for exact PDF line duplicates
    
    Args:
        conn: Database connection
        date: Transaction date (YYYY-MM-DD)
        shop_name: Shop name
        amount: Transaction amount
        raw_text: Original text from PDF
        
    Returns:
        True if duplicate exists, False otherwise
    """
    try:
        cursor = conn.cursor()
        
        # Check 1: Exact duplicate by raw_text (most reliable)
        cursor.execute("""
            SELECT id FROM transactions 
            WHERE raw_text = %s
        """, (raw_text,))
        
        if cursor.fetchone() is not None:
            logger.debug(f"⚠️ Exact duplicate found (by raw_text): {raw_text[:50]}...")
            return True
        
        # Check 2: Similar transaction (date + shop + amount)
        cursor.execute("""
            SELECT id FROM transactions 
            WHERE date = %s 
            AND amount = %s
            AND shop_id = (SELECT id FROM shops WHERE name = %s)
        """, (date, amount, shop_name))
        
        if cursor.fetchone() is not None:
            logger.debug(f"⚠️ Similar duplicate found: {date} | {shop_name} | {amount}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking duplicate: {str(e)}")
        return False

def insert_transaction(conn, date, shop_id, category_id, amount, raw_text, currency='MDL', amount_original=None, amount_mdl=None):
    """
    Insert transaction into database.
    
    Args:
        conn: Database connection
        date: Transaction date
        shop_id: Foreign key to shops
        category_id: Foreign key to categories
        amount: Transaction amount in MDL
        raw_text: Original text from PDF/HTML
        currency: Original transaction currency code
        amount_original: Original amount in transaction currency
        amount_mdl: Converted amount in MDL
        
    Returns:
        Transaction ID (int) or None if error
    """
    try:
        # Normalize values so stored transactions are always positive amounts
        if isinstance(amount, (int, float)):
            amount = abs(amount)
        if isinstance(amount_original, (int, float)):
            amount_original = abs(amount_original)
        if isinstance(amount_mdl, (int, float)):
            amount_mdl = abs(amount_mdl)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (
                date,
                shop_id,
                category_id,
                amount,
                currency,
                amount_original,
                amount_mdl,
                raw_text
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (date, shop_id, category_id, amount, currency, amount_original, amount_mdl, raw_text))
        
        transaction_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"✅ Transaction {transaction_id} inserted successfully")
        return transaction_id
        
    except Exception as e:
        logger.error(f"❌ Error inserting transaction: {str(e)}")
        conn.rollback()
        return None

def get_transaction_by_id(conn, transaction_id):
    """Get transaction details by ID."""
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM transactions WHERE id = %s", (transaction_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"❌ Error fetching transaction: {str(e)}")
        return None

def get_transactions_by_shop(conn, shop_id, limit=50):
    """Get recent transactions for a specific shop."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE shop_id = %s 
            ORDER BY date DESC 
            LIMIT %s
        """, (shop_id, limit))
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Error fetching shop transactions: {str(e)}")
        return []

# ============================================================================
# ANALYSIS & REPORTING
# ============================================================================

def get_monthly_analysis(conn, year, month):
    """
    Get transaction analysis for a specific month by categories.
    
    Args:
        conn: Database connection
        year: Year (YYYY)
        month: Month (1-12)
        
    Returns:
        List of tuples: [(category_name, type, count, total_amount), ...]
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.name,
                c.type,
                COUNT(t.id) as transaction_count,
                SUM(t.amount) as total_amount
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE EXTRACT(YEAR FROM t.date) = %s
            AND EXTRACT(MONTH FROM t.date) = %s
            GROUP BY c.id, c.name, c.type
            ORDER BY c.type DESC, c.name
        """, (year, month))
        
        result = cursor.fetchall()
        logger.debug(f"Monthly analysis for {year}-{month}: {len(result)} category rows")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error fetching monthly analysis: {str(e)}")
        return []

def get_yearly_analysis(conn, year):
    """Get transaction analysis for entire year by month."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                EXTRACT(MONTH FROM t.date) as month,
                c.type,
                SUM(t.amount) as total_amount
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE EXTRACT(YEAR FROM t.date) = %s
            GROUP BY EXTRACT(MONTH FROM t.date), c.type
            ORDER BY month, c.type DESC
        """, (year,))
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Error fetching yearly analysis: {str(e)}")
        return []

def get_category_spending(conn, year, month, category_id):
    """Get all transactions for a specific category in a month."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.date, s.name, t.amount
            FROM transactions t
            JOIN shops s ON t.shop_id = s.id
            WHERE t.category_id = %s
            AND EXTRACT(YEAR FROM t.date) = %s
            AND EXTRACT(MONTH FROM t.date) = %s
            ORDER BY t.date DESC
        """, (category_id, year, month))
        
        return cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Error fetching category spending: {str(e)}")
        return []

def get_database_stats(conn):
    """Get database statistics."""
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total_transactions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM shops")
        total_shops = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM categories")
        total_categories = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(amount) FROM transactions")
        total_amount = cursor.fetchone()[0] or 0
        
        return {
            "transactions": total_transactions,
            "shops": total_shops,
            "categories": total_categories,
            "total_amount": float(total_amount)
        }
    except Exception as e:
        logger.error(f"❌ Error fetching database stats: {str(e)}")
        return {}

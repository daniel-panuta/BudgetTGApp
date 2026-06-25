"""Shop lookup and normalization logic for the backend API."""

import logging
import re

logger = logging.getLogger(__name__)


def sanitize_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\ufffd", " ")
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    text = " ".join(text.split())
    return text


def normalize_shop_name(shop_name):
    normalized = sanitize_text(shop_name)
    normalized = normalized.replace("_", " ")
    normalized = normalized.replace(".", " ")
    normalized = normalized.replace("/", " ")
    normalized = normalized.replace("|", " ")
    normalized = normalized.replace("–", " ")
    normalized = normalized.replace("—", " ")
    normalized = re.sub(r"[^\w\s-]", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split()).upper()


def extract_keywords(shop_name):
    common_suffixes = ["SRL", "SA", "LLC", "LTD", "CORP", "INC", "OOO", "EOOD", "AD", "DOO"]
    common_words = [
        "AND",
        "THE",
        "STORE",
        "SHOP",
        "MARKET",
        "CENTER",
        "MAIB",
        "APP",
        "CARD",
        "BANK",
        "CITY",
        "CHISINAU",
        "MOLDOVA",
        "TRANS",
        "TRANSACTION",
        "TRANSACTIONS",
        "OPERATION",
        "OPERATIONS",
        "PAYMENT",
        "PAYMENTS",
        "DEBIT",
        "CREDIT",
        "OTHER",
        "TRANSFER",
        "A2A",
        "P2P",
        "IPS",
        "PURCHASE",
        "PURCHASES",
        "ПОКУПКА",
        "ДРУГИЕ",
        "ПРИЧИНА",
        "ОПЕРАЦИИ",
        "СЧЕТА",
        "ПЛАТЕЖ",
        "ПЕРЕВОД",
        "РАЗНЫЕ",
        "ДЕБИТОВЫЕ",
        "ACHITARE",
        "CARDUL",
        "DANIEL",
        "PANUTA",
    ]

    normalized = normalize_shop_name(shop_name)
    words = normalized.split()
    keywords = [word for word in words if word not in common_suffixes and word not in common_words and len(word) > 2]
    return keywords if keywords else [normalized]


def find_shop_by_name(conn, shop_name):
    cursor = conn.cursor()
    normalized_name = normalize_shop_name(shop_name)

    cursor.execute(
        "SELECT id FROM shops WHERE UPPER(name) = %s OR UPPER(commercial_name) = %s",
        (normalized_name, normalized_name),
    )
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("SELECT id, name, commercial_name FROM shops")
    candidates = cursor.fetchall()
    keywords = set(extract_keywords(normalized_name))
    best_match = None
    best_score = 0

    for shop_id, existing_name, commercial_name in candidates:
        for candidate_name in (existing_name, commercial_name):
            if not candidate_name:
                continue

            existing_keywords = set(extract_keywords(candidate_name))
            score = len(keywords & existing_keywords)
            if score > best_score:
                best_score = score
                best_match = shop_id

    if best_match and best_score >= 2:
        return best_match

    return None


def get_or_create_shop_id(conn, shop_name, default_category_id=None):
    cursor = conn.cursor()
    shop_id = find_shop_by_name(conn, shop_name)
    if shop_id:
        return shop_id

    normalized_name = normalize_shop_name(shop_name)
    cursor.execute(
        """
        SELECT character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'shops' AND column_name = 'name'
        """
    )
    limit_row = cursor.fetchone()
    max_len = limit_row[0] if limit_row and limit_row[0] else 255
    insert_name = normalized_name[:max_len]

    cursor.execute(
        """
        INSERT INTO shops (name, default_category_id)
        VALUES (%s, %s)
        ON CONFLICT (name) DO UPDATE SET default_category_id = COALESCE(EXCLUDED.default_category_id, shops.default_category_id)
        RETURNING id
        """,
        (insert_name, default_category_id),
    )
    new_shop_id = cursor.fetchone()[0]
    conn.commit()
    logger.debug("Created shop %s with id %s", insert_name, new_shop_id)
    return new_shop_id
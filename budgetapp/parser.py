"""
PDF/HTML Parser module - extracts transactions from bank statements
"""
import json
import logging
import os
import re

import PyPDF2
from bs4 import BeautifulSoup

from .config import FILTER_KEYWORDS

logger = logging.getLogger(__name__)

TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), 'templates', 'parser_templates.json')

def load_parser_templates():
    """Load parser templates from JSON file."""
    try:
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as file:
            templates = json.load(file)
        logger.debug(f"Loaded {len(templates)} parser templates")
        return templates
    except Exception as e:
        logger.error(f"❌ Error loading parser templates: {str(e)}")
        return []


PARSER_TEMPLATES = load_parser_templates()


def get_templates(template_type):
    return [t for t in PARSER_TEMPLATES if t.get('type') == template_type]

# Default exchange rates for currency conversion when MDL is not directly available.
# Update these values with actual historical rates for accurate conversion.
EXCHANGE_RATES = {
    "USD": {
        "2026-05-14": 18.50,
        "2026-05-15": 18.55,
        "2026-05-16": 18.60,
        "2026-05-18": 18.65,
    },
    "EUR": {
        "2026-05-14": 20.50,
        "2026-05-15": 20.55,
        "2026-06-12": 20.75,
    },
    "RON": {
        "2026-06-09": 4.35,
        "2026-06-10": 4.34,
    }
}


def parse_decimal(value_str):
    """Parse a numeric value string into a float."""
    if not value_str:
        return None

    value = value_str.strip().replace(' ', '').replace(',', '.')
    sign = 1

    if value.endswith('-'):
        sign = -1
        value = value[:-1]
    elif value.endswith('+'):
        value = value[:-1]

    if value == '' or value == '-':
        return None

    try:
        return float(value) * sign
    except ValueError:
        logger.debug(f"Could not parse decimal value: {value_str}")
        return None


def normalize_currency(currency_str):
    """Normalize currency strings to uppercase ISO codes."""
    if not currency_str:
        return 'MDL'
    norm = currency_str.strip().upper()
    if norm in ('MDL', 'MOLDOVA LEU', 'LEU'):
        return 'MDL'
    if norm in ('USD', 'US DOLLAR', 'DOLLAR'):
        return 'USD'
    if norm in ('EUR', 'EURO'):
        return 'EUR'
    if norm in ('RON', 'LEU ROMANESC', 'LEU ROMÂNESC', 'RON'):
        return 'RON'
    if norm in ('RUB', 'RUBLE', 'RUSSIAN RUBLE'):
        return 'RUB'
    return norm


def _normalize_currency_template(raw_currency, currency_hint, default_currency=None):
    if raw_currency:
        return normalize_currency(raw_currency)
    if currency_hint and currency_hint != 'auto':
        return normalize_currency(currency_hint)
    if default_currency:
        return normalize_currency(default_currency)
    return 'MDL'


def _normalize_shop(raw_shop):
    if not raw_shop:
        return None
    shop = raw_shop.replace('\n', ' ').strip()
    shop = ' '.join(shop.split())
    return shop


def _normalize_date(raw_date):
    if not raw_date:
        return None

    raw_date = raw_date.strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_date):
        return raw_date
    if re.match(r'^\d{2}\.\d{2}\.\d{4}$', raw_date):
        day, month, year = raw_date.split('.')
        return f"{year}-{month}-{day}"
    if re.match(r'^\d{2}-\d{2}-\d{4}$', raw_date):
        day, month, year = raw_date.split('-')
        return f"{year}-{month}-{day}"

    logger.debug(f"Unsupported date format: {raw_date}")
    return None


def _extract_template_date(groups):
    if not groups:
        return None

    raw_date = (
        groups.get('date')
        or groups.get('processing_date')
        or groups.get('posting_date')
        or groups.get('transaction_date')
    )
    if not raw_date:
        return None

    raw_date = raw_date.strip()
    if ' ' in raw_date and re.match(r'^\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2}$', raw_date):
        raw_date = raw_date.split()[0]
    return raw_date


def _parse_amount_for_template(raw_amount):
    if not raw_amount:
        return None
    value = raw_amount.strip().replace(' ', '').replace(',', '.')
    is_negative = value.endswith('-')
    is_positive = value.endswith('+')
    if is_negative or is_positive:
        value = value[:-1]
    try:
        amount = float(value)
        return -amount if is_negative else amount
    except ValueError:
        logger.debug(f"Failed to parse amount: {raw_amount}")
        return None


def _resolve_amount_mdl(date_value, currency, amount, amount_mdl_from_bank=None):
    """
    Resolve MDL amount for a transaction.
    
    Priority:
    1. Use MDL value extracted from bank statement (amount_mdl_from_bank)
    2. If currency is MDL, return the amount
    3. Otherwise, convert using exchange rates
    
    Args:
        date_value: Transaction date
        currency: Original transaction currency
        amount: Amount in original currency
        amount_mdl_from_bank: MDL amount extracted from bank (if available)
        
    Returns:
        Amount in MDL
    """
    # Priority 1: Use bank-provided MDL amount if available
    if amount_mdl_from_bank is not None:
        return round(amount_mdl_from_bank, 2)
    
    # Priority 2: If currency is already MDL, return it
    if currency == 'MDL':
        return round(amount, 2)
    
    # Priority 3: Convert from original currency to MDL
    return convert_amount_to_mdl(date_value, currency, amount)


def _is_pdf_table_header_line(line):
    """Detect repeated table header/footer lines inside PDF extraction."""
    if not line:
        return False

    normalized = line.replace(' ', '').replace('\n', '').lower()
    header_keywords = [
        'datatranzacțieidata',
        'procesăriidescriereaoperațiunii',
        'sumăînvalutatranzacției',
        'sumăînvalutacontului',
        'ieșiriintrărîicomisionsulduptrătranzacție',
        'tranzacție',
        '5din',
        'datalist'  # safe generic footer/header noise marker
    ]

    return any(keyword in normalized for keyword in header_keywords)


def _normalize_pdf_lines(lines):
    """Normalize PDF lines by merging split row date markers and removing header noise."""
    if not lines:
        return lines

    normalized = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if _is_pdf_table_header_line(line):
            idx += 1
            continue

        if re.match(r'^\d{4}-\d{2}-\d{2}\s*$', line) and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            if next_line.startswith(line):
                normalized.append(f"{line} {next_line}")
                idx += 2
                continue

        normalized.append(line)
        idx += 1

    return normalized


def _group_pdf_transaction_lines(text):
    """Group PDF text lines that belong to the same transaction row."""
    if not text:
        return text

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    raw_lines = [line.strip() for line in text.split('\n') if line.strip()]
    lines = _normalize_pdf_lines(raw_lines)
    grouped = []
    current = ''
    date_header_regex = re.compile(
        r'^(?:\d{4}-\d{2}-\d{2})\s+(?:\d{4}-\d{2}-\d{2})\b'
    )

    for line in lines:
        if date_header_regex.match(line):
            if current:
                grouped.append(current.strip())
            current = line
        else:
            if current:
                current = f"{current} {line}"
            else:
                current = line

    if current:
        grouped.append(current.strip())

    return '\n'.join(grouped)


def _split_embedded_pdf_transaction_rows(rows):
    """Split rows that contain embedded single-date transactions inside a larger block."""
    if not rows:
        return rows

    split_rows = []
    embedded_anchor = re.compile(r'(?=(?:\d{4}-\d{2}-\d{2})(?!\s+\d{4}-\d{2}-\d{2}))')

    for row in rows:
        positions = [m.start() for m in embedded_anchor.finditer(row)]
        if len(positions) <= 1:
            split_rows.append(row)
            continue

        for idx, pos in enumerate(positions):
            end = positions[idx + 1] if idx + 1 < len(positions) else len(row)
            part = row[pos:end].strip()
            if part:
                split_rows.append(part)

    return split_rows


def _split_pdf_transaction_rows(grouped_text):
    """Split grouped PDF text into individual transaction rows by full date header lines."""
    if not grouped_text:
        return []

    split_pattern = re.compile(r'\n(?=\d{4}-\d{2}-\d{2}\s+\d{4}-\d{2}-\d{2})')
    rows = [row.strip() for row in split_pattern.split(grouped_text) if row.strip()]
    return _split_embedded_pdf_transaction_rows(rows)


def get_exchange_rate_for_date(date_str, currency):
    """Return the exchange rate for the given date and currency."""
    currency = normalize_currency(currency)
    if currency == 'MDL':
        return 1.0

    rates = EXCHANGE_RATES.get(currency, {})
    if date_str in rates:
        return rates[date_str]

    # Try to find the closest previous date if exact date is missing
    available_dates = sorted(rates.keys())
    for d in reversed(available_dates):
        if d <= date_str:
            return rates[d]

    logger.warning(f"Exchange rate missing for {currency} on {date_str}")
    return None


def convert_amount_to_mdl(date_str, currency, amount):
    """Convert an amount in a given currency to MDL using the date-specific rate."""
    if currency == 'MDL' or amount is None:
        return amount

    rate = get_exchange_rate_for_date(date_str, currency)
    if rate is None:
        return None

    return round(amount * rate, 2)


def parse_statement_currency(html_content):
    """Parse the account statement currency from MAIB HTML header."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for bold in soup.find_all('b'):
        if bold.get_text(strip=True).lower().startswith('valuta'):
            parent_td = bold.find_parent('td')
            if parent_td:
                next_td = parent_td.find_next_sibling('td')
                if next_td:
                    currency = next_td.get_text(strip=True)
                    if currency:
                        return normalize_currency(currency)
    return 'MDL'

# ============================================================================
# PDF PARSING
# ============================================================================

def extract_text_from_pdf(file_path):
    """
    Extract all text from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        String containing all text from PDF
    """
    try:
        text = ""
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            page_count = len(reader.pages)
            logger.debug(f"PDF has {page_count} pages")
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                text += page_text + "\n"
                logger.debug(f"Extracted text from page {page_num + 1}")
        
        logger.info(f"✅ Successfully extracted text from PDF ({len(text)} characters)")
        return text
        
    except Exception as e:
        logger.error(f"❌ Error extracting text from PDF: {str(e)}")
        return None

def parse_transactions_from_text(text):
    """
    Parse transactions from PDF text using configured templates.

    Args:
        text: Text extracted from PDF

    Returns:
        List of transaction dictionaries
    """
    transactions = []
    seen_keys = set()

    templates = get_templates('pdf')
    if not templates:
        logger.warning("⚠️ No PDF templates configured in JSON")
        return []

    grouped_text = _group_pdf_transaction_lines(text)
    lines = _split_pdf_transaction_rows(grouped_text)

    for template in templates:
        try:
            pattern = template.get('pattern')
            currency_hint = template.get('currency', 'MDL')
            regex = re.compile(pattern)
            matches = 0

            for line in lines:
                for match in regex.finditer(line):
                    matches += 1
                    groups = match.groupdict()
                    raw_date = groups.get('date')
                    raw_shop = groups.get('shop')
                    raw_amount = groups.get('amount')
                    raw_currency = groups.get('currency')
                    raw_amount_mdl = groups.get('amount_mdl')

                    # Normalize values
                    date_value = _normalize_date(raw_date)
                    shop = _normalize_shop(raw_shop)
                    currency = _normalize_currency_template(raw_currency, currency_hint)
                    amount_value = _parse_amount_for_template(raw_amount)
                    amount_mdl_value = _parse_amount_for_template(raw_amount_mdl)

                    if not date_value or not shop or amount_value is None:
                        logger.debug(f"Skipping invalid transaction row: date={raw_date}, shop={raw_shop}, amount={raw_amount}")
                        continue

                    if _should_filter_transaction(shop):
                        logger.debug(f"Filtering out: {shop}")
                        continue

                    # Resolve MDL amount: prioritize bank-provided amount_mdl, then convert if needed
                    amount_mdl = _resolve_amount_mdl(date_value, currency, amount_value, amount_mdl_from_bank=amount_mdl_value)

                    if amount_mdl is None:
                        logger.debug(f"Could not resolve MDL amount for {shop} on {date_value}")
                        continue

                    amount_mdl = abs(amount_mdl)
                    amount_original = abs(amount_value)
                    unique_key = (date_value, shop, currency, amount_mdl, amount_original)
                    if unique_key in seen_keys:
                        continue

                    raw_text = f"{date_value} - {shop} - {amount_original:.2f} {currency} -> {amount_mdl:.2f} MDL"
                    if 'comision' in shop.lower() or 'commission' in shop.lower():
                        raw_text += " (commission)"

                    transaction = {
                        "date": date_value,
                        "shop": shop,
                        "currency": currency,
                        "amount_original": amount_original,
                        "amount_mdl": amount_mdl,
                        "amount": amount_mdl,
                        "raw_text": raw_text
                    }

                    if validate_transaction(transaction):
                        seen_keys.add(unique_key)
                        transactions.append(transaction)
                        logger.debug(f"Parsed transaction: {date_value} | {shop} | {amount_mdl:.2f} {currency}")

            logger.debug(f"Template '{template.get('name')}' found {matches} potential matches")
        except re.error as e:
            logger.error(f"❌ Invalid regex in template '{template.get('name')}': {str(e)}")
            continue
        except Exception as e:
            logger.error(f"❌ Error parsing with template '{template.get('name')}': {str(e)}")
            continue

    if transactions:
        logger.info(f"✅ Parsed {len(transactions)} transactions using PDF templates")
    else:
        logger.warning("⚠️ No transactions could be parsed with configured templates")
    return transactions

def parse_pdf_file(file_path):
    """
    Main function - parse PDF file and extract transactions.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of transaction dictionaries or None if error
    """
    logger.info(f"Starting PDF parsing: {file_path}")
    
    # Extract text
    text = extract_text_from_pdf(file_path)
    if text is None:
        return None
    
    # Parse transactions
    transactions = parse_transactions_from_text(text)
    
    if not transactions:
        logger.warning("⚠️ No transactions found in PDF")
        return []
    
    logger.info(f"✅ PDF parsing complete: {len(transactions)} transactions extracted")
    return transactions

# ============================================================================
# HTML PARSING
# ============================================================================

def extract_transactions_from_html(file_path):
    """
    Extract all transactions from HTML bank statement file.
    Supports multiple encodings: UTF-8, Windows-1251, ISO-8859-1, etc.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        String containing HTML content or None if error
    """
    encodings = ['utf-8', 'windows-1251', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as file:
                content = file.read()
            
            # Verify content looks like HTML
            if '<table' in content.lower() or '<tr' in content.lower():
                logger.info(f"✅ Successfully read HTML file with {encoding} encoding ({len(content)} characters)")
                return content
            
        except Exception as e:
            logger.debug(f"Could not read with {encoding}: {str(e)}")
            continue
    
    logger.error(f"❌ Error reading HTML file - could not decode with any supported encoding")
    return None

def detect_bank_from_html(html_content):
    """
    Detect which bank the HTML statement is from.
    
    Args:
        html_content: HTML content as string
        
    Returns:
        String: 'victoriabank', 'maib', or 'unknown'
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    html_lower = html_content.lower()
    
    # Check for Victoriabank indicators
    if 'victoriabank' in html_lower or 'sigla.jpg' in html_lower:
        return 'victoriabank'
    
    # Check for MAIB indicators
    if 'maib' in html_lower or 'moldova agroindbank' in html_lower:
        return 'maib'
    
    return 'unknown'

def parse_victoriabank_html(html_content):
    """
    Parse transactions from Victoriabank HTML statement.
    
    Args:
        html_content: HTML content as string
        
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')
        logger.debug(f"Found {len(rows)} table rows in Victoriabank HTML")
        
        # Find the header row with "Data procesarii"
        header_found = False
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 7:
                continue
            
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Look for header row
            if 'Data procesarii' in cell_texts[0] or 'Data tranzactiei' in cell_texts[0]:
                header_found = True
                logger.debug("Found Victoriabank transaction table header")
                continue
            
            if not header_found:
                continue
            
            # Skip empty rows or summary rows
            if len(cell_texts) < 7 or not cell_texts[1].strip():
                continue
            
            try:
                # Victoriabank format:
                # [0] Data procesarii (processing date)
                # [1] Data tranzactiei (transaction date) - format: "14-05-2026 16:02:24"
                # [2] Detaliile tranzactiei (shop/details)
                # [3] Suma in valuta originala
                # [4] Suma in valuta contului (THE AMOUNT WE WANT)
                # [5] Comision
                # [6] Total
                
                transaction_date_raw = cell_texts[1].strip()
                
                # Skip if it's a header or empty
                if 'Data' in transaction_date_raw or not transaction_date_raw:
                    continue
                
                # Extract date - format: "14-05-2026 16:02:24"
                date_part = transaction_date_raw.split()[0]
                
                # Convert DD-MM-YYYY to YYYY-MM-DD
                day, month, year = date_part.split('-')
                date = f"{year}-{month}-{day}"
                
                # Extract shop name from details (column 2)
                shop_raw = cell_texts[2].strip()
                # Remove HTML tags and clean
                shop = re.sub(r'<[^>]+>', '', shop_raw).strip()
                shop = re.sub(r'<DetTran>|</DetTran>', '', shop)  # Remove DetTran tags
                shop = ' '.join(shop.split())  # Normalize whitespace
                
                # Skip if no shop name
                if not shop:
                    continue
                
                # Extract amount from column 4 (valuta contului)
                amount_raw = cell_texts[4].strip()
                
                # Check if amount is negative (withdrawal)
                is_negative = amount_raw.startswith('-')
                
                # Extract numeric value
                amount_str = amount_raw.replace('-', '').replace(' ', '').replace(',', '.')
                
                # Skip if amount is 0 or empty
                try:
                    amount = float(amount_str)
                    if amount == 0:
                        continue
                except ValueError:
                    logger.debug(f"Could not parse amount: {amount_str}")
                    continue
                
                # Apply sign to amount
                if is_negative:
                    amount = -amount
                
                # Check if should be filtered
                if _should_filter_transaction(shop):
                    logger.debug(f"Filtering out: {shop}")
                    continue
                
                amount = abs(amount)

                transaction = {
                    "date": date,
                    "shop": shop,
                    "currency": "MDL",
                    "amount_original": amount,
                    "amount_mdl": amount,
                    "amount": amount,
                    "raw_text": f"{date} - {shop} - {amount_raw} MDL"
                }

                transactions.append(transaction)
                logger.debug(f"Parsed Victoriabank transaction: {date} | {shop} | {amount:.2f} MDL")

            except (IndexError, ValueError) as e:
                logger.debug(f"Could not parse Victoriabank row: {str(e)}")
                continue
        
        logger.info(f"✅ Successfully parsed {len(transactions)} transactions from Victoriabank HTML")
        return transactions
        
    except Exception as e:
        logger.error(f"❌ Error parsing Victoriabank HTML: {str(e)}")
        return []

def parse_maib_html(html_content):
    """
    Parse transactions from MAIB HTML statement.
    
    Args:
        html_content: HTML content as string
        
    Returns:
        List of transaction dictionaries
    """
    transactions = []
    default_currency = parse_statement_currency(html_content)
    logger.debug(f"Detected statement currency: {default_currency}")
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')
        logger.debug(f"Found {len(rows)} table rows in MAIB HTML")
        
        for row in rows:
            cells = row.find_all('td')
            
            # MAIB format requires at least 7 columns
            if len(cells) < 7:
                continue
            
            # Extract cell text
            cell_texts = [cell.get_text(strip=True) for cell in cells]
            
            # Skip header rows or empty rows
            if not cell_texts[0].strip() or 'Data inregistrarii' in cell_texts[0]:
                continue
            
            try:
                # MAIB format:
                # [0] Data inregistrarii (registration date)
                # [1] Data tranzactiei (transaction date) - THIS IS THE DATE WE WANT
                # [2] Numar de referinta al tranzactiei (reference number)
                # [3] Descriere tranzactie (shop/details)
                # [4] Valuta tranzactiei (transaction currency)
                # [5] Suma in valuta tranzactiei (amount in original currency)
                # [6] Suma in valuta contului (amount in account currency) - THIS IS THE AMOUNT WE WANT
                
                # Extract date - format: "DD-MM-YYYY"
                transaction_date_raw = cell_texts[1].strip()
                
                # Skip if no date
                if not transaction_date_raw or len(transaction_date_raw) < 8:
                    continue
                
                # Convert DD-MM-YYYY to YYYY-MM-DD
                try:
                    day, month, year = transaction_date_raw.split('-')
                    date = f"{year}-{month}-{day}"
                except (ValueError, IndexError):
                    logger.debug(f"Could not parse date: {transaction_date_raw}")
                    continue
                
                # Extract shop name from details (column 3)
                shop_raw = cell_texts[3].strip()
                
                # Clean up HTML tags and special characters
                shop = re.sub(r'<[^>]+>', '', shop_raw).strip()
                shop = ' '.join(shop.split())  # Normalize whitespace
                
                # Skip if no shop name
                if not shop:
                    continue
                
                # Check if should be filtered before processing
                if _should_filter_transaction(shop):
                    logger.debug(f"Filtering out: {shop}")
                    continue
                
                # Extract transaction currency and amounts
                currency_raw = cell_texts[4].strip()
                currency = normalize_currency(currency_raw or default_currency)
                original_amount_raw = cell_texts[5].strip()
                account_amount_raw = cell_texts[6].strip()

                original_amount = parse_decimal(original_amount_raw)
                account_amount = parse_decimal(account_amount_raw)
                is_negative = False
                if account_amount_raw:
                    is_negative = account_amount_raw.strip().endswith('-')
                elif original_amount_raw:
                    is_negative = original_amount_raw.strip().endswith('-')

                date = _normalize_date(transaction_date_raw)
                if not date:
                    logger.debug(f"Skipping invalid MAIB date row: {transaction_date_raw}")
                    continue

                # Allow any currency code, even if exchange rates are unavailable.
                # We still attempt MDL conversion when possible.
                if currency == 'MDL':
                    amount_mdl = account_amount if account_amount is not None else original_amount
                else:
                    if normalize_currency(default_currency) == 'MDL' and account_amount is not None:
                        # Amount in account currency is already MDL if statement currency is MDL.
                        amount_mdl = account_amount
                    else:
                        amount_mdl = original_amount if original_amount is not None else None
                        if amount_mdl is not None:
                            amount_mdl = convert_amount_to_mdl(date, currency, amount_mdl)

                if amount_mdl is None:
                    logger.debug(f"No MDL amount determined for {shop} ({currency})")
                    continue

                if is_negative:
                    amount_mdl = abs(amount_mdl)

                amount_original = abs(original_amount) if original_amount is not None else None
                amount_mdl = abs(amount_mdl)

                # Build raw text with currency info
                transaction = {
                    "date": date,
                    "shop": shop,
                    "currency": currency,
                    "amount_original": amount_original,
                    "amount_mdl": amount_mdl,
                    "amount": amount_mdl,
                    "raw_text": f"{date} - {shop} - {original_amount_raw} {currency} - {amount_mdl:.2f} MDL"
                }
                
                transactions.append(transaction)
                logger.debug(f"Parsed MAIB transaction: {date} | {shop} | {amount_mdl:.2f} MDL")
                
            except (IndexError, ValueError) as e:
                logger.debug(f"Could not parse MAIB row: {str(e)}")
                continue
        
        logger.info(f"✅ Successfully parsed {len(transactions)} transactions from MAIB HTML")
        return transactions
        
    except Exception as e:
        logger.error(f"❌ Error parsing MAIB HTML: {str(e)}")
        return []

def parse_transactions_from_html(html_content):
    """
    Parse transactions from HTML content using BeautifulSoup.
    Supports multiple banks: Victoriabank, MAIB, etc.

    Args:
        html_content: HTML content as string

    Returns:
        List of transaction dictionaries
    """
    try:
        transactions = parse_transactions_from_html_templates(html_content)
        if transactions:
            return transactions

        # Detect which bank
        bank = detect_bank_from_html(html_content)
        logger.info(f"Detected bank format: {bank}")

        if bank == 'victoriabank':
            return parse_victoriabank_html(html_content)
        elif bank == 'maib':
            return parse_maib_html(html_content)
        else:
            # Try Victoriabank first, then MAIB
            logger.warning("Unknown bank format, trying Victoriabank parser...")
            transactions = parse_victoriabank_html(html_content)
            if transactions:
                return transactions
            logger.warning("No transactions found with Victoriabank parser, trying MAIB...")
            return parse_maib_html(html_content)

    except Exception as e:
        logger.error(f"❌ Error parsing HTML transactions: {str(e)}")
        return []

def parse_html_file(file_path):
    """
    Main function - parse HTML file and extract transactions.
    
    Args:
        file_path: Path to HTML file
        
    Returns:
        List of transaction dictionaries or None if error
    """
    logger.info(f"Starting HTML parsing: {file_path}")
    
    # Extract HTML content
    content = extract_transactions_from_html(file_path)
    if content is None:
        return None
    
    # Parse transactions
    transactions = parse_transactions_from_html(content)
    
    if not transactions:
        logger.warning("⚠️ No transactions found in HTML")
        return []
    
    logger.info(f"✅ HTML parsing complete: {len(transactions)} transactions extracted")
    return transactions

# ============================================================================
# FILE TYPE DETECTION
# ============================================================================

def detect_file_type(file_path):
    """
    Detect if file is PDF or HTML by checking both extension and content.
    
    Args:
        file_path: Path to file
        
    Returns:
        String: 'pdf' or 'html' or None if unknown
    """
    try:
        # First, try to detect by content (most reliable)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(200)
            
            # Check for HTML markers
            if '<!DOCTYPE' in content or '<html' in content.lower() or '<table' in content.lower():
                logger.debug(f"Detected HTML content in {file_path}")
                return 'html'
            
            # Check for PDF markers
            if content.startswith('%PDF'):
                logger.debug(f"Detected PDF content in {file_path}")
                return 'pdf'
    except Exception as e:
        logger.debug(f"Could not read file for content detection: {str(e)}")
    
    # Fallback to extension detection
    file_lower = file_path.lower()
    
    if file_lower.endswith('.pdf'):
        return 'pdf'
    elif file_lower.endswith('.html') or file_lower.endswith('.htm'):
        return 'html'
    else:
        return None

def parse_file(file_path):
    """
    Parse any supported file type (PDF or HTML).
    Tries to detect type and falls back if one parser fails.
    
    Args:
        file_path: Path to file
        
    Returns:
        List of transaction dictionaries or None if error
    """
    file_type = detect_file_type(file_path)
    
    logger.info(f"Detected file type: {file_type}")
    
    if file_type == 'html':
        logger.info(f"Parsing as HTML file: {file_path}")
        return parse_html_file(file_path)
    elif file_type == 'pdf':
        logger.info(f"Parsing as PDF file: {file_path}")
        result = parse_pdf_file(file_path)
        
        # If PDF parsing fails, try HTML parsing as fallback
        if not result:
            logger.warning(f"PDF parsing failed or returned no transactions, trying HTML as fallback...")
            result = parse_html_file(file_path)
        
        return result
    else:
        # Unknown type - try both parsers
        logger.warning(f"Unknown file type for {file_path}, trying both parsers...")
        
        # Try HTML first (more likely for web-based statements)
        result = parse_html_file(file_path)
        if result:
            return result
        
        # Try PDF as fallback
        result = parse_pdf_file(file_path)
        if result:
            return result
        
        logger.error(f"❌ Could not parse file with any method: {file_path}")
        return None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def parse_transactions_from_html_templates(html_content):
    """Parse HTML content using HTML templates from JSON."""
    transactions = []
    templates = get_templates('html')
    if not templates:
        logger.debug("No HTML templates configured")
        return []

    default_currency = parse_statement_currency(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = [tr.get_text(separator=' ', strip=True) for tr in soup.find_all('tr') if tr.get_text(strip=True)]

    for template in templates:
        try:
            regex = re.compile(template.get('pattern'))
            for row in rows:
                for match in regex.finditer(row):
                    groups = match.groupdict()
                    raw_date = _extract_template_date(groups)
                    raw_shop = groups.get('shop')
                    raw_amount = groups.get('amount')
                    raw_currency = groups.get('currency')
                    raw_amount_mdl = groups.get('amount_mdl')

                    date_value = _normalize_date(raw_date)
                    shop = _normalize_shop(raw_shop)
                    currency = _normalize_currency_template(raw_currency, template.get('currency', 'MDL'), default_currency)
                    amount_value = _parse_amount_for_template(raw_amount)

                    amount_mdl_value = _parse_amount_for_template(raw_amount_mdl)
                    amount_mdl = _resolve_amount_mdl(
                        date_value,
                        currency,
                        amount_value,
                        amount_mdl_from_bank=amount_mdl_value
                    )

                    if not date_value or not shop or amount_value is None:
                        continue
                    if amount_mdl is None:
                        continue
                    if _should_filter_transaction(shop):
                        continue

                    transaction = {
                        'date': date_value,
                        'shop': shop,
                        'currency': currency,
                        'amount_original': amount_value,
                        'amount_mdl': amount_mdl,
                        'amount': amount_mdl,
                        'raw_text': row
                    }
                    if validate_transaction(transaction):
                        transactions.append(transaction)

            if transactions:
                logger.info(f"✅ Parsed {len(transactions)} HTML transactions using template '{template.get('name')}'")
                return transactions
        except re.error as e:
            logger.error(f"❌ Invalid regex in HTML template '{template.get('name')}': {str(e)}")
            continue
        except Exception as e:
            logger.error(f"❌ Error parsing HTML with template '{template.get('name')}': {str(e)}")
            continue

    logger.debug("No HTML transactions parsed from templates")
    return []


def _should_filter_transaction(shop_name):
    """
    Check if transaction should be filtered out.

    Args:
        shop_name: Name of shop

    Returns:
        True if should filter, False otherwise
    """
    if not shop_name:
        return False

    shop_name_lower = shop_name.lower()
    for keyword in FILTER_KEYWORDS:
        if keyword and keyword.lower() in shop_name_lower:
            return True
    return False

def validate_transaction(transaction):
    """
    Validate transaction data.

    Args:
        transaction: Transaction dictionary

    Returns:
        True if valid, False otherwise
    """
    try:
        required_fields = ["date", "shop", "amount", "raw_text"]
        for field in required_fields:
            if field not in transaction:
                logger.warning(f"Missing field '{field}' in transaction")
                return False

        if not re.match(r"^\d{4}-\d{2}-\d{2}$", transaction["date"]):
            logger.warning(f"Invalid date format: {transaction['date']}")
            return False

        if not isinstance(transaction["amount"], (int, float)):
            logger.warning(f"Invalid amount type: {transaction['amount']} ({type(transaction['amount'])})")
            return False

        if transaction["amount"] == 0:
            logger.warning(f"Transaction amount is zero: {transaction}")
            return False

        if not transaction["shop"] or len(transaction["shop"].strip()) == 0:
            logger.warning("Empty shop name")
            return False

        if transaction.get("currency"):
            currency_code = transaction["currency"].strip().upper()
            if not currency_code or not re.match(r'^[A-Z]{2,5}$', currency_code):
                logger.warning(f"Invalid currency code: {transaction['currency']}")
                return False

        return True
    except Exception as e:
        logger.error(f"❌ Error validating transaction: {str(e)}")
        return False

def format_transaction_for_display(transaction):
    """
    Format transaction for Telegram display.
    
    Args:
        transaction: Transaction dictionary
        
    Returns:
        Formatted string
    """
    if transaction.get('currency') and transaction.get('currency') != 'MDL':
        original = transaction.get('amount_original')
        currency = transaction.get('currency')
        if original is not None:
            return f"📅 {transaction['date']} | 🏪 *{transaction['shop']}* | 💸 **{abs(original):.2f} {currency}** → **{abs(transaction['amount']):.2f} MDL**"
    return f"📅 {transaction['date']} | 🏪 *{transaction['shop']}* | 💸 **{abs(transaction['amount']):.2f} MDL**"

def get_transaction_statistics(transactions):
    """
    Calculate statistics from transaction list.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Dictionary with statistics
    """
    if not transactions:
        return {
            "count": 0,
            "total": 0.0,
            "average": 0.0,
            "min": 0.0,
            "max": 0.0
        }
    
    amounts = [abs(t["amount"]) for t in transactions]
    total = sum(amounts)
    
    return {
        "count": len(transactions),
        "total": total,
        "average": total / len(transactions),
        "min": min(amounts),
        "max": max(amounts)
    }

#!/usr/bin/env python3
"""
Test script for parser.parse_transactions_from_text() function
Shows how the parser works with sample PDF text
"""

import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.services.parser_service import (extract_text_from_pdf,
                                                 parse_file,
                                                 parse_transactions_from_text)


# ============================================================================
# TEST 1: Parse sample PDF text directly
# ============================================================================
def test_sample_text():
    """Test with sample transaction text"""
    print("=" * 80)
    print("TEST 1: Parse sample PDF transaction text")
    print("=" * 80)
    
    # Sample transaction rows (as they appear in MAIB PDF)
    sample_text = """
    2026-06-12 2026-06-12 PAY BY LINK VECTOR ACADEM 5.00 EUR 101.96
    2026-06-11 2026-06-11 BOLT EU V.O.S 15.50 EUR 316.31
    2026-06-10 2026-06-10 YANDEX GO 10.25 RON 47.24
    2026-06-09 2026-06-09 CINEPLEX DACIA 150.00 MDL 150.00
    """
    
    transactions = parse_transactions_from_text(sample_text)
    
    print(f"\n✅ Parsed {len(transactions)} transactions:\n")
    for i, tx in enumerate(transactions, 1):
        print(f"Transaction {i}:")
        print(f"  Date: {tx['date']}")
        print(f"  Shop: {tx['shop']}")
        print(f"  Currency: {tx['currency']}")
        print(f"  Amount Original: {tx['amount_original']:.2f} {tx['currency']}")
        print(f"  Amount MDL: {tx['amount_mdl']:.2f} MDL")
        print(f"  Amount (DB): {tx['amount']:.2f} MDL")
        print(f"  Raw Text: {tx['raw_text']}")
        print()


# ============================================================================
# TEST 2: Parse from actual PDF file
# ============================================================================
def test_pdf_file():
    """Test parsing from actual PDF file"""
    print("=" * 80)
    print("TEST 2: Parse from actual PDF file")
    print("=" * 80)
    
    pdf_path = "extracts/06-2026/Extras_din_cont_2026-06-12_2026-06-22.pdf"
    
    try:
        transactions = parse_file(pdf_path)
        
        if transactions:
            print(f"\n✅ Successfully parsed {len(transactions)} transactions from PDF\n")
            
            # Show first 3 transactions
            print("First 3 transactions:")
            for tx in transactions[:3]:
                print(f"  {tx['date']} | {tx['shop']:<40} | {tx['amount']:.2f} MDL")
            
            if len(transactions) > 3:
                print(f"  ... and {len(transactions) - 3} more")
        else:
            print("⚠️  No transactions found in PDF")
    
    except Exception as e:
        print(f"❌ Error parsing PDF: {str(e)}")


# ============================================================================
# TEST 3: Extract text from PDF and parse
# ============================================================================
def test_extract_and_parse():
    """Extract text from PDF, then parse it"""
    print("=" * 80)
    print("TEST 3: Extract text from PDF, then parse manually")
    print("=" * 80)
    
    pdf_path = "extracts/06-2026/Extras_din_cont_2026-06-12_2026-06-22.pdf"
    
    try:
        # Step 1: Extract text from PDF
        print(f"\nExtracting text from: {pdf_path}")
        text = extract_text_from_pdf(pdf_path)
        
        if text:
            print(f"✅ Extracted {len(text)} characters from PDF\n")
            
            # Step 2: Parse transactions
            print("Parsing transactions...")
            transactions = parse_transactions_from_text(text)
            
            print(f"✅ Found {len(transactions)} transactions\n")
            
            # Step 3: Show details
            print("Sample transactions:")
            for tx in transactions[:5]:
                print(f"  {tx['date']} | {tx['shop']:<40} | {tx['amount_original']:.2f} {tx['currency']} -> {tx['amount_mdl']:.2f} MDL")
        
        else:
            print("❌ Could not extract text from PDF")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")


# ============================================================================
# TEST 4: Filter keywords test
# ============================================================================
def test_with_filters():
    """Test that MAIB P2P is filtered out"""
    print("=" * 80)
    print("TEST 4: Verify MAIB P2P filtering")
    print("=" * 80)
    
    sample_text = """
    2026-06-12 2026-06-12 PAY BY LINK VECTOR ACADEM 5.00 EUR 101.96
    2026-06-11 2026-06-11 MAIB P2P Transfer 100.00 MDL 100.00
    2026-06-10 2026-06-10 BOLT EU V.O.S 15.50 EUR 316.31
    2026-06-09 2026-06-09 P2P de iesire 50.00 MDL 50.00
    2026-06-08 2026-06-08 CINEPLEX DACIA 150.00 MDL 150.00
    """
    
    transactions = parse_transactions_from_text(sample_text)
    
    print(f"\n✅ Parsed {len(transactions)} transactions (2-3 should be filtered out):\n")
    for tx in transactions:
        print(f"  {tx['shop']:<40} | {tx['amount']:.2f} MDL")
    
    # Verify filters worked
    filtered_shops = [tx['shop'] for tx in transactions]
    assert 'MAIB P2P Transfer' not in filtered_shops, "MAIB P2P should be filtered!"
    assert 'P2P de iesire' not in filtered_shops, "P2P de iesire should be filtered!"
    print("\n✅ Filter keywords working correctly!")


# ============================================================================
# TEST 5: Show transaction structure
# ============================================================================
def test_transaction_structure():
    """Show the structure of a parsed transaction"""
    print("=" * 80)
    print("TEST 5: Transaction structure")
    print("=" * 80)
    
    sample_text = "2026-06-12 2026-06-12 PAY BY LINK VECTOR ACADEM 5.00 EUR 101.96"
    transactions = parse_transactions_from_text(sample_text)
    
    if transactions:
        tx = transactions[0]
        print("\nTransaction object structure:")
        print(json.dumps(tx, indent=2, default=str))


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    print("\n")
    print("🧪 PARSER FUNCTION TEST SUITE")
    print("=" * 80)
    print("\n")
    
    # Run tests
    test_sample_text()
    print("\n")
    
    test_transaction_structure()
    print("\n")
    
    test_with_filters()
    print("\n")
    
    # These require actual files
    try:
        test_extract_and_parse()
    except FileNotFoundError:
        print("⚠️  Skipping PDF file tests (file not found)")
    
    print("\n" + "=" * 80)
    print("✅ Tests completed!")
    print("=" * 80 + "\n")

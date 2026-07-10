import unittest

from backend.app.repositories import db_repository as db
from backend.app.services import parser_service as parser
from budgetapp.bot import summarize_transactions_preview


class ParserBusinessLogicTests(unittest.TestCase):
    def test_detect_file_type_prefers_content_over_extension(self):
        # Telegram can send HTML statements with .pdf extension.
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".pdf", delete=True) as tmp:
            tmp.write("<html><table><tr><td>row</td></tr></table></html>")
            tmp.flush()
            self.assertEqual(parser.detect_file_type(tmp.name), "html")

    def test_parse_decimal_sign_and_separator_handling(self):
        self.assertEqual(parser.parse_decimal("101,96"), 101.96)
        self.assertEqual(parser.parse_decimal("101.96-"), -101.96)
        self.assertEqual(parser.parse_decimal("101.96+"), 101.96)
        self.assertIsNone(parser.parse_decimal("not-a-number"))

    def test_exchange_rate_fallback_to_previous_date(self):
        rate = parser.get_exchange_rate_for_date("2026-05-17", "EUR")
        self.assertEqual(rate, 20.55)

    def test_convert_amount_to_mdl_with_unknown_rate_returns_none(self):
        self.assertIsNone(parser.convert_amount_to_mdl("2020-01-01", "USD", 10))

    def test_should_filter_transfer_keywords(self):
        self.assertTrue(parser._should_filter_transaction("MAIB P2P Transfer catre prieten"))
        self.assertTrue(parser._should_filter_transaction("Direct P2P plata"))
        self.assertFalse(parser._should_filter_transaction("KAUFLAND CHISINAU"))

    def test_parse_transactions_from_text_filters_p2p(self):
        text = "\n".join(
            [
                "2026-06-12 2026-06-12 PAY BY LINK VECTOR ACADEM 5.00 EUR 101.96",
                "2026-06-11 2026-06-11 MAIB P2P Transfer 100.00 MDL 100.00",
            ]
        )

        transactions = parser.parse_transactions_from_text(text)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["shop"], "PAY BY LINK VECTOR ACADEM")
        self.assertEqual(transactions[0]["currency"], "EUR")
        self.assertEqual(transactions[0]["amount"], 101.96)

    def test_parse_transactions_from_text_omits_card_verification_pairs(self):
        text = "\n".join(
            [
                "2026-05-15 2026-05-15 PP*2792CODE 1.00- USD 18.55-",
                "2026-05-15 2026-05-15 PP*2792CODE 1.00+ USD 18.55+",
            ]
        )

        transactions = parser.parse_transactions_from_text(text)
        self.assertEqual(transactions, [])

    def test_statistics_use_absolute_amounts(self):
        stats = parser.get_transaction_statistics(
            [
                {"amount": -20.0},
                {"amount": 10.0},
                {"amount": -5.0},
            ]
        )

        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["total"], 35.0)
        self.assertAlmostEqual(stats["average"], 35.0 / 3)
        self.assertEqual(stats["min"], 5.0)
        self.assertEqual(stats["max"], 20.0)


class BotBusinessLogicTests(unittest.TestCase):
    def test_summarize_preview_returns_all_for_small_list(self):
        txs = [
            {"date": "2026-06-12", "shop": "A", "amount": 10.0, "currency": "MDL"},
            {"date": "2026-06-13", "shop": "B", "amount": 20.0, "currency": "MDL"},
            {"date": "2026-06-14", "shop": "C", "amount": 30.0, "currency": "MDL"},
        ]

        preview = summarize_transactions_preview(txs, preview_size=2)
        self.assertEqual(len(preview), 3)

    def test_summarize_preview_returns_first_and_last_chunks(self):
        txs = [
            {"date": "2026-06-10", "shop": "S1", "amount": 1.0, "currency": "MDL"},
            {"date": "2026-06-11", "shop": "S2", "amount": 2.0, "currency": "MDL"},
            {"date": "2026-06-12", "shop": "S3", "amount": 3.0, "currency": "MDL"},
            {"date": "2026-06-13", "shop": "S4", "amount": 4.0, "currency": "MDL"},
            {"date": "2026-06-14", "shop": "S5", "amount": 5.0, "currency": "MDL"},
        ]

        preview = summarize_transactions_preview(txs, preview_size=2)
        self.assertEqual(len(preview), 4)
        self.assertIn("S1", preview[0])
        self.assertIn("S2", preview[1])
        self.assertIn("S4", preview[2])
        self.assertIn("S5", preview[3])


class DbBusinessLogicTests(unittest.TestCase):
    def test_sanitize_text_removes_control_chars(self):
        value = " SHOP\x00\n\tNAME \ufffd "
        self.assertEqual(db.sanitize_text(value), "SHOP NAME")

    def test_normalize_shop_name_keeps_words_and_uppercases(self):
        self.assertEqual(db.normalize_shop_name('LOCAL" 09 Dacia L6'), "LOCAL 09 DACIA L6")
        self.assertEqual(db.normalize_shop_name("KAUFLAND-NR1_SRL"), "KAUFLAND-NR1 SRL")

    def test_extract_keywords_removes_common_noise(self):
        keywords = db.extract_keywords("MAIB APP KAUFLAND NR1 SRL CHISINAU")
        self.assertIn("KAUFLAND", keywords)
        self.assertIn("NR1", keywords)
        self.assertNotIn("MAIB", keywords)
        self.assertNotIn("APP", keywords)

    def test_previous_month_rollover(self):
        self.assertEqual(db._previous_month(2026, 1), (2025, 12))
        self.assertEqual(db._previous_month(2026, 6), (2026, 5))


if __name__ == "__main__":
    unittest.main()
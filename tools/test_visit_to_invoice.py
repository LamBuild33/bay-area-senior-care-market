"""Tests for visit_to_invoice.py, using the worked examples in docs/weekly_invoice.md.
Run:  python -m unittest tools/test_visit_to_invoice.py   (from the repo folder)
"""
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import visit_to_invoice as v  # noqa: E402

CLIENT = {"name": "Example Client", "rate": 35, "minimum_hours": 4, "mileage_rate": 0.76}


def note(day="Tuesday, October 13", times="10:00 am - 2:20 pm", drives="None."):
    return (f"Visit note\nDate: {day}\nStart time - end time: {times}\n"
            f"What we did: x\nDrives or purchases today (miles, items and amount, receipt kept): {drives}\n"
            "Next visit: soon\n")


def invoice(text):
    visits = v.parse_notes(text, 2026)
    return v.compute_invoice(visits, CLIENT, "example", 1, date(2026, 10, 16)), visits


class WorkedExamples(unittest.TestCase):
    def test_nearest_minute(self):            # 4 h 20 min at $35 = $151.67
        inv, _ = invoice(note())
        self.assertEqual(inv.lines[0].actual, 260)
        self.assertEqual(inv.visits_total, Decimal("151.67"))

    def test_shortest_visit_applies(self):    # 3 h 10 min billed as 4 h = $140.00
        inv, _ = invoice(note(times="10:00 am - 1:10 pm"))
        self.assertEqual(inv.lines[0].billed, 240)
        self.assertEqual(inv.visits_total, Decimal("140.00"))

    def test_mileage(self):                   # 6.2 miles at $0.76 = $4.71
        inv, _ = invoice(note(drives="6.2 miles to the pharmacy and store."))
        self.assertEqual(inv.mileage_total, Decimal("4.71"))

    def test_purchases(self):                 # client's card listed only; mine added
        inv, _ = invoice(note(drives="Groceries $38.40 on your card, receipt kept. "
                                     "Batteries $12.00 on my card, receipt kept."))
        self.assertEqual(inv.repay_total, Decimal("12.00"))
        self.assertEqual(inv.total, Decimal("151.67") + Decimal("12.00"))


class Safety(unittest.TestCase):
    def test_unsure_card_not_added_and_flagged(self):
        inv, _ = invoice(note(drives="Lamp $20.00, receipt kept."))
        self.assertEqual(inv.repay_total, Decimal("0.00"))
        self.assertEqual(len(inv.unsure), 1)

    def test_both_cards_in_one_sentence_is_unsure(self):
        inv, _ = invoice(note(drives="Soap $5.00 on your card or my card."))
        self.assertEqual(len(inv.unsure), 1)

    def test_own_card_over_100_warns(self):
        inv, _ = invoice(note(drives="Chair $120.00 on my card, receipt kept."))
        self.assertTrue(any("under $100" in w for w in inv.warnings))

    def test_over_12_hours_warns(self):
        inv, _ = invoice(note(times="7:00 am - 8:30 pm"))
        self.assertTrue(any("12 hours" in w for w in inv.warnings))

    def test_bad_times_block_that_visit(self):
        _, visits = invoice(note() + note(day="Friday, October 16", times="10 - 2"))
        self.assertTrue(visits[1].errors)

    def test_end_before_start_is_an_error(self):
        visits = v.parse_notes(note(times="2:00 pm - 10:00 am"), 2026)
        self.assertTrue(visits[0].errors)

    def test_wrong_weekday_warns(self):
        visits = v.parse_notes(note(day="Wednesday, October 13"), 2026)
        self.assertTrue(visits[0].warnings)

    def test_duplicate_note_warns(self):
        _, visits = invoice(note() + note())
        self.assertTrue(any("repeat" in w for w in visits[1].warnings))

    def test_mileage_sentence_dollar_not_a_purchase(self):
        inv, _ = invoice(note(drives="6.2 miles to the store ($4.71)."))
        self.assertEqual(len(inv.purchases), 0)

    def test_due_date_is_seven_days_after_sending(self):
        inv, _ = invoice(note())
        self.assertEqual(inv.due, date(2026, 10, 23))

    def test_curly_dash_and_plain_pm_formats(self):
        inv, _ = invoice(note(times="10:00 AM – 2:20 PM"))
        self.assertEqual(inv.lines[0].actual, 260)


class TwoVisits(unittest.TestCase):
    def test_example_file_total(self):
        text = Path(__file__).with_name("example_notes.txt").read_text(encoding="utf-8")
        inv, _ = invoice(text)
        # 4h20 = 151.67; 3h10 -> 4h min = 140.00; mileage 4.71; my card 12.00
        self.assertEqual(inv.total, Decimal("151.67") + Decimal("140.00") + Decimal("4.71") + Decimal("12.00"))


if __name__ == "__main__":
    unittest.main()

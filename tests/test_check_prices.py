"""The price-watch parsers against the operators' real pages as fetched 2026-10-21 (tests/fixtures/prices/,
already stripped to text exactly as check_prices.text() produces). If an operator redesigns, the daily job
alerts; these tests pin the parsers against the known-good layout. Run: python3 -m pytest tests/"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import check_prices as cp

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "prices")


def fx(name):
    return open(os.path.join(FIX, name + ".txt"), encoding="utf-8").read()


class Parsers(unittest.TestCase):
    def test_carreiros(self):
        self.assertEqual(cp.carreiros(fx("carreiros")),
                         {"sled_1": "30", "sled_2": "40", "sled_3": "60", "days_hours": "Mon-Sat 09:00-18:00"})

    def test_cablecar(self):
        self.assertEqual(cp.cablecar(fx("cablecar")), {"return": "22", "one_way": "16"})

    def test_montepalace(self):
        self.assertEqual(cp.montepalace(fx("montepalace")), {"adult": "18"})

    def test_gardencable(self):
        self.assertEqual(cp.gardencable(fx("gardencable")),
                         {"one_way": "11", "round": "16", "combo_one_way": "19", "combo_round": "24"})

    def test_hfbus(self):
        got = cp.hfbus(fx("hfbus"))
        self.assertEqual(got["fare"], "3,00")
        self.assertEqual(got["shuttle"], "1,20")
        self.assertEqual(got["times"], "06:00,06:45,13:30,14:15,12:15,19:00")

    def test_redesign_is_detected(self):
        self.assertIsNone(cp.carreiros("a page without the price cards"))


if __name__ == "__main__":
    unittest.main()

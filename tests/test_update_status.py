"""The status pipeline's sharp edges: the PR1 one-way rule (owner, 2026-10-20: the CONDICIONADOS listing is
one-way, never a closure) and the never-publish-a-contradiction gate. Run: python3 -m pytest tests/"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import update_status as u

ONEWAY_PT = "Percurso com sentido único entre o Miradouro da Pedra Rija e o Pico Ruivo."


class OneWay(unittest.TestCase):
    def test_oneway_only_listing_is_not_a_closure(self):
        note = u.oneway_note("PR1", [("CLOSED", ONEWAY_PT)])
        self.assertIsNotNone(note)
        self.assertIn("en", note)
        self.assertNotIn("closed", note["en"].lower())

    def test_real_closure_still_wins(self):
        self.assertIsNone(u.oneway_note("PR1", [("CLOSED", ONEWAY_PT), ("CLOSED", "Encerrado por derrocada ao km 2.")]))

    def test_only_pr1(self):
        self.assertIsNone(u.oneway_note("PR6", [("CLOSED", ONEWAY_PT)]))


class Contradiction(unittest.TestCase):
    def test_open_with_restrictive_note_fails_loud(self):
        with self.assertRaises(SystemExit):
            u.assert_not_contradictory("OPEN", {"en": "Open only between km 1,2 and the summit."})

    def test_honest_open_passes(self):
        u.assert_not_contradictory("OPEN", {"en": "Trail in good condition."})


if __name__ == "__main__":
    unittest.main()

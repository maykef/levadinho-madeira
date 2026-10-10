#!/usr/bin/env python3
"""Tests for storm.py with IFCN's real notices (March 2026 closure and reopening, the standing trail list).
Run: python3 scripts/test_storm.py"""
import json, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storm

CLOSURE_0303 = ("O Instituto das Florestas e Conservação da Natureza, IP-RAM informa que, devido aos avisos meteorológicos "
                "emitidos, pelo Instituto Português do Mar e da Atmosfera (IPMA), para a Região Autónoma da Madeira, todos "
                "os percursos pedestres classificados da RAM estarão encerrados no dia 03 de março de 2026. Mais se informa "
                "que a Estrada Florestal que liga a Eira do Serrado ao Pico do Areeiro estará igualmente encerrada. "
                "Após a sua abertura, caso verifique alguma situação anómala nos percursos pedestres...")
REOPEN_0305 = ("O Instituto das Florestas e Conservação da Natureza, IP-RAM, informa que, a partir de amanhã, dia 05 de "
               "março de 2026, os percursos pedestres classificados da RAM, bem como a Estrada Florestal que liga a Eira do "
               "Serrado ao Pico do Areeiro já se encontram transitáveis. Mantêm-se, contudo, encerrados os seguintes "
               "percursos pedestres: PR 1.3 Vereda da Encumeada PR 7 Levada do Moinho PR 10 Levada do Furado")
STANDING = ("Solicita-se a atenção para o novo modelo de taxas e reservas no acesso aos Percursos pedestres classificados, "
            "em vigor desde o dia 01 de janeiro de 2026. O IFCN informa que os seguintes percursos pedestres classificados "
            "se encontram: ENCERRADOS/CONDICIONADOS: PR 1 Vereda do Areeiro PR 7 Levada do Moinho PARCIALMENTE "
            "TRANSITÁVEIS: PR 4 ... TRANSITÁVEIS: PR 6 ... reabre a 30 de novembro de 2026")
SINGLE_TRAIL = ("O IFCN informa que, em virtude da ocorrência de uma derrocada, o percurso pedestre PR 10 Levada do Furado "
                "encontra-se temporariamente encerrado, por motivos de segurança.")
ROAD = ("O Instituto das Florestas e Conservação da Natureza, IP-RAM vem informar que, devido à realização do evento Eco "
        "Rally Madeira, a Estrada Florestal que liga a Eira do Serrado ao Pico do Areeiro estará encerrada no dia 4 de "
        "outubro de 2026 entre as 07h55 e as 10h08.")


def page(*texts):
    return "<html><body>" + "".join(
        f'<div class="com-content-category-blog__item blog-item"><div class="article-intro-text"><p>{t}</p></div></div>'
        for t in texts) + "</body></html>"


class Blanket(unittest.TestCase):
    def run_on(self, today, *texts):
        os.environ["STORM_TODAY"] = today
        return storm.blanket(page(*texts))

    def test_normal_page_no_blanket(self):
        self.assertIsNone(self.run_on("2026-10-10", ROAD, SINGLE_TRAIL, STANDING)["state"])

    def test_closure_announced_the_day_before(self):
        b = self.run_on("2026-03-02", CLOSURE_0303, ROAD, STANDING)
        self.assertEqual((b["state"], b["from"]), ("announced", "2026-03-03"))

    def test_closure_in_force_on_the_day(self):
        self.assertEqual(self.run_on("2026-03-03", CLOSURE_0303, STANDING)["state"], "closed")

    def test_closure_stays_until_a_reopening_notice(self):
        self.assertEqual(self.run_on("2026-03-04", CLOSURE_0303, STANDING)["state"], "closed")

    def test_reopening_announced_for_tomorrow_keeps_closed(self):
        b = self.run_on("2026-03-04", REOPEN_0305, CLOSURE_0303, STANDING)
        self.assertEqual((b["state"], b["reopen"]), ("closed", "2026-03-05"))
        self.assertIn("reopen tomorrow", storm.blanket_note(b)["en"])

    def test_reopened(self):
        self.assertIsNone(self.run_on("2026-03-05", REOPEN_0305, CLOSURE_0303, STANDING)["state"])

    def test_standing_list_and_single_trail_never_blanket(self):
        for t in (STANDING, SINGLE_TRAIL, ROAD):
            self.assertIsNone(storm.classify(t), t[:40])

    def test_page_changed_is_fatal(self):
        with self.assertRaises(SystemExit):
            storm.blanket("<html>nothing here</html>")

    def test_apply_closes_every_trail(self):
        trails = [{"code": "PR1", "status": "PARTIAL"}, {"code": "PR6", "status": "OPEN"}]
        os.environ["STORM_TODAY"] = "2026-03-03"
        self.assertTrue(storm.apply(trails, {"state": "closed"}))
        self.assertEqual({t["status"] for t in trails}, {"CLOSED"})
        self.assertEqual(trails[0]["ifcn_status"], "PARTIAL")
        self.assertFalse(storm.apply(trails, {"state": "announced"}))


class Ipma(unittest.TestCase):
    def test_orange_mountains_now(self):
        os.environ["STORM_NOW"] = "2026-05-05T09:00:00"
        raw = json.dumps([
            {"idAreaAviso": "MRM", "awarenessLevelID": "orange", "awarenessTypeName": "Precipitação",
             "startTime": "2026-05-05T06:00:00", "endTime": "2026-05-05T21:00:00", "text": ""},
            {"idAreaAviso": "MPS", "awarenessLevelID": "red", "awarenessTypeName": "Vento",
             "startTime": "2026-05-05T06:00:00", "endTime": "2026-05-05T21:00:00", "text": ""},
            {"idAreaAviso": "MCN", "awarenessLevelID": "yellow", "awarenessTypeName": "Vento",
             "startTime": "2026-05-05T06:00:00", "endTime": "2026-05-05T21:00:00", "text": ""}])
        a = storm.ipma_alert(raw)
        self.assertEqual((a["level"], len(a["warnings"]), a["warnings"][0]["now"]), ("orange", 1, True))

    def test_orange_tomorrow_counts_expired_does_not(self):
        os.environ["STORM_NOW"] = "2026-05-04T20:00:00"
        raw = json.dumps([
            {"idAreaAviso": "MCS", "awarenessLevelID": "orange", "awarenessTypeName": "Precipitação",
             "startTime": "2026-05-05T06:00:00", "endTime": "2026-05-05T21:00:00"},
            {"idAreaAviso": "MCN", "awarenessLevelID": "red", "awarenessTypeName": "Vento",
             "startTime": "2026-05-03T06:00:00", "endTime": "2026-05-04T06:00:00"}])
        a = storm.ipma_alert(raw)
        self.assertEqual((a["level"], a["warnings"][0]["now"]), ("orange", False))

    def test_broken_feed_degrades(self):
        self.assertEqual(storm.ipma_alert("not json"), {"ok": False})


if __name__ == "__main__":
    unittest.main(verbosity=1)

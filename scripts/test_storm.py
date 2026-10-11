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


# IFCN's real September 2026 notice (inside its standing article, after the fees line), and the notices that must
# NOT become dated closures: PR8 open with detours, PR3 closed "until the works end", a forest road.
PR1_SEPT = ("Solicita-se a atenção para o novo modelo de taxas e reservas no acesso aos Percursos pedestres classificados, "
            "em vigor desde o dia 01 de janeiro de 2026, podendo ser consultado as FAQ's para esclarecimento do mesmo. "
            "O Instituto das Florestas e Conservação da Natureza informa que, nos dias 14 a 17 e 21 a 22 de setembro de "
            "2026, estará encerrado o troço do PR1 – Vereda do Areeiro compreendido entre o Miradouro da Pedra Rija e o "
            "Pico Ruivo, para permitir a realização de intervenções programadas no percurso. Durante estes períodos, não "
            "será possível realizar o percurso completo entre o Pico do Areeiro e o Pico Ruivo. " + STANDING)
PR8_DETOURS = ("O Instituto das Florestas e Conservação da Natureza informa que, devido à execução dos trabalhos de "
               "recuperação do PR8 – Vereda da Ponta de São Lourenço, será necessário introduzir pequenos desvios "
               "temporários ao traçado habitual do percurso, mantendo-se o percurso aberto. Esta situação terá início no "
               "dia 30 de setembro de 2026 e manter-se-á por um período mínimo de 270 dias.")
PR3_WORKS = ("O IFCN informa que, a ARM, no âmbito da Empreitada, encontra-se a realizar trabalhos. Por este motivo, o "
             "percurso pedestre PR 3 Levada do Pico do Castelo permanecerá temporariamente encerrado até à conclusão dos "
             "referidos trabalhos.")
WHOLE_PERIOD = ("O IFCN informa que o percurso pedestre PR 9 Levada do Caldeirão Verde estará encerrado. O encerramento "
                "terá início no dia 2 de novembro de 2026, estando previsto por um período de 10 dias.")
UNDATED_FUTURE = "O IFCN informa que o percurso pedestre PR 11 Vereda dos Balcões estará encerrado para obras."


class TrailClosures(unittest.TestCase):
    def run_on(self, today, *texts):
        os.environ["STORM_TODAY"] = today
        return storm.trail_closures(page(*texts))

    def test_before_is_announced_with_all_days(self):
        c, = self.run_on("2026-09-01", PR1_SEPT, PR8_DETOURS, PR3_WORKS, ROAD, SINGLE_TRAIL)
        self.assertEqual((c["codes"], c["state"], c["section"]), (["PR1"], "announced", True))
        self.assertEqual(c["ranges"], [["2026-09-14", "2026-09-17"], ["2026-09-21", "2026-09-22"]])
        self.assertTrue(c["text"].startswith("Nos dias 14 a 17 e 21 a 22 de setembro de 2026, estará encerrado o troço do PR1"))

    def test_closure_day_is_closed(self):
        for day in ("2026-09-14", "2026-09-17", "2026-09-21", "2026-09-22"):
            self.assertEqual(self.run_on(day, PR1_SEPT)[0]["state"], "closed", day)

    def test_between_blocks_announces_the_rest_only(self):
        c, = self.run_on("2026-09-18", PR1_SEPT)
        self.assertEqual((c["state"], c["ranges"]), ("announced", [["2026-09-21", "2026-09-22"]]))

    def test_after_last_day_gone(self):
        self.assertEqual(self.run_on("2026-09-23", PR1_SEPT), [])
        self.assertEqual(self.run_on("2026-10-11", PR1_SEPT), [])

    def test_not_dated_closures(self):
        self.assertEqual(self.run_on("2026-09-01", PR8_DETOURS, PR3_WORKS, ROAD, SINGLE_TRAIL, STANDING), [])

    def test_start_plus_period(self):
        c, = self.run_on("2026-10-11", WHOLE_PERIOD)
        self.assertEqual((c["codes"], c["ranges"], c["section"]), (["PR9"], [["2026-11-02", "2026-11-11"]], False))

    def test_future_closure_without_dates_fails_loud(self):
        with self.assertRaises(SystemExit):
            self.run_on("2026-10-11", UNDATED_FUTURE)

    def test_dates_in_five_languages(self):
        r = [["2026-09-14", "2026-09-17"], ["2026-09-21", "2026-09-22"]]
        self.assertEqual([storm.fmt_ranges(r, l) for l in ("en", "pt", "fr", "de", "pl")],
                         ["14–17 and 21–22 September", "14 a 17 e 21 a 22 de setembro",
                          "du 14 au 17 et du 21 au 22 septembre", "14.–17. und 21.–22. September", "14–17 i 21–22 września"])
        self.assertEqual(storm.fmt_ranges([["2026-09-28", "2026-10-02"]], "en"), "28 September–2 October")
        self.assertEqual(storm.fmt_ranges([["2026-10-04", "2026-10-04"]], "pt"), "4 de outubro")

    def test_closure_text(self):
        c, = self.run_on("2026-09-14", PR1_SEPT)
        t = storm.closure_text(c, {"pt": c["text"], "en": "On 14 to 17 ..."})
        self.assertEqual(t["en"], "Section closed today by an IFCN notice (14–17 and 21–22 September). On 14 to 17 ...")

if __name__ == "__main__":
    unittest.main(verbosity=1)

"""Real notices from 2021-2026 (seo_research/funchal/promenade_research.md §3). Run: python3 -m unittest -v"""
import datetime as dt
import unittest
from classify import classify

D = dt.date


class Real(unittest.TestCase):
    def check(self, text, official, posted, decision, areas=None, action=None, starts=None, ends=None):
        r = classify(text, official, posted)
        self.assertEqual(r["decision"], decision, r)
        if areas is not None:
            self.assertEqual(r["areas"], areas, r)
        if action is not None:
            self.assertEqual(r["action"], action, r)
        if starts is not None:
            self.assertEqual(r["starts"], starts, r)
        if ends is not None:
            self.assertEqual(r["ends"], ends, r)

    def test_boardwalk_closed_press(self):  # DN 2026-08-16
        self.check("Passadiço da Praia Formosa encerrado preventivamente", False, D(2026, 8, 16),
                   "review", [2], "closure")

    def test_boardwalk_closed_official(self):
        self.check("O passadiço da Praia Formosa encontra-se encerrado preventivamente devido à cedência do pavimento.",
                   True, D(2026, 8, 16), "apply", [2], "closure")

    def test_boardwalk_reopened(self):  # DN 2024-05-21 headline, as if posted by SMD
        self.check("Passeio público marítimo reaberto entre a Praia Formosa e os Socorridos", True, D(2024, 5, 21),
                   "apply", [2], "reopening")

    def test_doca_works_dates(self):  # CMF 2026-06
        r = classify("Doca do Cavacas encerra de 22 a 26 de junho para substituição das pontes de madeira; "
                     "interrupções temporárias no percurso pedonal entre a Doca e a Praia Formosa", True, D(2026, 6, 15))
        self.assertEqual((r["starts"], r["ends"]), ("2026-06-22", "2026-06-26"))
        self.assertIn(4, r["areas"])
        self.assertEqual(r["decision"], "apply")

    def test_storm_francis(self):  # CMF 2026-01-01
        self.check("Devido à agitação marítima, a promenade da Praia Formosa encontra-se encerrada, bem como os "
                   "complexos balneares e os acessos ao mar.", True, D(2026, 1, 1), "apply", [3], "closure")

    def test_sea_access_only(self):  # CMF 2025-12-12
        self.check("Encontram-se encerrados os acessos ao mar, com colocação de barreiras físicas, pela FrenteMar Funchal",
                   True, D(2025, 12, 12), "apply", [], "sea_access")

    def test_formosa_to_cdl(self):  # DN 2026-02-11, official wording assumed
        self.check("Está interdito o passeio marítimo entre a Praia Formosa e Câmara de Lobos devido à forte agitação marítima.",
                   True, D(2026, 2, 11), "apply", [1, 2, 3], "closure")

    def test_cliff_cleaning(self):  # CMF 2025-08
        self.check("Limpeza de escarpas condiciona mobilidade na Avenida Sá Carneiro, Rua Dr. João Serra e promenade do Lido, "
                   "entre a Ponta Gorda e o Madeira Magic, no dia 8 de agosto", True, D(2025, 8, 5), "review", None, "closure", "2025-08-08", "2025-08-08")

    def test_unrelated_closure(self):  # CMF 2026-10-02 strike notice
        self.check("O Ecocentro do Funchal encontra-se encerrado ao público devido à greve.", True, D(2026, 10, 2), "ignore")

    def test_lido_pool_only(self):
        self.check("O Complexo Balnear do Lido estará encerrado amanhã para manutenção.", True, D(2026, 10, 2), "review", [6])

    def test_swim_event(self):
        self.check("Frente MarFunchal Swim 2026! Inscrições abertas no Complexo Balnear do Lido", True, D(2026, 10, 1), "ignore")

    def test_event_with_restricted_spaces(self):  # Frente MarFunchal 2026-10-01
        self.check("Frente MarFunchal Swim 2026! No próximo sábado o Complexo Balnear do Lido recebe mais uma edição do evento "
                   "Frente Mar Funchal Swim! Nota: alguns espaços irão estar condicionados.", True, D(2026, 10, 1), "review")

    def test_cliff_restricted_is_review(self):
        self.check("A promenade do Lido estará condicionada entre a Ponta Gorda e o Lido.", True, D(2026, 10, 1), "review", [6])

    def test_until_date(self):
        r = classify("O túnel da Doca do Cavacas está encerrado até 15 de janeiro.", True, D(2025, 12, 20))
        self.assertEqual((r["ends"], r["decision"]), ("2026-01-15", "apply"))


if __name__ == "__main__":
    unittest.main()

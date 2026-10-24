#!/usr/bin/env python3
"""Seasonal timetable switch (owner, 2026-10-24: "make sure there are no old timetables as soon as we change time").

Horários do Funchal's "Pico do Areeiro" bus and its summit shuttle run a summer timetable (last trip 19:00) and a
winter one (last trip 18:00, 25 Oct 2026 - 27 Mar 2027; seo_research/facts/pr1_transport.md, operator page). The
other 60 Horários do Funchal lines don't change on that date (their GTFS feed, checked 2026-10-24), and the
Rodoeste / SAM / CAM sheets we transcribed have school-term variants only.

The bot's bus data switches by itself (kb.bus_trip valid_from / valid_to, seed.AREEIRO_BUS). The website is static,
so on the switch date this script replaces the "19:00 (18:00 from 25 Oct)" wording with the winter wording, in the
four pages that carry it (getting-back, pr1-sunrise-transport, areeiro-pedra-rija, pico-do-areeiro-parking; 5
languages, visible text and FAQ schema alike), in the two generators behind the last two, in the bot's
pr1_facts.md and the local facts file. Then it re-runs the generators, bumps dateModified / lastmod, rebuilds
bot/kb.json, reloads the knowledge store's page docs, commits and pushes.

    python3 scripts/season_switch.py            # apply every switch whose date has come (idempotent)
    python3 scripts/season_switch.py --check    # list what would change, change nothing
    --date YYYY-MM-DD (pretend it is that day) and --no-commit (apply and rebuild, no commit/push) are for rehearsals.

Cron runs it at 00:01 on the switch dates. Add the next season (summer from 28 Mar 2027) to SWITCHES before then.
"""
import datetime
import os
import subprocess
import sys
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TZ = zoneinfo.ZoneInfo("Atlantic/Madeira")
PY = sys.executable

P = {  # page families: path for each language
    "back": {"en": "getting-back.html", **{l: f"{l}/getting-back.html" for l in ("pt", "fr", "de", "pl")}},
    "sunrise": {"en": "pr1-sunrise-transport/index.html",
                **{l: f"{l}/pr1-sunrise-transport/index.html" for l in ("pt", "fr", "de", "pl")}},
}
GEN_PEDRA, GEN_PARK = "scripts/gen_pedrarija_page.py", "scripts/gen_parking_page.py"
FACTS_BOT, FACTS_LOCAL = "bot/pr1_facts.md", "seo_research/facts/pr1_transport.md"

# date -> [(file, old, new)]; every old string must be found (else the run fails loud, nothing is committed)
SWITCHES = {
    "2026-10-25": [
        # getting back (hand-written; FAQ schema text = visible text, so one replace covers both)
        (P["back"]["en"], "comes back down at 12:15 and 19:00 (18:00 in winter).", "comes back down at 12:15 and 18:00."),
        (P["back"]["en"], "Summer timetable (to 24 Oct 2026)", "Winter timetable (to 27 Mar 2027)"),
        (P["back"]["en"], "<td>19:00 (18:00 from 25 Oct)</td>", "<td>18:00</td>"),
        (P["back"]["en"], "14:10–19:00 (18:00 in winter)", "14:10–18:00"),
        (P["back"]["pt"], "volta a descer às 12:15 e às 19:00 (18:00 no inverno).", "volta a descer às 12:15 e às 18:00."),
        (P["back"]["pt"], "Horário de verão (até 24 out 2026)", "Horário de inverno (até 27 mar 2027)"),
        (P["back"]["pt"], "<td>19:00 (18:00 a partir de 25 out)</td>", "<td>18:00</td>"),
        (P["back"]["pt"], "14:10–19:00 (18:00 no inverno)", "14:10–18:00"),
        (P["back"]["fr"], "redescend à 12h15 et 19h00 (18h00 en hiver).", "redescend à 12h15 et 18h00."),
        (P["back"]["fr"], "Horaire d'été (jusqu'au 24 oct. 2026)", "Horaire d'hiver (jusqu'au 27 mars 2027)"),
        (P["back"]["fr"], "<td>19h00 (18h00 à partir du 25 oct.)</td>", "<td>18h00</td>"),
        (P["back"]["fr"], "14h10–19h00 (18h00 en hiver)", "14h10–18h00"),
        (P["back"]["de"], "fährt um 12:15 und 19:00 (im Winter 18:00) wieder hinunter.", "fährt um 12:15 und 18:00 wieder hinunter."),
        (P["back"]["de"], "Sommerfahrplan (bis 24. Okt. 2026)", "Winterfahrplan (bis 27. März 2027)"),
        (P["back"]["de"], "<td>19:00 (ab 25. Okt. 18:00)</td>", "<td>18:00</td>"),
        (P["back"]["de"], "14:10–19:00 (im Winter 18:00)", "14:10–18:00"),
        (P["back"]["pl"], "a wraca o 12:15 i 19:00 (zimą 18:00).", "a wraca o 12:15 i 18:00."),
        (P["back"]["pl"], "Rozkład letni (do 24 paź 2026)", "Rozkład zimowy (do 27 mar 2027)"),
        (P["back"]["pl"], "<td>19:00 (od 25 paź 18:00)</td>", "<td>18:00</td>"),
        (P["back"]["pl"], "14:10–19:00 (zimą do 18:00)", "14:10–18:00"),
        # sunrise transport (hand-written)
        (P["sunrise"]["en"], "Down from the summit at 12:15 and 19:00 (18:00 from 25 Oct 2026)", "Down from the summit at 12:15 and 18:00"),
        (P["sunrise"]["en"], "The summer timetable runs until 24 October 2026; the winter timetable from 25 October 2026 to 27 March 2027.",
         "The winter timetable runs until 27 March 2027."),
        (P["sunrise"]["en"], "12:15 and 19:00 from the Radar roundabout (18:00 instead of 19:00 in winter), back at the Teleférico at 13:00 and 19:45.",
         "12:15 and 18:00 from the Radar roundabout, back at the Teleférico at 13:00 and about 18:45."),
        (P["sunrise"]["en"], "(06:40–12:15 and 14:10–19:00, 18:00 in winter)", "(06:40–12:15 and 14:10–18:00)"),
        (P["sunrise"]["pt"], "Desce do cume às 12:15 e às 19:00 (18:00 a partir de 25 out. 2026)", "Desce do cume às 12:15 e às 18:00"),
        (P["sunrise"]["pt"], "O horário de verão vigora até 24 de outubro de 2026; o de inverno de 25 de outubro de 2026 a 27 de março de 2027.",
         "O horário de inverno vigora até 27 de março de 2027."),
        (P["sunrise"]["pt"], "12:15 e 19:00 da rotunda junto ao Radar (18:00 em vez das 19:00 no inverno), com chegada ao Teleférico às 13:00 e às 19:45.",
         "12:15 e 18:00 da rotunda junto ao Radar, com chegada ao Teleférico às 13:00 e por volta das 18:45."),
        (P["sunrise"]["pt"], "(06:40–12:15 e 14:10–19:00, 18:00 no inverno)", "(06:40–12:15 e 14:10–18:00)"),
        (P["sunrise"]["fr"], "Redescend du sommet à 12:15 et 19:00 (18:00 à partir du 25 oct. 2026)", "Redescend du sommet à 12:15 et 18:00"),
        (P["sunrise"]["fr"], "L'horaire d'été court jusqu'au 24 octobre 2026 ; l'horaire d'hiver du 25 octobre 2026 au 27 mars 2027.",
         "L'horaire d'hiver court jusqu'au 27 mars 2027."),
        (P["sunrise"]["fr"], "12:15 et 19:00 depuis le rond-point du Radar (18:00 au lieu de 19:00 en hiver), retour au Teleférico à 13:00 et 19:45.",
         "12:15 et 18:00 depuis le rond-point du Radar, retour au Teleférico à 13:00 et vers 18:45."),
        (P["sunrise"]["fr"], "(06:40–12:15 et 14:10–19:00, 18:00 en hiver)", "(06:40–12:15 et 14:10–18:00)"),
        (P["sunrise"]["de"], "Talfahrt vom Gipfel um 12:15 und 19:00 (ab 25. Okt. 2026 um 18:00)", "Talfahrt vom Gipfel um 12:15 und 18:00"),
        (P["sunrise"]["de"], "Der Sommerfahrplan gilt bis 24. Oktober 2026, der Winterfahrplan vom 25. Oktober 2026 bis 27. März 2027.",
         "Der Winterfahrplan gilt bis 27. März 2027."),
        (P["sunrise"]["de"], "12:15 und 19:00 ab dem Radar-Kreisel (im Winter 18:00 statt 19:00), Ankunft am Teleférico um 13:00 und 19:45.",
         "12:15 und 18:00 ab dem Radar-Kreisel, Ankunft am Teleférico um 13:00 und gegen 18:45."),
        (P["sunrise"]["de"], "(06:40–12:15 und 14:10–19:00, im Winter bis 18:00)", "(06:40–12:15 und 14:10–18:00)"),
        (P["sunrise"]["pl"], "Zjazd ze szczytu o 12:15 i 19:00 (od 25 paź 2026 o 18:00)", "Zjazd ze szczytu o 12:15 i 18:00"),
        (P["sunrise"]["pl"], "Rozkład letni obowiązuje do 24 października 2026, zimowy od 25 października 2026 do 27 marca 2027.",
         "Rozkład zimowy obowiązuje do 27 marca 2027."),
        (P["sunrise"]["pl"], "12:15 i 19:00 z ronda przy Radarze (zimą 18:00 zamiast 19:00), przyjazd na Teleférico o 13:00 i 19:45.",
         "12:15 i 18:00 z ronda przy Radarze, przyjazd na Teleférico o 13:00 i około 18:45."),
        (P["sunrise"]["pl"], "(06:40–12:15 i 14:10–19:00, zimą do 18:00)", "(06:40–12:15 i 14:10–18:00)"),
        # Pedra Rija generator (pages rewritten by running it)
        (GEN_PEDRA, "19:00 (18:00 winter, from 25 Oct)", "18:00 (winter timetable to 27 Mar 2027; 19:00 in summer)"),
        (GEN_PEDRA, "last bus down at 19:00, or 18:00 with the winter timetable from 25 October.", "last bus down at 18:00."),
        (GEN_PEDRA, "último autocarro para baixo às 19:00, ou 18:00 com o horário de inverno a partir de 25 de outubro.",
         "último autocarro para baixo às 18:00."),
        (GEN_PEDRA, "dernier bus de descente à 19:00, ou 18:00 avec l'horaire d'hiver à partir du 25 octobre.", "dernier bus de descente à 18:00."),
        (GEN_PEDRA, "letzter Bus hinunter um 19:00, ab 25. Oktober mit dem Winterfahrplan um 18:00.", "letzter Bus hinunter um 18:00."),
        (GEN_PEDRA, "ostatni autobus w dół o 19:00, a od 25 października, w rozkładzie zimowym, o 18:00.", "ostatni autobus w dół o 18:00."),
        # parking generator
        (GEN_PARK, "14:10-19:00, last trip 18:00 from\n                 25 Oct 2026 (winter timetable)",
         "14:10-18:00 (winter timetable to\n                 27 Mar 2027; 19:00 in summer)"),
        (GEN_PARK, "14:10–19:00 (last trip 18:00 from 25 October, with the winter timetable)", "14:10–18:00"),
        (GEN_PARK, "das 14:10 às 19:00 (última viagem às 18:00 a partir de 25 de outubro, com o horário de inverno)", "das 14:10 às 18:00"),
        (GEN_PARK, "de 14:10 à 19:00 (dernier départ à 18:00 à partir du 25 octobre, avec l'horaire d'hiver)", "de 14:10 à 18:00"),
        (GEN_PARK, "14:10–19:00 (letzte Fahrt 18:00 ab 25. Oktober, mit dem Winterfahrplan)", "14:10–18:00"),
        (GEN_PARK, "14:10–19:00 (ostatni kurs o 18:00 od 25 października, w rozkładzie zimowym)", "14:10–18:00"),
        # the bot's PR1 facts (knowledge store doc) and the local facts file
        (FACTS_BOT, "**12:15** and **19:00** (the 19:00 is **18:00** in the winter\n    timetable, from 25 Oct 2026 to 27 Mar 2027).",
         "**12:15** and **18:00** (winter timetable, until 27 Mar 2027; the last\n    trip is 19:00 in summer)."),
        (FACTS_LOCAL, "- **12:15** and **19:00** from the Radar roundabout. The 19:00 trip runs at **18:00 in winter**.",
         "- **12:15** and **18:00** from the Radar roundabout (winter timetable, to 27/03/2027; 19:00 in summer)."),
        (FACTS_LOCAL, "- **Every 15 min, 06:40–12:15 and 14:10–19:00** (18:00 in winter).",
         "- **Every 15 min, 06:40–12:15 and 14:10–18:00** (winter timetable; 19:00 in summer)."),
    ],
}


def sh(*cmd, check=True):
    print("$", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True)


def main():
    check_only, no_commit = "--check" in sys.argv, "--no-commit" in sys.argv
    today = (sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv
             else datetime.datetime.now(TZ).date().isoformat())
    due = [(d, r) for d, rs in sorted(SWITCHES.items()) if d <= today for r in rs]
    todo, missing = [], []
    for d, (path, old, new) in due:
        text = open(os.path.join(ROOT, path), encoding="utf-8").read()
        if old in text:
            todo.append((d, path, old, new, text.count(old)))
        elif new not in text:
            missing.append((d, path, old))
    print(f"{today}: {len(due)} replacements due, {len(todo)} to apply, {len(due) - len(todo) - len(missing)} already done")
    for d, path, old, _new, n in todo:
        print(f"  {d} {path} ×{n}: {old[:70]!r}")
    if missing:
        for d, path, old in missing:
            print(f"  MISSING {d} {path}: {old[:90]!r}")
        sys.exit("season switch: some texts were not found (pages changed?); nothing applied")
    if check_only or not todo:
        return
    dirty = [l for l in sh("git", "status", "--porcelain", "--untracked-files=no").stdout.splitlines() if l.strip()]
    if dirty:
        sys.exit(f"season switch: the working tree has uncommitted changes, not touching it: {dirty[:5]}")
    if not no_commit:
        sh("git", "pull", "-q", "--rebase", "origin", "main")
    for _d, path, old, new, _n in todo:
        p = os.path.join(ROOT, path)
        text = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(text.replace(old, new))
    gens = {path for _d, path, *_ in todo if path in (GEN_PEDRA, GEN_PARK)}
    for g in sorted(gens):
        sh(PY, g)
    sh(PY, "scripts/bump_dates.py")
    sh(PY, "scripts/check_site.py")
    sh(PY, "bot/build_kb.py")
    if no_commit:
        print(sh("git", "status", "--short").stdout)
        return
    sh(PY, "backend/load.py", "docs", check=False)
    sh("git", "add", "-u")
    msg = ("Season switch " + today + " (scripts/season_switch.py): Pico do Areeiro bus and summit shuttle on the winter "
           "timetable, last trip 18:00 (getting back, sunrise transport, Pedra Rija, parking; 5 languages; bot PR1 facts).")
    sh("git", "commit", "-q", "-m", msg)
    sh("git", "push", "-q", "origin", "main")
    print("pushed:", sh("git", "log", "--oneline", "-1").stdout.strip())


if __name__ == "__main__":
    main()

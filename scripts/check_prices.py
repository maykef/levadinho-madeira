#!/usr/bin/env python3
"""Daily price watch (owner, 2026-10-21): every tariff, ticket and official transport price the site states is
checked once a day against the operator's own page. Taxis are excluded by the owner's rule (visitors confirm the
fare with the driver; our taxi figures are marked indicative on the pages).

What it does:
  - fetches each registered source and extracts the prices/times with a strict pattern;
  - compares them with the canonical snapshot (reports/data/prices.json, git-ignored; --init writes it);
  - all good -> one OK line in reports/data/price_watch.log;
  - a value CHANGED -> writes reports/data/price_alert.md naming the source, the old and the new value and the
    pages that state it, logs PRICE CHANGE, and exits 2. The alert file is read at the start of the next Claude
    session and the pages are corrected immediately (the generators' literals, then re-run; owner's rule).
  - a pattern STOPPED MATCHING (site redesign, fetch error) -> alert too (exit 2): a price we can't verify is as
    bad as a wrong one. The snapshot is never updated automatically; it is updated when the pages are fixed
    (run with --init again).

Legal rates (Portaria 801/2025 trail fees, Portaria 48/2026 parking/Botanical entry, Portaria 591/2025 Cabo
Girão) are not scraped: they change by new Portaria, and the 2027-2029 steps are already printed in the law.
The year rollover is caught by the 'year' check below.

    python3 scripts/check_prices.py          # daily run (collect job price_watch)
    python3 scripts/check_prices.py --init   # (re)write the snapshot from what the sites say now
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "reports", "data", "prices.json")
LOG = os.path.join(ROOT, "reports", "data", "price_watch.log")
ALERT = os.path.join(ROOT, "reports", "data", "price_alert.md")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) levadinho-price-watch (hello@levadinho-madeira.com)"}


def text(url):
    h = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read().decode("utf-8", "replace")
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def carreiros(t):
    m = re.search(r"1 Person\D{0,40}?([\d]+),\d\d\s*EUR.*?2 Persons\D{0,40}?([\d]+),\d\d\s*EUR.*?3 Persons\D{0,40}?([\d]+),\d\d\s*EUR", t)
    d = re.search(r"Monday to Saturday\s*From\s*(\d\d:\d\d)\s*to\s*(\d\d:\d\d)", t, re.I)
    if not (m and d):
        return None
    return {"sled_1": m.group(1), "sled_2": m.group(2), "sled_3": m.group(3), "days_hours": f"Mon-Sat {d.group(1)}-{d.group(2)}"}


def cablecar(t):
    m = re.search(r"Round trip\s*(\d+)\s*€\s*One way\s*(\d+)\s*€", t, re.I)
    if not m:
        return None
    return {"return": m.group(1), "one_way": m.group(2)}


def montepalace(t):
    m = re.findall(r"(\d+)\s*€", t)
    return {"adult": m[0]} if m else None


def gardencable(t):
    m = re.search(r"Adult\s*([\d.]+)\s*€\s*([\d.]+)\s*€.*?Child[^€]*?([\d.]+)\s*€\s*([\d.]+)\s*€", t)
    c = re.search(r"CABLE CAR & BOTANICAL GARDEN.*?Adult\s*([\d.]+)\s*€\s*([\d.]+)\s*€", t, re.I | re.S)
    if not (m and c):
        return None
    return {"one_way": m.group(1).rstrip("0").rstrip("."), "round": m.group(2).rstrip("0").rstrip("."),
            "combo_one_way": c.group(1).rstrip("0").rstrip("."), "combo_round": c.group(2).rstrip("0").rstrip(".")}


def hfbus(t):
    fare = re.search(r"3,00\s*€", t) and "3,00"
    shuttle = re.search(r"1,20\s*€", t) and "1,20"
    # last trip down: 19:00 in summer, 18:00 in winter (25 Oct–27 Mar; scripts/season_switch.py moves the pages)
    times = [x for x in ("06:00", "06:45", "13:30", "14:15", "12:15") if x in t] + \
            [x for x in ("18:00", "19:00") if re.search(rf"{x}\s*(?:a\))?\s*-\s*Pico do Areeiro", t)]
    if not (fare and shuttle and len(times) == 6):
        return None
    return {"fare": fare, "shuttle": shuttle, "times": ",".join(times)}


CHECKS = [
    # key, url, parser, pages that state these values
    ("carreiros_toboggan", "https://www.carreirosdomonte.com/v3/en/prices.php", carreiros,
     ["/monte/", "/two-days-in-madeira/"]),
    ("monte_cable_car", "https://madeiracablecar.com/en/", cablecar,
     ["/monte/", "/one-day-in-madeira/", "/two-days-in-madeira/", "/madeira-cruise-port/", "/funchal/"]),
    ("monte_palace", "https://montepalacemadeira.com/visita/", montepalace,
     ["/monte/", "/one-day-in-madeira/", "/two-days-in-madeira/"]),
    ("garden_cable_car", "https://telefericojardimbotanico.com/en/prices.html", gardencable,
     ["/monte/", "/two-days-in-madeira/"]),
    ("hf_areeiro_bus", "https://www.horariosdofunchal.pt/index.php/viajar/pico-do-areeiro", hfbus,
     ["/areeiro-pedra-rija/", "/pr1-sunrise-transport/", "/pico-do-areeiro-parking/"]),
]


def year_check():
    """Portaria 48/2026 and 801/2025 rates are printed per year; on 1 Jan the pages must move to the next step."""
    y = time.gmtime().tm_year
    return {"site_prices_year": "2026"} if y == 2026 else None


def run(init):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    old = json.load(open(STATE)) if os.path.exists(STATE) else {}
    now, problems = {}, []
    for key, url, parse, pages in CHECKS:
        try:
            got = parse(text(url))
        except Exception as e:  # noqa: BLE001  fetch errors are a verification failure, reported not raised
            got = None
            problems.append((key, url, pages, f"fetch failed: {e}", old.get(key)))
        if got is None:
            if not any(p[0] == key for p in problems):
                problems.append((key, url, pages, "pattern stopped matching (page changed?)", old.get(key)))
            continue
        now[key] = got
        if not init and key in old and old[key] != got:
            problems.append((key, url, pages, f"PRICE CHANGE: {old[key]} -> {got}", old[key]))
    yc = year_check()
    if yc is None:
        problems.append(("year_rollover", "-", ["hiking-fees", "parking", "botanical entry", "Cabo Girão"],
                         "new year: apply the Portarias' next-year rates (48/2026 annex II; 801/2025)", None))
    else:
        now.update(yc)

    stamp = time.strftime("%F %T")
    if init:
        json.dump(now, open(STATE, "w"), indent=1, ensure_ascii=False)
        line = f"{stamp} snapshot written: {len(now)} sources"
    elif problems:
        with open(ALERT, "w") as f:
            f.write(f"# PRICE ALERT {stamp}\n\nFix the pages NOW (owner's rule, 2026-10-21), then re-run "
                    f"`python3 scripts/check_prices.py --init`.\n\n")
            for key, url, pages, msg, _was in problems:
                f.write(f"- **{key}** ({url}): {msg}\n  pages: {', '.join(pages)}\n")
        line = f"{stamp} PRICE CHANGE / verify failure: {[p[0] for p in problems]} -> {ALERT}"
    else:
        if os.path.exists(ALERT):
            os.remove(ALERT)
        line = f"{stamp} OK: {len(now)} sources match the site"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")
    return 2 if (problems and not init) else 0


if __name__ == "__main__":
    sys.exit(run("--init" in sys.argv[1:]))

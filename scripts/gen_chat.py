#!/usr/bin/env python3
"""Levadinho's chat at the top of the page (owner, 2026-10-10), on the pilot pages only.

Owner, 2026-10-20: chat only on question-shaped pages; trail pages are factsheets. The 8 trail-code pilot pages
(PR6.8, PR9.1, PR7, PR28, PR13, PR13.1, PR6.6, PR1.3) were removed from the pilot that day; getting-back stays
(it converts ~1 in 4), and new question pages (one-day-in-madeira…) join this list as they are built. × 5 languages.
Each gets <script src="/chat.js?v=20261108" defer> before </body>, between CHAT:START/END markers. The page HTML is otherwise
unchanged (Google indexes the same page); chat.js adds the chat above it only when the bot answers.
Idempotent. `--remove` takes the markers out of every page (to end the pilot).

Storm mode (owner, 2026-11-08): every other page with a live status card (the 37 trail pages incl. PR1) gets the same
script marked data-storm-only: chat.js shows the chat there only during IFCN's island-wide closure, opening with
"all trails are closed". On normal days those pages stay factsheets (owner, 2026-10-20). Re-run after gen_spokes.py.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_DIRS = ["", "pt/", "fr/", "de/", "pl/"]
PILOT = ["getting-back.html", "one-day-in-madeira/index.html", "two-days-in-madeira/index.html", "madeira-cruise-port/index.html",
         "pr1-one-way/index.html", "levadas-by-bus/index.html",  # owner, 2026-10-22: the week's top landings for PT/PL visitors; both question-shaped
         "pico-do-areeiro-weather/index.html", "pr1-sunrise-transport/index.html",  # owner, 2026-10-22: the remaining question-shaped
         "free-walks/index.html", "simplifica-booking/index.html"]  # pages in October's top 15 (chat now covers ~41% of views)
BLOCK = '<!-- CHAT:START (scripts/gen_chat.py) --><script src="/chat.js?v=20261108" defer></script><!-- CHAT:END -->'
BLOCK_STORM = ('<!-- CHAT:START (scripts/gen_chat.py, storm mode only) --><script src="/chat.js?v=20261108" data-storm-only defer>'
               '</script><!-- CHAT:END -->')
MARK = re.compile(r"<!-- CHAT:START.*?<!-- CHAT:END -->", re.S)


def main(remove=False):
    want = {os.path.join(ROOT, d + p) for d in LANG_DIRS for p in PILOT}
    changed = storm = 0
    for f in sorted(set(glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True)) | want):
        if not os.path.isfile(f):
            sys.exit(f"missing pilot page: {f}")
        h = open(f, encoding="utf-8").read()
        new = MARK.sub("", h)
        if f in want and not remove:
            new = new.replace("</body>", BLOCK + "</body>", 1)
        elif not remove and 'id="statusCard"' in new and "/trails/" not in f.replace(ROOT, ""):
            new = new.replace("</body>", BLOCK_STORM + "</body>", 1)
            storm += 1
        if new != h:
            open(f, "w", encoding="utf-8").write(new)
            changed += 1
    print(f"chat {'removed from' if remove else 'on'} {len(want) if not remove else 0} pilot pages, storm-only on {storm} "
          f"trail pages ({changed} files changed)")


if __name__ == "__main__":
    main("--remove" in sys.argv)

#!/usr/bin/env python3
"""Levadinho's chat at the top of the page (owner, 2026-10-10), on the pilot pages only.

Owner, 2026-10-20: chat only on question-shaped pages; trail pages are factsheets. The 8 trail-code pilot pages
(PR6.8, PR9.1, PR7, PR28, PR13, PR13.1, PR6.6, PR1.3) were removed from the pilot that day; getting-back stays
(it converts ~1 in 4), and new question pages (one-day-in-madeira…) join this list as they are built. × 5 languages.
Each gets <script src="/chat.js" defer> before </body>, between CHAT:START/END markers. The page HTML is otherwise
unchanged (Google indexes the same page); chat.js adds the chat above it only when the bot answers.
Idempotent. `--remove` takes the markers out of every page (to end the pilot).
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_DIRS = ["", "pt/", "fr/", "de/", "pl/"]
PILOT = ["getting-back.html", "one-day-in-madeira/index.html", "two-days-in-madeira/index.html", "madeira-cruise-port/index.html"]
BLOCK = '<!-- CHAT:START (scripts/gen_chat.py) --><script src="/chat.js" defer></script><!-- CHAT:END -->'
MARK = re.compile(r"<!-- CHAT:START.*?<!-- CHAT:END -->", re.S)


def main(remove=False):
    want = {os.path.join(ROOT, d + p) for d in LANG_DIRS for p in PILOT}
    changed = 0
    for f in sorted(set(glob.glob(os.path.join(ROOT, "**/*.html"), recursive=True)) | want):
        if not os.path.isfile(f):
            sys.exit(f"missing pilot page: {f}")
        h = open(f, encoding="utf-8").read()
        new = MARK.sub("", h)
        if f in want and not remove:
            new = new.replace("</body>", BLOCK + "</body>", 1)
        if new != h:
            open(f, "w", encoding="utf-8").write(new)
            changed += 1
    print(f"chat {'removed from' if remove else 'on'} {len(want) if not remove else 0} pilot pages ({changed} files changed)")


if __name__ == "__main__":
    main("--remove" in sys.argv)

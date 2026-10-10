#!/usr/bin/env python3
"""Levadinho's chat at the top of the page (owner, 2026-10-10), on the pilot pages only.

Pilot (owner: "trail codes and getting back in all languages"): the 8 trail pages that rank on page one for their bare
code in Search Console (PR6.8, PR9.1, PR7, PR28, PR13, PR13.1, PR6.6, PR1.3) and getting-back, × 5 languages.
Each gets <script src="/chat.js" defer> before </body>, between CHAT:START/END markers. The page HTML is otherwise
unchanged (Google indexes the same page); chat.js adds the chat above it only when the bot answers.
Idempotent. `--remove` takes the markers out of every page (to end the pilot).
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANG_DIRS = ["", "pt/", "fr/", "de/", "pl/"]
PILOT = ["levada-do-paul-ii-um-caminho-para-todos/index.html", "levada-do-caldeirao-verde-um-caminho-para-todos/index.html",
         "levada-do-moinho/index.html", "levada-da-rocha-vermelha/index.html", "fanal/index.html",
         "vereda-da-palha-carga/index.html", "vereda-do-tunel-do-cavalo/index.html", "vereda-da-encumeada/index.html",
         "getting-back.html"]
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

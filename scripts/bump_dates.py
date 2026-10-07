#!/usr/bin/env python3
"""Honest dates for hand edits (LLM audit item J, 2026-10-07).

The daily updater moves "dateModified" and the sitemap <lastmod> only for pages whose status line changed. Hand edits
(copy, tables, generators re-run) never moved them. Run this before committing a hand edit: every published page that
differs from HEAD (or is new) gets "dateModified" = now (Madeira time) and <lastmod> = today.

    python scripts/bump_dates.py            # bump, then list the pages
    python scripts/bump_dates.py --dry-run  # only list them
"""
import datetime, os, subprocess, sys, zoneinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import update_status as u  # noqa: E402  (reuses bump_date_modified / bump_sitemap)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def changed_html():
    git = lambda *a: subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout.split("\n")
    names = set(git("diff", "--name-only", "HEAD")) | set(git("ls-files", "--others", "--exclude-standard"))
    published = set(u.site_pages())
    return sorted(n for n in names if n.endswith(".html") and n in published and os.path.exists(n))


def main():
    os.chdir(ROOT)
    pages = changed_html()
    if "--dry-run" not in sys.argv and pages:
        now = datetime.datetime.now(zoneinfo.ZoneInfo("Atlantic/Madeira"))
        u.bump_date_modified(now.isoformat(timespec="minutes"), pages)
        u.bump_sitemap(now.strftime("%Y-%m-%d"), pages)
    print(f"{len(pages)} changed page(s)" + (" (dry run)" if "--dry-run" in sys.argv else " -> dateModified + lastmod"))
    for p in pages:
        print(" ", p)


if __name__ == "__main__":
    main()

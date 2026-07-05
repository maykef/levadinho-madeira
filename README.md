# Levadinho

A WhatsApp guide for Madeira hikers, and the small website that feeds it.

The site isn't the product — the chatbot is. These static pages exist to
catch people mid-search ("is PR1 open today?", "how do I get back from Achada
do Teixeira?") and hand them off to the bot on WhatsApp. Everything here is
built around one promise: the trail status you read is true *this morning*,
not whatever was true when the page was written.

Two pages so far. `index.html` covers PR1 Vereda do Areeiro — today's status,
what to do when SIMplifica is sold out, how to reschedule. `getting-back.html`
covers the one-way problem: PR1 drops you at Achada do Teixeira, miles from
your car, so it walks through transfers, taxis and the two-car trick.

## The daily updater

`scripts/update_status.py` runs at 06:40 UTC via GitHub Actions. It does four
things:

- Scrapes the official Visit Madeira PR1 page for the status word (OPEN /
  CLOSED / RESTRICTED) and the warning note next to it.
- Fetches summit weather from Open-Meteo, using the ridge elevation (1,818 m)
  so the temperature isn't a coastal reading. Values below −10 °C or above
  30 °C are discarded.
- Rewrites the status block and `<title>` in `index.html`, updates the date in
  `getting-back.html`, and bumps the `lastmod` in `sitemap.xml`.
- Commits and pushes if anything changed.

If the note restricts access ("only between…", "km 1,2"), an OPEN status is
changed to PARTIAL, and the script exits without writing if the badge and note
still contradict each other. Any scrape failure exits non-zero, so a failed
run leaves yesterday's status up instead of publishing garbage.

`scripts/manual_note.txt`, if present, adds a line to the status card — for
things the scrape can't see, like a ranger reporting ice on the summit stairs.

## Running it

Needs Python 3.12 and `requests`. From the repo root:

    python scripts/update_status.py

It edits the HTML in place, so check `git diff` before pushing. The Action
does exactly this on a schedule, plus a commit; you can also trigger it by
hand from the Actions tab.

## Config

Each HTML file has a small CONFIG block at the top — the WhatsApp number and
the analytics code, nothing else. If the WhatsApp buttons are dead, the number
is still the placeholder.

Hosted on GitHub Pages. When it moves to a real domain, the base URL lives in
a few places on purpose (the canonical tags, `sitemap.xml`, `robots.txt`) —
search for the current one and replace it, and add a `CNAME`.

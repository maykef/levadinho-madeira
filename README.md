# Levadinho

A WhatsApp guide for Madeira hikers, and the small website that feeds it:

Four pages so far:

- `index.html` — PR1 Vereda do Areeiro: today's status, sold-out fixes, rescheduling.
- `getting-back.html` — the one-way problem: getting back from Achada do Teixeira.
- `simplifica-from-abroad.html` — booking when the SIMplifica portal won't work from abroad.
- `hiking-fees.html` — the 2026 trail fees, passes and exemptions, as a table.

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

Each HTML file has a small CONFIG block at the top — currently just the
analytics code (`goatcounterCode`, plus `lastUpdated` on the article pages). The
WhatsApp buttons that used to live on every page were removed for now, and the
CONFIG's `whatsappNumber` went with them; both come back when the WhatsApp
helpdesk is wired up.

Hosted on GitHub Pages from the `maykef/levadinho-madeira` repo, served at
`https://madeira.maykef.info/` (custom domain in the `CNAME` file). The base URL
lives in a few places on purpose (the canonical tags, `sitemap.xml`,
`robots.txt`) — if it ever changes again, search for the current one and replace
it, and update `CNAME`.

# Levadinho

WhatsApp + web chatbot for Madeira trail questions. This repo is the SEO
landing layer: static pages answering the questions hikers actually google
("Is PR1 open today?", "how do I get back from Achada do Teixeira?"),
refreshed every morning from official sources, each ending in a WhatsApp CTA.

## Pages

| File | Target queries |
|---|---|
| `index.html` | is PR1 open today, PR1 sold out, SIMplifica reschedule |
| `getting-back.html` | PR1 one-way, getting back from Achada do Teixeira |

## Daily updater — `scripts/update_status.py`

Runs at 06:40 UTC via GitHub Actions (`.github/workflows/update.yml`).
Scrapes the official Visit Madeira PR1 page for status + note, pulls summit
weather from Open-Meteo, rewrites the STATUS block and `<title>` in
`index.html`, stamps `getting-back.html`, bumps `sitemap.xml` lastmod.

Hard rules (v3):
1. **Badge never contradicts the note.** If the official note restricts
   access ("only between…", "km 1,2"), an OPEN status is downgraded to
   PARTIAL. A final sanity check refuses to publish a contradictory block.
2. **Weather uses the real ridge elevation (1,818 m)** — without the
   `elevation` param Open-Meteo returns near-coastal temperatures.
   Implausible values (< −10 °C or > 30 °C) are rejected.
3. **Fail loud.** Any scrape failure exits non-zero → red Action →
   yesterday's honest status stays live instead of garbage.
4. `scripts/manual_note.txt` (optional, not committed by the bot) injects a
   human-written line into the status card — e.g. "Rangers report ice near
   the summit stairs."

## Setup checklist

- [ ] Set your real WhatsApp number in the CONFIG block of **both** HTML
      files (placeholder `351900000000` = dead buttons).
- [ ] Enable GitHub Pages (main branch, root).
- [ ] Verify in Google Search Console (verification file included) and
      submit `sitemap.xml`.
- [ ] When you buy a custom domain: add `CNAME`, update the canonical tag
      in each page, every `<loc>` in `sitemap.xml`, and `robots.txt`.

## Next pages to build (highest demand / lowest competition first)

1. PR9 Caldeirão Verde status + "do I need a headlamp"
2. PR6 / 25 Fontes status + parking
3. PR1.2 Achada do Teixeira → Pico Ruivo (the sold-out escape route)
4. Fanal fog forecast ("when is Fanal foggy")
5. German versions of all of the above (hreflang pairs)

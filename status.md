# Project status — Levadinho

_Snapshot: 2026-07-07. Branch `main`, working tree clean._

## Where it stands

A working, live static site on GitHub Pages — now a **hub-and-spoke** trail site
in **four languages** (EN at the root; `fr/`, `de/`, `pl/`):

- **Hub:** `/trails/` — a live "open or closed today?" board for all ~37 paid
  Madeira PR trails.
- **Spokes:** the PR1 flagship (`/`) plus **6 per-trail pages** (25 Fontes,
  Pico Ruivo, Caldeirão Verde, São Lourenço, Balcões, Fanal).

One daily engine (`update_status.py` → `status.json`) drives every status card
and the board; pages render client-side via `status.js` / `dashboard.js`,
localized per page — including the scraped official note (machine-translated to
fr/de/pl). Content/pricing reflect the **April 2026 one-way reopening** and 2026
fees. Strategy is freshness-first — own the volatile "is X open / new fees /
closures" queries, funnelling to the planned Levadinho chatbot (see the
`levadinho-strategy` memory). On Google Search Console (`madeira.maykef.info`
property; homepage indexed).

## Pages (all × en/fr/de/pl)

| Page | Role |
|------|------|
| `/` (`index.html`) | PR1 flagship — live status card, webcam, sold-out/closed help |
| `/trails/` | Dashboard hub — live board of all ~37 trails |
| `/25-fontes/`, `/pico-ruivo/`, `/caldeirao-verde/`, `/sao-lourenco/`, `/balcoes/`, `/fanal/` | Trail spokes (PR6, PR1.2, PR9, PR8, PR11, PR13) |
| `/getting-back.html`, `/simplifica-from-abroad.html`, `/hiking-fees.html` | Evergreen explainers |

**44 URLs** in `sitemap.xml` (with hreflang). Translations are machine-generated
— recommend a native FR/DE/PL proofread before relying on them commercially.

## Automation

- `scripts/update_status.py` (v4) + `.github/workflows/update.yml` — runs
  06:40 UTC daily, scrapes Visit Madeira for trail status and reads official
  IPMA observations for summit weather, writes `status.json` + bumps
  `sitemap.xml`, commits if changed. **v4 (2026-07-07): stopped editing HTML** —
  the status card is now rendered client-side from `status.json` for all
  languages.
- **Weather source switched to IPMA (2026-07-07):** was Open-Meteo (model
  forecast); now the real measured reading from IPMA's Pico do Areeiro station.
  Trade-off: IPMA has no sky/weather code, so the old "clear skies / FOG" phrase
  is replaced by temperature + a humidity-derived "likely in cloud" note.
- **Official note translated (2026-07-07):** the scraped English note is mirrored
  into fr/de/pl via MyMemory (free/keyless, English fallback) and stored as a
  per-language object `{en,fr,de,pl}` in `status.json`, so localized pages show
  the note in their own language (proper nouns preserved).
- Current live status: **PARTIAL** (footpath accessible only Areeiro → Pedra Rija
  Belvedere, km 1,2), last checked 2026-07-07.

- **Dashboard shipped (2026-07-07):** `/trails/` (+ fr/de/pl) — live "open or
  closed today?" board for all ~37 Madeira PR trails, driven by the multi-trail
  engine (one scrape of the Visit Madeira index → `trails[]`, `counts`, 5-region
  IPMA weather in `status.json`). Rendered by `dashboard.js`; search + filter
  chips; photo ribbon uses real self-hosted trail photos (Wikimedia Commons,
  credited in `/img/CREDITS.txt`). Kept at `/trails/` for now (PR1 stays the
  homepage `/`) — could be promoted to the homepage now that spokes exist.

- **Spoke pages (2026-07-07):** `/25-fontes/` (PR6), `/pico-ruivo/` (PR1.2),
  `/caldeirao-verde/` (PR9), `/sao-lourenco/` (PR8), `/balcoes/` (PR11),
  `/fanal/` (PR13) — **6 trails**, each + fr/de/pl (28 pages). Built from
  the PR1 shell: hero photo, live status card (`status.js` `data-trail`),
  trail-facts sidebar, and trail-specific booking / getting-there / alternatives
  content. The engine's `PAGES` map links each dashboard card to its spoke.
  Adding more is cheap: copy the template, set `data-trail`, add to `PAGES`,
  translate, add to sitemap.

## Open items / risks

- [x] **WhatsApp fully removed (2026-07-07):** per decision, all four pages had
  their WhatsApp buttons, sticky bars, `wa.me` JS, click tracking,
  `CONFIG.whatsappNumber`, and copy stripped out (GoatCounter pageview analytics
  kept). **The pages now have no call-to-action** — a replacement (WhatsApp or
  otherwise) still needs designing and building before this is a lead-gen site.
- [x] **GoatCounter analytics live (2026-07-07):** account created at
  `madeira-levadinho.goatcounter.com`; the `goatcounterCode` in every page's
  `CONFIG` was corrected from `levadinho-madeira` to `madeira-levadinho` (the
  account name is reversed). Pageviews now record, respecting the `#skipgc`
  self-exclusion.
- [ ] Article pages (all languages) show a static `CONFIG.lastUpdated` date.
  Since v4 the updater no longer touches HTML, so these dates don't advance.
  Cosmetic — could wire them to `status.json`'s `date` with a small script if it
  matters.
- [ ] Translations are machine-generated (by Claude) — get a native FR/DE/PL
  proofread before using commercially.
- [x] **Domain move complete (2026-07-07):** repo republished on
  `maykef/levadinho-madeira`, served at `https://madeira.maykef.info/` via GitHub
  Pages + `CNAME` + DNS; base URL updated everywhere. The old
  `Levadinho-Madeira` repo **and account** have been deleted.
- [x] **Google Search Console (2026-07-07):** new `https://madeira.maykef.info/`
  URL-prefix property verified (HTML-file method), homepage indexed. Sitemap now
  carries **44 URLs** + hreflang. **To do:** URL Inspection → Request indexing on
  `/trails/` and the 6 spoke pages to speed discovery (Google refetches the
  sitemap on its own). The old github.io property is obsolete.
- [ ] Status scraper depends on the exact wording/structure of the Visit Madeira
  page. If they redesign it, the run fails loud (by design) and status freezes
  at the last good value until fixed.

## Possible next steps

- **Request-index** the dashboard + 6 spokes in Search Console.
- **Levadinho chatbot** — the funnel endpoint. When ready, drop the "add
  Levadinho on WhatsApp" QR/CTA into every page (see `levadinho-strategy` memory).
- More spokes only if search demand justifies (top trails are now covered); the
  closed PR7/PR10/PR20 could be low-effort "is it closed?" targets.
- Consider promoting `/trails/` to the homepage now that spokes exist.
- Native FR/DE/PL proofread of the machine translations.
- Optional: wire the article pages' static `lastUpdated` to `status.json`'s date;
  a `manual_note.txt` workflow for pushing ranger notes.

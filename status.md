# Project status — Levadinho

_Snapshot: 2026-07-08. Branch `main`, working tree clean, pushed._

## Where it stands

A working, live static site on GitHub Pages — a **hub-and-spoke** trail site in
**four languages** (EN at the root; `fr/`, `de/`, `pl/`). As of 2026-07-08,
**every one of the ~37 paid Madeira PR trails on the dashboard now has its own
live-status page.**

- **Hub:** `/trails/` — a live "open or closed today?" board for all ~37 trails.
- **Spokes (37 trail pages):** the PR1 flagship (`/`) plus **36 per-trail pages**:
  - **9 hand-authored** (rich, photo heroes): 25 Fontes, Pico Ruivo, Caldeirão
    Verde, São Lourenço, Balcões, Fanal, Levada do Furado, Levada do Rei,
    Levada dos Cedros.
  - **27 generated** (lightweight, live-status-first) by `scripts/gen_spokes.py`.

One daily engine (`update_status.py` → `status.json`) drives every status card
and the board; pages render client-side via `status.js` / `dashboard.js`,
localized per page — including the scraped official note (machine-translated to
fr/de/pl). Content/pricing reflect the **April 2026 one-way reopening** and 2026
fees. Strategy is freshness-first — own the volatile "is X open / new fees /
closures" queries, funnelling to the planned Levadinho chatbot (see the
`levadinho-strategy` memory). On Google Search Console (`madeira.maykef.info`).

## Pages (all × en/fr/de/pl)

| Page | Role |
|------|------|
| `/` (`index.html`) | PR1 flagship — live status card, sold-out/closed help |
| `/trails/` | Dashboard hub — live board of all ~37 trails |
| 9 hand-authored spokes | 25 Fontes (PR6), Pico Ruivo (PR1.2), Caldeirão Verde (PR9), São Lourenço (PR8), Balcões (PR11), Fanal (PR13), Levada do Furado (PR10), Levada do Rei (PR18), Levada dos Cedros (PR14) |
| 27 generated spokes | every remaining PR trail (Risco, Moinho, Fajã do Rodrigues, Alecrim, Ribeira da Janela, the Caminhos Reais, etc.) via `gen_spokes.py` |
| `/getting-back.html`, `/simplifica-from-abroad.html`, `/hiking-fees.html` | Evergreen explainers |

**164 URLs** in `sitemap.xml` (41 pages × 4 languages, with hreflang).
Translations are machine-generated — recommend a native FR/DE/PL proofread
before relying on them commercially.

## The generator (`scripts/gen_spokes.py`) — added 2026-07-08

One-off (re-runnable) generator for the 27 long-tail spokes. For every PR trail
without a hand-authored spoke it:

- **Scrapes real facts** from each trail's official Visit Madeira page —
  distance, difficulty, duration, altitude, start/end, and route type (via the
  "round trip"/"circular" signals). Nothing is invented; a missing field just
  drops its row.
- Emits a lightweight en/fr/de/pl page from a shared template: live
  `data-trail` card, facts sidebar, and templated booking / getting-there /
  closed / "before you go" sections with the trail name + facts injected.
- Heroes come from a `PHOTOS` map (Wikimedia Commons, credited). **17 of the 27
  long-tail spokes carry a photo**; the other 10 use a plain hero because no
  correct CC-licensed image was found (wrong-subject candidates — info signs, a
  chapel, an archive scan — were rejected on a contact-sheet review).
- Wiring into `PAGES` (updater) and `sitemap.xml` is done by the caller.

Adding a photo to a plain spoke later = one `PHOTOS` entry + the image.

## Automation

- `scripts/update_status.py` (v4) + `.github/workflows/update.yml` — runs
  06:40 UTC daily, scrapes Visit Madeira for trail status + IPMA summit weather,
  writes `status.json` + bumps `sitemap.xml`, commits if changed. Renders no
  HTML (client-side via `status.js`/`dashboard.js`). `PAGES` now has **37
  entries**, so every dashboard card links to its spoke.
- **The daily cron now fires on its own** — confirmed 2026-07-08 (an automatic
  `Daily status update` commit landed unprompted). Earlier in the day it had to
  be kicked manually once because a freshly-added cron takes ~a day to activate.
- Weather from IPMA Pico do Areeiro station (temp + humidity-derived cloud note
  + wind); official note machine-translated to fr/de/pl via MyMemory.
- Current live status: **PR1 PARTIAL** (footpath only Areeiro → Pedra Rija
  Belvedere, km 1,2); board **28 OPEN / 4 PARTIAL / 5 CLOSED**; dated 2026-07-08.

## Fixed this session (2026-07-08)

- **Start/End scrape over-run:** the fact regex ran to end-of-page on
  point-to-point trails, dumping the whole scraped page (nav, newsletter,
  reCAPTCHA JS) into the "getting there" paragraph — 17 trails × 4 langs = 68
  broken pages (e.g. `/levada-do-paul-ii-.../`). Regex now bounded at
  "Max. Altitude" / "How to get there"; regenerated. 0 pages affected now.
- **Wrong ribbon photos:** the dashboard ribbon (and matching spoke heroes)
  showed a boulder for São Lourenço and a moorland road for Areeiro → Ruivo.
  Replaced with the iconic peninsula (Asurnipal) and the PR1 summit ridge
  (Krzysztof Popławski); `CREDITS.txt` + ribbon credit line updated in all 4.

## Open items / risks

- [ ] **No call-to-action.** WhatsApp was fully stripped; pages carry no CTA
  until the Levadinho bot CTA is built. This is still not a lead-gen site yet.
- [ ] **10 long-tail spokes have a plain hero** (no correct CC photo found).
  Could revisit with wider/manual sourcing — but a plain band beats a
  wrong-subject photo.
- [ ] Translations are machine-generated (by Claude) — native FR/DE/PL proofread
  before commercial use. The 27 generated spokes are templated, so their prose
  is uniform across trails (unique facts + status differentiate them).
- [ ] Article pages show a static `CONFIG.lastUpdated` date that no longer
  advances (updater doesn't touch HTML). Cosmetic.
- [ ] Status scraper (both `update_status.py` and `gen_spokes.py` facts) depends
  on Visit Madeira's page wording/structure. A redesign breaks the scrape — the
  daily run fails loud by design; `gen_spokes.py` is a manual re-run.

## Possible next steps

- **Levadinho chatbot** — the funnel endpoint. When ready, drop the "add
  Levadinho on WhatsApp" QR/CTA into every page (see `levadinho-strategy`).
- Photos for the remaining 10 plain spokes (manual sourcing).
- Consider promoting `/trails/` to the homepage now that every trail is covered.
- Native FR/DE/PL proofread; optionally hand-enrich the highest-demand generated
  spokes with bespoke copy.
- Request-index the new pages in Search Console (Google refetches the sitemap
  anyway).

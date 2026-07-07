# Project status — Levadinho

_Snapshot: 2026-07-07. Branch `main`, working tree clean._

## Where it stands

A working, live static site on GitHub Pages with a self-maintaining PR1 status
card **and a live all-trails dashboard** (`/trails/`), now in **four languages**
(EN at the root; `fr/`, `de/`, `pl/`). The daily
updater (v4) writes a language-neutral `status.json` that every homepage renders
via `status.js`, localized per page — including the scraped official note, which
is machine-translated into fr/de/pl. Content and pricing reflect the **April 2026
one-way reopening** and 2026 fees. The site is on Google Search Console (new
`madeira.maykef.info` property; homepage indexed).

## Pages

| Page | State |
|------|-------|
| `index.html` (+ `fr/`,`de/`,`pl/`) | Live. Status card rendered from `status.json` via `status.js`, localized. |
| `getting-back.html` (+ 3 langs) | Live. |
| `simplifica-from-abroad.html` (+ 3 langs) | Live. |
| `hiking-fees.html` (+ 3 langs) | Live. |

Translations (FR/DE/PL) were machine-generated on 2026-07-07 — recommend a
native proofread before relying on them commercially.

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
  chips; photo ribbon uses **placeholder gradients** (swap in real licensed
  photos). Kept at `/trails/` for now (PR1 stays the homepage `/`); promote to
  the homepage once per-trail spoke pages exist.

- **Spoke pages (2026-07-07):** `/25-fontes/` (PR6), `/pico-ruivo/` (PR1.2),
  `/caldeirao-verde/` (PR9), `/sao-lourenco/` (PR8) — each + fr/de/pl. Built from
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
  carries 16 URLs + hreflang — let Google refetch it in the new property and use
  URL Inspection → Request indexing on `/fr/`, `/de/`, `/pl/` to speed discovery.
  The old github.io property is obsolete.
- [ ] Status scraper depends on the exact wording/structure of the Visit Madeira
  page. If they redesign it, the run fails loud (by design) and status freezes
  at the last good value until fixed.

## Possible next steps

- Set the real WhatsApp number and verify the buttons end-to-end.
- Confirm GoatCounter is live; sanity-check the self-exclusion (`#skipgc`).
- Consider more content pages (other popular trails: PR6 25 Fontes,
  PR9 Caldeirão Verde) following the existing template.
- Optional: a `manual_note.txt` workflow/UI for pushing ranger notes.

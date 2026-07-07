# Project status — Levadinho

_Snapshot: 2026-07-07. Branch `main`, working tree clean._

## Where it stands

A working, live static site on GitHub Pages with a self-maintaining PR1 status
card. Four content pages ship; the daily updater (v3) is deployed and running on
schedule. Content and pricing reflect the **April 2026 one-way reopening** and
2026 fees.

## Pages

| Page | State |
|------|-------|
| `index.html` | Live. Status block auto-updated daily. |
| `getting-back.html` | Live. `lastUpdated` stamped by the updater. |
| `simplifica-from-abroad.html` | Live. |
| `hiking-fees.html` | Live. |

## Automation

- `scripts/update_status.py` (v3) + `.github/workflows/update.yml` — runs
  06:40 UTC daily, scrapes Visit Madeira + Open-Meteo, commits if changed.
- Last recorded status update commit: **2026-07-06** (badge currently `PARTIAL`
  — footpath accessible only Areeiro → Pedra Rija Belvedere, km 1,2).

## Open items / risks

- [ ] **WhatsApp number is still the placeholder `351900000000`** across all
  four pages. The core CTA of the whole site is non-functional until this is
  set. Highest-priority fix.
- [ ] **GoatCounter analytics** uses code `levadinho-madeira` — confirm the
  account exists at `levadinho-madeira.goatcounter.com`, else pageviews/clicks
  aren't recorded.
- [ ] The updater stamps `lastUpdated` only in `getting-back.html`.
  `hiking-fees.html` and `simplifica-from-abroad.html` also carry a
  `lastUpdated` field that the script does **not** refresh — they'll show a
  stale date. Decide whether to extend the script or leave them static.
- [x] **Domain move done (2026-07-07):** repo republished on the `maykef`
  account as `maykef/levadinho-madeira`; base URL switched to
  `https://madeira.maykef.info/` across the pages, `sitemap.xml`, `robots.txt`,
  and the scraper UA; `CNAME` added. **Still pending on GitHub's side:** delete
  the old `Levadinho-Madeira/Levadinho` repo, enable Pages + custom domain on
  the new repo, and add the DNS `CNAME madeira → maykef.github.io`.
- [ ] Status scraper depends on the exact wording/structure of the Visit Madeira
  page. If they redesign it, the run fails loud (by design) and status freezes
  at the last good value until fixed.

## Possible next steps

- Set the real WhatsApp number and verify the buttons end-to-end.
- Confirm GoatCounter is live; sanity-check the self-exclusion (`#skipgc`).
- Consider more content pages (other popular trails: PR6 25 Fontes,
  PR9 Caldeirão Verde) following the existing template.
- Optional: a `manual_note.txt` workflow/UI for pushing ranger notes.

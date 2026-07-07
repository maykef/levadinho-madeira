# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**Levadinho** is a tiny static website that answers the questions visitors
actually ask about Madeira's paid, booking-only PR trails — above all
**PR1 Vereda do Areeiro** (Pico do Areeiro → Pico Ruivo). It's intended to feed
a WhatsApp helpdesk, but the WhatsApp call-to-action was **removed on
2026-07-07** (not ready yet); the pages currently carry no CTA and will get one
back when the helpdesk is wired up.

There is no build step, no framework, no dependencies for the site itself. Each
page is a single self-contained `.html` file (inline CSS + inline JS). It is
hosted on **GitHub Pages**.

## Layout

| File | Purpose |
|------|---------|
| `index.html` | PR1 live status (auto-updated daily), sold-out fixes, rescheduling |
| `getting-back.html` | The one-way problem: getting back from Achada do Teixeira |
| `simplifica-from-abroad.html` | Booking when the SIMplifica portal won't work from abroad |
| `hiking-fees.html` | 2026 trail fees, passes, exemptions (as a table) |
| `scripts/update_status.py` | Daily status scraper/updater (Python 3.12, `requests`) |
| `.github/workflows/update.yml` | Cron that runs the updater at 06:40 UTC daily |
| `sitemap.xml`, `robots.txt` | SEO |
| `googleea2064b7684c2bab.html` | Google Search Console site-verification token — do not delete |

## The daily updater (`scripts/update_status.py`)

Runs at 06:40 UTC via GitHub Actions (`workflow_dispatch` also allows manual
runs from the Actions tab). What it does:

1. Scrapes the official Visit Madeira PR1 page for the status word
   (`OPEN` / `CLOSED` / `RESTRICTED`→`PARTIAL`) and the official warning note.
2. Reads **official measured** summit weather from IPMA's Pico do Areeiro
   observation station (`1210974`, keyless open-data API). IPMA carries no sky
   code, so it reports temperature + a humidity-derived "likely in cloud" note
   + wind (falling back to neighbouring station `1210973` when the summit wind
   sensor reports the `-99` "missing" sentinel). `-99` fields and temps
   `< -10 °C` / `> 30 °C` are rejected → generic fallback line.
3. Rewrites the `<!-- STATUS:BEGIN … STATUS:END -->` block and `<title>` in
   `index.html`, stamps `lastUpdated` in `getting-back.html`, bumps `<lastmod>`
   in `sitemap.xml`.
4. The Action commits and pushes only if something changed.

### Invariants — do not break these

- **The badge must never contradict the note.** An `OPEN` badge with a
  restrictive note (`only`, `between`, `km 1,2`, …) is downgraded to `PARTIAL`.
  `assert_not_contradictory` is a final gate that exits non-zero rather than
  publish a "green but restricted" lie.
- **Fail loud.** Any scrape failure exits non-zero → red Action → yesterday's
  honest status stays live instead of publishing garbage. Do not add
  try/except that swallows scrape errors.
- The `STATUS:BEGIN…END` block in `index.html` is machine-written — **do not
  hand-edit it**; edit `build_block()` instead.
- `scripts/manual_note.txt` (optional, not committed) injects a human-written
  line into the status card — for things the scrape can't see (e.g. a ranger
  reporting ice).

Run locally from the repo root (edits HTML in place — check `git diff` first):

```
python scripts/update_status.py
```

## Conventions

- Each page carries a small `CONFIG` block at the very top. It currently holds
  just `goatcounterCode` (plus `lastUpdated` on the three article pages). The
  old `whatsappNumber` was removed with the WhatsApp buttons; add it back here
  when the helpdesk returns.
- Analytics is **GoatCounter**, loaded only when not self-excluded. Visiting any
  page with `#skipgc` sets a localStorage flag so your own device is never
  counted; `#countme` undoes it.
- Shared visual language: cream `--paper`, ink green, and the yellow/red
  **waymark stripe** (the paint marks on Madeira's rocks). Reuse the existing
  CSS variables and the `.waymark`, `.wa-btn`, `.fact`, `.opt` patterns rather
  than inventing new styles.
- Every page has FAQ `schema.org` JSON-LD in the head — keep it in sync with the
  visible copy when you change facts.
- Pages cross-link via a "Next steps" list. Keep those links working when adding
  or renaming pages, and add new pages to `sitemap.xml`.

## The base URL

The site is served at **`https://madeira.maykef.info/`** — a subdomain of the
owner's main domain, hosted from the `maykef/levadinho-madeira` repo via GitHub
Pages (custom domain set in the `CNAME` file). This base URL is repeated on
purpose in the canonical/og tags, `sitemap.xml`, and `robots.txt`. If it ever
changes again: search-and-replace the base URL everywhere and update `CNAME`.

A subdomain is used (not the apex `maykef.info`) so the project never collides
with the owner's main site at the root of that domain.

## Facts to keep accurate (2026)

These are the substance of the site; verify against official sources before
changing them:

- PR1 is **one-way** since the April 2026 reopening: Areeiro → Ruivo only, you
  finish at Achada do Teixeira (no bus there).
- PR1 fee: **€10.50** full traverse, **€4.50** for the Areeiro–Pedra Rija
  section when only that is open. Standard PR trails: **€4.50** (operator €3).
  PR1 via operator: **€7**. Under-12s, residents, and 60%+ disability are exempt
  but must still be on the booking. Parking ~€4.00/hour.
- Booking is **SIMplifica, online-only**; hiking without a valid ticket is an
  infraction with fines reported up to **€250**.

## Git

Branch is `main`; commits push straight to it (the Action commits as
`levadinho-bot`). Don't commit or push unless the user asks.

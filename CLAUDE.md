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
| `index.html` | English homepage: PR1 live status card, sold-out fixes, rescheduling |
| `getting-back.html` | The one-way problem: getting back from Achada do Teixeira |
| `simplifica-from-abroad.html` | Booking when the SIMplifica portal won't work from abroad |
| `hiking-fees.html` | 2026 trail fees, passes, exemptions (as a table) |
| `fr/`, `de/`, `pl/` | Full French/German/Polish translations of all four pages |
| `status.json` | Live data written daily: PR1 flagship fields (top-level) **plus** `counts`, `regions` (weather) and `trails[]` for the dashboard |
| `status.js` | Renders the single-trail status card (PR1 pages) from `status.json`, localized by `<html lang>` |
| `dashboard.js` | Renders the trails dashboard (board + weather strip + counts + search/filter) from `status.json`, localized |
| `trails/` (+ `fr/`,`de/`,`pl/`) | The live "Madeira trails: open or closed today?" dashboard — the hub |
| `scripts/update_status.py` | Daily status scraper/updater (Python 3.12, `requests`) |
| `.github/workflows/update.yml` | Cron that runs the updater at 06:40 UTC daily |
| `sitemap.xml`, `robots.txt` | SEO (sitemap carries hreflang alternates for all 16 URLs) |
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
3. Scrapes the Visit Madeira hiking **index** (one request → every PR trail's
   Open/Restricted/Closed status, parsed from the embedded JSON) and reads five
   regional IPMA stations, then writes `status.json`: the PR1 flagship fields
   (status; note translated to fr/de/pl via MyMemory with English fallback;
   structured weather; timestamp) **plus** `counts`, `regions`, and `trails[]`
   for the dashboard. PR1's own status/note override the coarse index value with
   our detailed scrape. Bumps `<lastmod>` in `sitemap.xml`; edits **no HTML** —
   per-trail cards render via `status.js`, the dashboard via `dashboard.js`.
4. The Action commits and pushes only if something changed (`status.json` +
   `sitemap.xml`).

### Invariants — do not break these

- **The badge must never contradict the note.** An `OPEN` badge with a
  restrictive note (`only`, `between`, `km 1,2`, …) is downgraded to `PARTIAL`.
  `assert_not_contradictory` is a final gate that exits non-zero rather than
  publish a "green but restricted" lie.
- **Fail loud on the status scrape.** Any failure there exits non-zero → red
  Action → yesterday's honest `status.json` stays live instead of garbage. Do
  not add try/except that swallows scrape errors. Weather and note-translation
  are the deliberate exceptions — they degrade gracefully (weather →
  `{"ok": false}`, note-translation → English fallback) so a transient IPMA or
  MyMemory outage never blanks the whole card.
- The status card is **rendered client-side** by `status.js` from `status.json`
  — don't hard-code status into any homepage's HTML. To change wording or add a
  language, edit the `LANGS` dictionary in `status.js`; to change the data
  shape, edit the updater and `status.js` together. Each homepage keeps a
  plain-text fallback inside `#statusCard` for no-JS.
- `scripts/manual_note.txt` (optional, not committed) injects a human-written
  line into the status card (lands in `status.json` as `manual_note`) — for
  things the scrape can't see (e.g. a ranger reporting ice).

Run locally from the repo root (writes `status.json`, bumps `sitemap.xml` —
check `git diff` first):

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
  CSS variables and the `.waymark`, `.fact`, `.opt` patterns rather than
  inventing new styles.
- **Multilingual (en/fr/de/pl).** English lives at the root; `fr/`, `de/`, `pl/`
  mirror all four pages. Every page has a language switcher (`.langs`), five
  `hreflang` alternates in the head, and a self-referencing canonical. When you
  add/rename a page or change copy, update **all four languages**, the switcher
  links, the hreflang blocks, and `sitemap.xml`. Internal links stay relative so
  they resolve within each language folder. Machine translations — flag for
  native review before relying on them commercially.
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

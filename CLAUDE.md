# CLAUDE.md

Guidance for Claude Code when working in this repository.

## ▶ First thing, once per day — the daily SEO report sequence

**Once per calendar day**, at the start of the first session, ask: **"Do you want the full daily
report sequence?"** Ask it in the same message as the bot question below.
- **Once a day only:** run `cat reports/.asked 2>/dev/null`. If it holds today's date (`date +%F`), don't ask.
  Otherwise ask, then write today's date into it (`date +%F > reports/.asked`) whatever the answer.
- **No** → carry on.
- **Yes** → run the sequence:
  1. **Data:** check `reports/data/daily_sweep.log` for today's run (cron 05:30 runs `reports/daily_sweep.sh`).
     If it's missing, ask the owner to type `! bash reports/daily_sweep.sh` (about 20 min). Claude can't run it,
     because the Firecrawl key lives in another project's env file that auto mode won't let Claude load.
  2. **Search Console:** ask the owner for today's exports (Performance → last 7 days and last 28 days:
     Queries, Pages, Countries, Devices, Chart). Save them to `google_search_console/<date>_last7d/` (or `_last28d/`).
  3. **Build:** `python3 reports/build_daily.py` → `reports/data/<date>/auto_summary.md` (rankings from Funchal
     vs the previous day, share of expected clicks per language, competitor movers and new top-3 entrants,
     new autocomplete terms we don't track, Search Console, Lighthouse).
  4. **Write `reports/<date>_daily_report.md`:** what changed, Levadinho's positions, the competitors' ranking,
     new search terms we're missing, what Search Console shows, then **proposed fixes** (ranked by impact,
     each tied to a keyword and a page, all 5 languages). **Never edit pages until the owner approves the fixes.**
  - `reports/`, `google_search_console/` and `seo_research/` are git-ignored: never commit them (GitHub Pages
    would publish them).
  - Tracked keywords: `seo_research/keywords/keywords_v2.json` (146 = 13 core + 81 from autocomplete, × 5
    languages). Funchal is the primary location. Add new keywords there when the report finds them.
  - Cost: about 290 Firecrawl credits a day (+ about 180 on Mondays for the home-country check).

## ▶ At the start of every session — ask about the Levadinho bot

Before anything else, ask the user: **"Do you want the Levadinho WhatsApp bot up and running?"**

- **No** → leave it off and carry on.
- **Yes** →
  1. **Check the GPU first:** run `nvidia-smi` (memory used and compute processes) and `docker ps`. Tell the user what is running and whether the GPU is busy. The model needs about 85 GB of the 96 GB card, so any other large job means busy.
  2. **If the GPU is busy, stop and report.** Don't stop other people's jobs or containers (epiproc etc.).
  3. **If the GPU is free,** run `bot/start.sh`. It loads the model (about 2 min), starts the webhook (which also serves the audio guide), makes sure the Tailscale Funnel route `/levadinho` is up, points Meta's webhook at that permanent URL, and checks the access token.
  4. **Report the result.** If it warns that the access token was rejected, the 24 h test token has expired: the user must generate a new one in Meta (WhatsApp → Step 1 Try it out → Generate token) and save it with
     `read -rsp "Paste WA token: " T && sed -i "s|^WA_TOKEN=.*|WA_TOKEN=$T|" bot/.env && unset T`.
     Then restart the webhook: `bot/stop.sh` stops everything, so for the token alone use `kill $(cat bot/app.pid)` and re-run `bot/start.sh`.
- **To shut down and free the GPU:** `bot/stop.sh`.
- **"Restart the bot/server" = full restart:** `bot/stop.sh`, show `nvidia-smi` with the GPU vacated,
  `bot/start.sh`, show it reloaded. Never a webhook-only restart unless you say so explicitly.
- **A watchdog** (`bot/watchdog.sh`, cron every 5 min) checks the webhook, the Funnel, Meta's API and the model
  while `bot/.running` exists, logs to `bot/logs/watchdog.log`, and after 3 failures does a full
  restart (max once an hour). Old webhook logs are kept in `bot/logs/`.

## What this is

**Levadinho** is a static website answering the questions visitors actually ask
about Madeira's paid, booking-only PR trails. It's a **hub-and-spoke** site:

- **Hub** — the homepage `/`, a live "open or closed today?" board for all ~37 trails.
  (It lived at `/trails/` until 2026-09-28; the old `/trails/` URLs are now forwarding stubs.)
- **Spokes** — the PR1 flagship (`/pr1/`) plus a per-trail page for **every one of the
  ~37 trails**, each with a live status card. **9 are hand-authored** (rich, with
  photo heroes: 25 Fontes, Pico Ruivo, Caldeirão Verde, São Lourenço, Balcões,
  Fanal, Levada do Furado, Levada do Rei, Levada dos Cedros); the other **27 are
  generated** (lightweight, live-status-first) by `scripts/gen_spokes.py`.
- **Guides** — answer pages for the other target queries: fees, booking (SIMplifica
  step by step, and from abroad), "do I need a permit", getting back from Pico Ruivo,
  PR1 sunrise transport, Pico do Areeiro weather/webcam, best levadas, easy levadas
  without vertigo, levadas with tunnels. The query → page map is in
  `seo_research/SEO_Plan.md` (local only).

**Strategy (why it exists):** own the *volatile, novel* search queries — "is X
open today", "new 2026 fees", closures, booking — where daily-updated freshness
beats years-old static guides. That traffic is meant to funnel to **Levadinho**,
a planned LLM chatbot on WhatsApp (added by QR) — see the `levadinho-strategy`
memory. Since 2026-09-30 **every page carries the "Ask Levadinho on WhatsApp" block**
(written by `scripts/gen_cta.py`, see Conventions). The bot itself lives in `bot/` (see below).

No build step, no framework. Pages are self-contained `.html` (inline CSS + JS),
sharing only `/status.json` (data), `/status.js` + `/dashboard.js` (render), and
`/img/` (photos) and `/trail_extras.json` (tunnel/exposure data for the dashboard filters).
Hosted on **GitHub Pages**, in **five languages** (en at the root; `pt/`, `fr/`, `de/`, `pl/`).

## Layout

| File | Purpose |
|------|---------|
| `index.html` | English homepage = the live trails dashboard (the hub) |
| `pr1/` | The PR1 flagship: detailed live status card, sold-out fixes, rescheduling |
| `getting-back.html` | The one-way problem: getting back from Achada do Teixeira |
| `simplifica-from-abroad.html` | Booking when the SIMplifica portal won't work from abroad |
| `hiking-fees.html` | 2026 trail fees, passes, exemptions (as a table) |
| `do-i-need-a-permit/` | "Do I need a permit for levada walks?": the three kinds of walk (IFCN-booked PR trails / PR trails run by others / unclassified levadas) |
| `simplifica-booking/` | SIMplifica booking step by step: tickets, the PR1 two-section trap, refunds, errors |
| `pico-do-areeiro-weather/` | Pico do Areeiro weather: webcam + measured IPMA summit reading, PR1 card |
| `pr1-sunrise-transport/` | Getting to Areeiro for sunrise: public bus, shuttle, taxi, own car + parking |
| `pr1-one-way/` | "Is PR1 one-way?": direction, what's two-way, tickets, getting back (added 2026-10-02 from the competitor report: beyondmadeira's dedicated page ranks top 3) |
| `free-walks/` | "Free walks in Madeira: no ticket needed": which walks need no SIMplifica ticket (added 2026-10-02 for "ohne Gebühr" / "non payante" searches) |
| `best-levada-walks/` | Best levada walks, each with a live badge + STATIC-STATUS line |
| `easy-levadas-no-vertigo/` | Easy levadas ranked by sourced exposure (IFCN panels), live badges |
| `levadas-with-tunnels/` | Which levadas have tunnels / need a torch (sourced table), live badges |
| `pt/`, `fr/`, `de/`, `pl/` | Full Portuguese (European, formal "você")/French/German/Polish versions of every page |
| `status.json` | Live data written daily: PR1 flagship fields (top-level) **plus** `counts`, `regions` (weather), `trails[]` for the dashboard, and `source: {name, url, updated}` (`updated` = IFCN's own "ATUALIZADO" date) |
| `trail_extras.json` | Tunnels / torch / exposure (vertigo) per trail, written by `scripts/gen_trail_extras.py` from `seo_research/facts/tunnels_exposure.json`. Feeds the dashboard's "No vertigo" / "Has tunnels" filters and the spokes' facts rows. `null` = no sourced data, never "no tunnel" |
| `status.js` | Renders a single-trail status card from `status.json`. `#statusCard` with no `data-trail` → the detailed PR1 card; `data-trail="PR6"` → that trail's spoke card from `trails[]`. Localized by `<html lang>` |
| `dashboard.js` | Renders the trails dashboard (board + weather strip + counts + search/filter) from `status.json`, localized |
| `trails/` (+ `pt/`,`fr/`,`de/`,`pl/`) | Forwarding stubs only (meta-refresh + canonical to `/`, `/fr/`…) — GitHub Pages can't 301. Not in the sitemap; don't link to them |
| `25-fontes/`, `pico-ruivo/`, `caldeirao-verde/`, `sao-lourenco/`, `balcoes/`, `fanal/`, `levada-do-furado/`, `levada-do-rei/`, `levada-dos-cedros/` (each + `pt/`,`fr/`,`de/`,`pl/`) | The **9 hand-authored spoke** pages (PR6, PR1.2, PR9, PR8, PR11, PR13, PR10, PR18, PR14): PR1 shell + bespoke trail content, hero photo, `data-trail` live card, trail-facts sidebar |
| 27 more trail dirs (e.g. `levada-do-risco/`, `levada-do-moinho/`, …, each + `pt/`,`fr/`,`de/`,`pl/`) | The **generated spokes** — one per remaining PR trail; lightweight, live-status-first, facts scraped from the official page. Written by `scripts/gen_spokes.py`; don't hand-edit — re-run the generator |
| `scripts/gen_spokes.py` | One-off (re-runnable) generator for the 27 long-tail spokes: scrapes real facts (distance/difficulty/duration/altitude/start-end/route-type) from each trail's official Visit Madeira page, emits en/pt/fr/de/pl pages, and carries a `PHOTOS` map for hero images (17 of 27 have one). Since 2026-09-30 it also writes short titles (≤60 chars, `SHORT_NAMES` overrides), a 120–155-char description with a CTA, four visible question headings that double as the FAQ schema, `og:image` (hero JPEG or `/img/og-default.jpg`), the `.webp` hero + preload, a `TouristAttraction` JSON-LD with trailhead geo (via `gen_site_nav.trail_coords()`) and a lazy OpenStreetMap trailhead block. `--dry-run CODE OUTDIR` renders one trail outside the repo. Calls `gen_site_nav.py` and `gen_cta.py` at the end; the STATIC-STATUS markers it writes start empty until the next updater run |
| `scripts/update_status.py` | Daily status scraper/updater (Python 3.12, `requests`); also fills the STATIC-STATUS markers |
| `scripts/gen_trail_extras.py` | Builds `trail_extras.json` from the sourced facts file; `--patch-hand` refreshes the TRAIL-EXTRAS rows on the hand-authored spokes. Needs the local `seo_research/` folder |
| `scripts/gen_cta.py` | Writes the **Levadinho WhatsApp block** (CSS in `LEVADINHO-CTA-HEAD`, block in `LEVADINHO-CTA` markers) into every page except `privacy/`, `404.html` and the `trails/` stubs. Idempotent; re-run when a page is added |
| `scripts/gen_trail_index.py` | Writes the **static, crawlable** list of all 37 trail links into `#trailBoard` in the five dashboard homepages (`index.html`, `fr/index.html`, …) (between `STATIC-TRAIL-INDEX` markers). `dashboard.js` overwrites the container on load, so JS visitors never see it — it exists so Googlebot can *discover* the spokes. Re-run whenever a trail is added or removed |
| `scripts/gen_site_nav.py` | Injects the site-wide **nav bar** (6 links), **breadcrumbs** (visible + `BreadcrumbList` JSON-LD), a **"Nearby trails"** block (4 closest trailheads by real GPS distance, from the Visit Madeira index) on trail pages, and a **"More guides"** block (`SITE-NAV-GUIDES`: descriptive links to the guide pages, per-page list in `RELATED_GUIDES`, skipping pages the copy already links) into every page, between `SITE-NAV*` marker comments. Guide pages are registered in `GUIDES`. Since 2026-09-30 trail pages also get an **"In our guides"** line (links to best / easy / tunnels when those pages mention the trail). `trail_coords()` is importable. `--dry-run [OUTDIR]` writes sample pages outside the repo. Idempotent; `gen_spokes.py` calls it after regenerating. Re-run whenever a page or trail is added |
| `.github/workflows/update.yml` | Cron that runs the updater daily at 01:00 UTC (GitHub starts it ~4–6 h late); commits `status.json`, `sitemap.xml` and changed `*.html` (static status lines, `dateModified`), never `bot/` |
| `sitemap.xml`, `robots.txt` | SEO. `sitemap.xml` carries hreflang alternates (en, pt, fr, de, pl, x-default) for all 250 URLs (50 pages × 5 languages), is listed in `robots.txt`, and gets its `<lastmod>` bumped by the updater. A `sitemap_index.xml` wrapper existed briefly as a workaround for Search Console's stored `/sitemap.xml` entry being stuck on "Couldn't fetch"; it was deleted on 2026-09-07 — don't re-add references to it without re-adding the file |
| `googleea2064b7684c2bab.html` | Google Search Console site-verification token — do not delete |
| `404.html`, `favicon.ico`, `img/icon-180.png`, `img/icon-192.png` | Custom not-found page (noindex, no CTA/nav, served by GitHub Pages automatically) and the favicon / touch icons rendered from the Levadinho avatar. Every page links the two icons in its head |
| `img/*.webp`, `img/og-default.jpg` | Every hero JPEG has a `.webp` twin used in the CSS background (with a `<link rel=preload>`); the JPEG stays for `og:image`. Pages without a hero use `og-default.jpg` (Pride of Madeira, owner photo). Owner's own PR1 photos (`pr1-*.jpg`, `pride-of-madeira.jpg`) are credited in `img/CREDITS.txt` |
| `seo_research/` | **Local only, git-ignored** (it would be published otherwise): the SEO plan (`SEO_Plan.md`), agent brief, SERP evidence, and the verified facts files `facts/*.md` + `facts/tunnels_exposure.json` that page copy must cite |
| `bot/` | The **Levadinho WhatsApp bot** (trial, PR1 only): Meta Cloud API webhook (`app.py`) → `brain.py` → local Qwen3.6-35B-A3B on vLLM, grounded in `pr1_facts.md` + live `status.json`. See `bot/README.md` |

## The WhatsApp bot (`bot/`) — trial, started 2026-09-26

The funnel endpoint from the strategy. It is being built for the **2026-10-19 meeting** with
Madeira's Regional Secretary of Tourism, Environment and Culture, the Director of Tourism
(DRT) and the IFCN president. The meeting shows a teaser of the bot (PR1 only), the scraping
already in place, and a mock-up of the future usage log.

- **Everything is local.** The model runs in Docker `levadinho-llm` (vLLM, port 8001), the
  webhook is uvicorn on port 5020, and the public URL is the permanent Tailscale Funnel
  `https://microscopy-rig-system.tail53cc58.ts.net/levadinho` (webhook at `/webhook`, audio guide at `/guide/`).
  It's **off by default**: start it with `bot/start.sh` and stop it with `bot/stop.sh`.
- **Language rule:** a question is answered in its own language (PT/EN/FR/DE/PL, else
  English); a first contact that isn't a question gets the 5-language picker.
- **The bot may only state facts from `bot/pr1_facts.md` and live `status.json`.** Never
  let it invent prices, timetables or rules.
- **Don't scrape SIMplifica** (it's behind a login and reCAPTCHA). Availability and booking
  are to be requested from the Region.
- It is **live on +44 7405 754593** with a permanent token, so any phone can use it while it's
  running. Full run instructions, IDs and the Meta setup status are in `bot/README.md`.
- **Analytics (since 2026-09-28):** every interaction is kept permanently and pseudonymously
  in Postgres (`levadinho-db` container, :5433, always on): events, scrubbed conversations,
  individual GPS fixes. No phone numbers or IPs; the visitor id is an HMAC with
  `bot/.visitor_key`. See the "Analytics database" section of `bot/README.md`. The nightly
  backup runs from cron (`bot/db/backup.sh`).
- **Privacy notice (since 2026-09-28):** the bot answers nothing until the visitor taps Accept on
  a short notice. No acceptance means no service, and only an anonymous count is kept. The chat record's legal basis
  is legitimate interest; the guide's GPS log is a separate opt-in consent ("share my walk"). The
  policy is `privacy/` (one page, 5 languages: `#en #pt #fr #de #pl`). **Keep the policy, the
  consent wording in `brain.py` / `guide.js` and what is actually recorded in sync**, and bump
  `CONSENT_VERSION` (both files) with the policy date when what's recorded changes. Access and
  erasure requests: `bot/privacy_request.py`, runbook `bot/db/PRIVACY_REQUESTS.md`.
- **Containerised stack:** a separate PRIVATE repository, `maykef/levadinho-stack`
  (local: `/mnt/nvme8tb/levadinho-stack`). It packages the bot, the model, PostGIS, backups
  and the route builder, with `install.sh` / `uninstall.sh`, a server-move guide
  (`migrate/`, README) and REQUIREMENTS.md. It is meant for the server if the Region's
  contract comes. The workstation bot in this repo's `bot/` is still what runs live. The two
  share nothing, and only one model fits on the GPU at a time. The stack there runs in
  dry-run.
- **Audio guide:** `bot/guide/` is the GPS audio-guide web app. It has pocket mode, works
  offline, and is served at `…/levadinho/guide/`. Plan and task list:
  `WPA_Implementation_Plan.md` (local only, not committed).
- `bot/.env`, `bot/.visitor_key`, `bot/levadinho.db`, `bot/*.log`, `bot/tracklog/`,
  `bot/routes_private/` and `bot/.tts/` are git-ignored.
- **Heads-up:** GitHub Pages publishes `bot/`'s source code publicly.

## The daily updater (`scripts/update_status.py`)

Runs daily via GitHub Actions: cron 01:00 UTC, which GitHub starts 4–6 h late, so
roughly 05:15–06:55 UTC. **Planned:** an exact trigger so the update is live at
06:00 Madeira time with 05:55 weather. `workflow_dispatch` also allows manual
runs from the Actions tab. What it does:

1. **Status source (since 2026-09-30): the official IFCN warnings page**
   (`ifcn.madeira.gov.pt/pt/?view=article&id=627:percursos-pedestres-avisos&catid=146:avisos`).
   Scrapes its lists: items under ENCERRADOS/CONDICIONADOS → `CLOSED`, PARCIALMENTE
   TRANSITÁVEIS → `PARTIAL`, TRANSITÁVEIS → `OPEN`; a trail under two headings (PR1) →
   `PARTIAL`. The item text after the name is the note (Portuguese original, MyMemory
   pt→en/fr/de/pl with fixed section labels, cached). Porto Santo items are excluded; codes
   without a site page are skipped; ≤5 omitted trails fall back to the Visit Madeira index.
   The heading drives the status; `RESTRICTIVE` (EN+PT phrases) only downgrades
   `OPEN`→`PARTIAL` and gates. `status.json.source.updated` = IFCN's own "ATUALIZADO"
   date, shown on the cards, the dashboard and the static lines. **IFCN does not update
   daily**, so pages never say "updated every morning" about the status: they say it comes
   from the official IFCN warnings list and carry IFCN's own "updated" date.
2. Reads **official measured** summit weather from IPMA's Pico do Areeiro
   observation station (`1210974`, keyless open-data API). IPMA carries no sky
   code, so it reports temperature + a humidity-derived "likely in cloud" note
   + wind (falling back to neighbouring station `1210973` when the summit wind
   sensor reports the `-99` "missing" sentinel). `-99` fields and temps
   `< -10 °C` / `> 30 °C` are rejected → generic fallback line.
3. Reads five regional IPMA stations, then writes `status.json`: the PR1 flagship
   fields (status; note; structured weather; timestamp) **plus** `counts`, `regions`,
   `trails[]` and `source` for the dashboard. Bumps `<lastmod>` in `sitemap.xml` and the
   `"dateModified"` of the `WebPage` JSON-LD on the 5 homepages and 5 PR1 pages.
4. **Static (crawlable) status lines:** fills every `<!-- STATIC-STATUS:<CODE>:START/END -->`
   pair (one trail: "Official IFCN list (updated 14/09/2026): OPEN — note") and every
   `<!-- STATIC-STATUS-BOARD:START/END -->` pair (all-trail counts) in the site's HTML, in
   the page's `<html lang>`. They sit in each trail's `#statusCard` fallback (hand-authored
   spokes, `/pr1/`, and the weather/sunrise pages; generated spokes via `gen_spokes.py`),
   in the 5 homepages' summary, and next to each trail on the list pages
   (best / easy / tunnels). `status.js` / `dashboard.js` still replace them live.
5. The Action commits and pushes only if something changed (`status.json`,
   `sitemap.xml` and the changed `*.html`; never `bot/`).

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
  — don't hard-code status into any page's HTML by hand. The no-JS fallback inside each
  `#statusCard` is a neutral sentence plus the updater-written STATIC-STATUS line; the
  only status text in HTML is what the updater writes between STATIC-STATUS markers.
  The source note links the IFCN warnings list (the status source), SIMplifica and IPMA. To change wording or add a
  language, edit the `LANGS` dictionary in `status.js`; to change the data
  shape, edit the updater and `status.js` together. Each status page keeps a
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
  just `goatcounterCode` (plus `lastUpdated` on the article pages).
- **Levadinho WhatsApp block on every page** (`scripts/gen_cta.py`, between
  `LEVADINHO-CTA` markers; not on `privacy/` or the `trails/` stubs). **Placement (owner, 2026-09-30):**
  full width, directly below the webcam block / status card (the official note), else below the
  page header. Each run of `gen_cta.py` moves it there. The owner rejected a desktop top-right version,
  so don't put it back. Contents: a tap-to-open
  `https://wa.me/447405754593?text=Olá Levadinho! 👋 #web-<tag>` link on all screens, plus an
  inline SVG QR code (built with the `qrcode` lib) shown only at ≥720 px with "Scan with your
  phone". Tags are per page and shared by all languages (the bot detects the language):
  `web-home`, `web-pr1`, `web-fees`, `web-abroad`, `web-back`, `web-permit`, `web-booking`,
  `web-weather`, `web-sunrise`, `web-oneway`, `web-free`, `web-best`, `web-easy`, `web-tunnels`, and `web-<trail code>`
  on spokes (`web-pr6`, `web-pr1-2`, …). `bot/brain.py` records any `web-[a-z0-9-]{1,40}` tag
  as the source, not a guide route. A click fires a GoatCounter event `whatsapp-<tag>`
  (only when GoatCounter loaded). Don't hand-edit inside the markers; a new page needs a tag
  in `TAGS` (the script fails loud otherwise).
- Analytics is **GoatCounter**, loaded only when not self-excluded. Visiting any
  page with `#skipgc` sets a localStorage flag so your own device is never
  counted; `#countme` undoes it.
- Shared visual language: cream `--paper`, ink green, and the yellow/red
  **waymark stripe** (the paint marks on Madeira's rocks). Reuse the existing
  CSS variables and the `.waymark`, `.fact`, `.opt` patterns rather than
  inventing new styles.
- **Multilingual (en/pt/fr/de/pl).** English lives at the root; `pt/` (European
  Portuguese, formal "você"), `fr/`, `de/`, `pl/` mirror every page. Every page has a
  language switcher (`.langs`, EN · PT · FR · DE · PL), six `hreflang` alternates in the
  head (en, pt, fr, de, pl, x-default), and a self-referencing canonical. When you
  add/rename a page or change copy, update **all five languages**, the switcher links,
  the hreflang blocks, `sitemap.xml`, `GUIDES` in `gen_site_nav.py` and `TAGS` in
  `gen_cta.py`, then re-run both. Internal links are **root-relative** (`/pt/pr1/`),
  never `index.html`. Machine translations — flag for native review before relying on
  them commercially.
- **Facts must be sourced.** Prices, rules, dates and names come from official sources
  (IFCN, SIMplifica, Visit Madeira, Portarias 801/2025 & 48/2026, DLR 24/2022/M, IPMA,
  Horários do Funchal) or from the verified files in `seo_research/facts/`, and the page
  keeps a short "Sources" line. Where sources conflict, say so or leave it out.
- **Spokes now cover every trail.** All ~37 PR trails have a page and a `PAGES`
  entry. Two kinds:
  - **Hand-authored** (the 9 top trails): copy `25-fontes/index.html`, set
    `data-trail="<CODE>"`, write bespoke content + facts + FAQ, add to `PAGES`,
    add the `<!-- STATIC-STATUS:<CODE>:START/END -->` pair in the card fallback, translate
    to pt/fr/de/pl, add 5 URLs to `sitemap.xml`, re-run `gen_site_nav.py` and `gen_cta.py`. Keep them lightweight and
    freshness-focused (open today? booking, fee, parking, closures) — not
    exhaustive guides.
  - **Generated** (the other 27): produced by `scripts/gen_spokes.py` — **don't
    hand-edit them**, change the generator and re-run it (it re-scrapes facts and
    rewrites all 27 × 5 pages, then runs `gen_site_nav.py` and `gen_cta.py`; run the updater afterwards to refill the static status lines). To give a generated spoke a photo, add one line to
    the `PHOTOS` map in `gen_spokes.py` + drop the image in `/img/` (credited in
    `CREDITS.txt`), then re-run. New trails from the index get a generated spoke;
    only "promote" one to hand-authored if search demand justifies bespoke copy.
- **Internal links must exist in the raw HTML.** The dashboard renders its
  cards client-side, so for months the only statically-linked pages were `/`
  and the four `/trails/` — Search Console knew 4 URLs out of 164 and indexed
  2. `scripts/gen_trail_index.py` now emits real `<a href>`s for every trail.
  Never let a page's only route in be a JS-injected link.
- **Site nav, breadcrumbs, "Nearby trails" and "More guides" are generated**, not hand-written:
  don't edit inside the `SITE-NAV*` markers, change `scripts/gen_site_nav.py` and re-run
  it. Added from a Screaming Frog audit (2026-09-28) that found the fees and
  booking pages orphaned and most spokes with only 5 inbound links. Link to pages as
  `/`, `/fr/` etc., never `index.html` (that creates a duplicate homepage URL).
- **Titles ≤ 60 characters, descriptions 120–155 with a call to action** (pass 2, 2026-09-30). Never a
  trail name twice. Keep the per-language query words (e.g. PT "reabre", DE "gesperrt aktuell",
  PL "szlaków", "webcams" plural on the weather page); the SERP evidence is in `seo_research/`.
- **FAQ schema must be verbatim visible text.** Every FAQPage question is a visible heading (or the
  "Questions" / "Questions people ask" block) and every answer is the visible paragraph under it.
  When you change copy, change both; the audit from 2026-09-30 found 190 pages failing before.
- **Trail pages carry a `TouristAttraction` JSON-LD** (facts + trailhead geo) and a trailhead map block;
  PR1 has the schema but no map yet (no facts sidebar; placement undecided).
- Every page has FAQ `schema.org` JSON-LD in the head — keep it in sync with the
  visible copy when you change facts.
- Pages cross-link via a hand-written "Next steps" list plus the generated "More guides"
  block. Keep those links working when adding or renaming pages, and add new pages to
  `sitemap.xml`. Every guide page is one click from the homepage (its "More guides" block
  lists them all) and has well over 3 inbound links.

## The base URL

The site is served at **`https://levadinho-madeira.com/`** (apex; `www` redirects to it),
hosted from the `maykef/levadinho-madeira` repo via GitHub Pages (custom domain in the
`CNAME` file, DNS at GoDaddy). It moved from `madeira.maykef.info` on 2026-09-27. The base
URL is repeated on purpose in the canonical/og tags, `sitemap.xml`, and `robots.txt`. If it
ever changes again: search-and-replace the base URL everywhere and update `CNAME`.
Email: hello@levadinho-madeira.com (Microsoft 365 via GoDaddy — don't touch its DNS records).

## Facts to keep accurate (2026)

These are the substance of the site; verify against official sources before
changing them:

- PR1 is **one-way** since the full-route reopening on **1 May 2026** (Fri–Sun at first,
  daily from 26 June 2026): Areeiro → Ruivo only, you finish at Achada do Teixeira (no bus
  there). Never write "27 April" or "April" for the reopening.
- PR1 fee: **€10.50** full traverse, **€4.50** for the Areeiro–Pedra Rija
  section when only that is open. Standard PR trails: **€4.50** (operator €3).
  PR1 via operator: **€7**. Under-12s, residents, and 60%+ disability are exempt
  but must still be on the booking. Parking ~€4.00/hour.
- Booking is **SIMplifica, online-only**. Walking an IFCN classified trail without a valid
  SIMplifica ticket is an administrative offence (Portaria 801/2025 art. 10; DLR 24/2022/M
  art. 13); the law sets fines for individuals of **€250–€2,500**. Never "up to €250".
- Multi-day rates (automatic in one booking, PR1 excluded): **€9** / **€22.50** (3 days) /
  **€52.50** (7 days).

## Git

Branch is `main`; commits push straight to it (the Action commits as
`levadinho-bot`). Don't commit or push unless the user asks.

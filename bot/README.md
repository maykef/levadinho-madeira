# Levadinho WhatsApp bot (trial)

The trial version of **Levadinho**, a WhatsApp guide for Madeira visitors. It covers
**PR1 Vereda do Areeiro only**, as a teaser for the 2026-10-19 meeting with the Regional
Secretary of Tourism, Environment and Culture, DRT and IFCN.

## How it works

```
WhatsApp → Meta Cloud API → webhook (app.py, :5020) → brain.py → local LLM (vLLM, :8001)
                                                       ├─ pr1_facts.md   (static PR1 knowledge)
                                                       └─ status.json    (live status + IPMA weather,
                                                                          fetched from levadinho-madeira.com every 10 min)
```

**Language rules:**
- **First contact:** if the message is a question, answer it in the language it's written in
  (PT/EN/FR/DE/PL, or English for anything else). Otherwise, e.g. the QR code's pre-filled
  "Olá Levadinho!", send the 5-language picker (a WhatsApp list message).
- **After that:** every question is answered in its own language (English if not one of the
  five). Anything that isn't a question gets a reply in the chosen language.
- Typing "idioma", "language", "langue", "sprache" or "język" re-opens the picker.

**Grounding:** the model may only use LIVE STATUS and `pr1_facts.md`. Live status always
wins. The status comes from the **official IFCN warnings list**, which IFCN does not update every
day: `status_block()` passes `status.json`'s `source.updated` ("IFCN list updated 14/09/2026") and
the model (and the location reply, `LOC_FAR`) says "according to IFCN's list, updated <date>",
never "this morning's check". Trail notes are Portuguese originals with translations: the model
gets the `en` text, else the `pt` original. Other trails get a link to the trails board at `/`, and off-topic requests are declined.

## Files

| File | Purpose |
|------|---------|
| `pr1_facts.md` | PR1 knowledge compiled 2026-09-26, brought in line with the verified research in `seo_research/facts/` on 2026-09-30 (fines €250–€2,500, operator and multi-day rates, the Areeiro bus, Santana taxi, reopening dates, September works). It has a "not confirmed" section the bot must not state as fact |
| `brain.py` | Conversation flow, language handling, prompt, LLM calls. Knows nothing about WhatsApp |
| `llm_control.py` | Wake-on-demand: is the model up, is the GPU free, `docker start`/`stop levadinho-llm`, the background waiter |
| `tests/test_wake_on_demand.py` | Offline tests (fake docker/GPU/model/WhatsApp, scratch SQLite): `python bot/tests/test_wake_on_demand.py` |
| `tests/test_followups.py` | Offline tests for privacy export/erase of the queue, the chat with the model down, the scrub sweep, `web-*` campaigns, the facts file and the IFCN wording: `python bot/tests/test_followups.py` |
| `store.py` | SQLite (`levadinho.db`): each visitor's language, state and consent choice, the last 8 exchanges (24 h TTL), de-duplication of message ids, guide tokens (30 days), messages waiting for the model (`pending`) and each visitor's last message time (`last_inbound`, for WhatsApp's 24 h window) |
| `chat.py` | Local test chat through the same brain: `python bot/chat.py` (interactive) or `python bot/chat.py "msg1" "msg2"` (scripted). A digit 1–5 answers the picker, `/reset` starts over. With the model asleep it prints "[model down — would queue …]" and the waking-up message instead of crashing (nothing is queued or started). Set `LEVADINHO_DB` to a scratch file to keep the test visitor out of the live store |
| `privacy_request.py` | GDPR access / erasure for one phone number (runbook: `db/PRIVACY_REQUESTS.md`) |
| `app.py` | FastAPI webhook for the Meta Cloud API: GET verification, POST with X-Hub-Signature-256 check, background replies, list-message picker, fallback for non-text messages. Also `POST /twilio` (Twilio sandbox, below) |
| `twilio_wa.py` | The Twilio WhatsApp Sandbox channel: signature check, form → message dict, plain-text picker / notice and typed replies, split + send through Twilio's REST API |
| `tests/test_twilio.py` | pytest, offline: `python -m pytest bot/tests/test_twilio.py -q` (signed / bad-signature posts, the normalised message, background send, the plain-text flow, queued replay, the 1,500-character split) |
| `twilio_env.sh` | Asks for the Twilio Account SID and Auth Token without echoing them (`read -rsp`) and rewrites the four `TWILIO_*` lines in `.env` (mode 600). Run it in a real terminal: Claude Code's `!` prompt has no TTY, so the script refuses |
| `requirements.txt`, `.env.example` | The webhook's Python packages (installed in the miniforge base Python) and every `.env` key, without values |
| `extract_facts.py` → `trail_facts.json` | Facts for all 37 trails (official scrape plus coordinates). **Not used by the trial**; kept for the multi-trail version |
| `.env` (git-ignored) | `WA_TOKEN`, `WA_PHONE_NUMBER_ID`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`; the `TWILIO_*` keys; optionally `LLM_URL`, `LLM_MODEL`, `STATUS_URL` and the wake-on-demand settings below |

**Heads-up:** GitHub Pages publishes everything in the repo, so this folder's source code is
publicly readable at levadinho-madeira.com/bot/. Secrets live only in the git-ignored `.env`.

## Running it

```
bot/start.sh   # model → webhook + guide → Tailscale Funnel → points Meta's webhook at it → checks the token
bot/stop.sh    # stops all three, frees the GPU
```

**Check the GPU is free before starting.** `start.sh` still starts the model straight away; with
wake-on-demand (below) it is enough to keep the webhook running and let the model come and go.
The model takes about 85 GB. The container has
`--restart no`, so the bot is off after a reboot until started.
- **Model:** vLLM in Docker `levadinho-llm`, Qwen3.6-35B-A3B-FP8, `127.0.0.1:8001`. Takes about 2 min
  to load; answers take about 0.5–1.5 s with thinking disabled.
- **Webhook:** uvicorn `app:app` on `127.0.0.1:5020`, PID in `app.pid`, log in `app.log`. Each
  incoming message logs its type and the last 4 digits of the sender.
- **Public URL (since 2026-09-28):** Tailscale Funnel, path `/levadinho` → `127.0.0.1:5020`, so
  the permanent base is `https://microscopy-rig-system.tail53cc58.ts.net/levadinho` (the prefix is
  stripped before it reaches the app). Meta's webhook is `…/levadinho/webhook`; `start.sh` adds the
  Funnel route if it's missing and re-points Meta (harmless now the URL never changes). Other apps'
  Funnel routes on this machine must be left alone. The Cloudflare quick tunnel is retired.
- **Audio guide:** `…/levadinho/guide/?r=<route>&l=<lang>&t=<token>`. The bot sends this link when
  a visitor shares a location pin near a route's start (or types "guide"/"guia" to get WhatsApp's
  "Send location" button). Routes are built by `build_route.py` from a GPX + `source.json` (Piper TTS
  in the git-ignored `bot/.tts/`). `routes/` is public; `routes_private/` (git-ignored, e.g. the
  owner's Ely test loop) is served only with a valid guide token. Desk test: add `&sim=1&speed=5`.
  Plan and task list: `WPA_Implementation_Plan.md` in the repo root.
- **Never touch** the system `cloudflared.service` (epiproc). Never `pkill -f`/`pgrep -f` a
  pattern that also appears in your own command line (it kills the shell); use the PID files.
- **To reset a phone to "new visitor" for testing,** delete its rows from `users` and `turns`
  in `levadinho.db`.

## Wake on demand (since 2026-09-30)

The webhook runs all the time; the ~85 GB model runs only while it's needed (`llm_control.py`).

- **A message needs the model** (a free-text question, or classifying a first free-text message)
  **while it's down:** `brain.llm()` raises `LLMDown`, `app.py` queues the message in `store.py`
  (`pending`) and replies at once:
  - **GPU free** (≥ `LLM_GPU_FREE_GB` free): "Levadinho is waking up. Give me about 2 minutes 🥾"
    (pt/en/fr/de/pl, guessed from the message, else the chosen language), and `docker start
    levadinho-llm` (or the same `docker run` as `start.sh` if the container doesn't exist);
  - **GPU busy** (someone else's job): "Levadinho is very busy right now. I'll message you here as
    soon as I'm free." Nothing is stopped to make room. When the GPU frees, the waiter starts the
    model and answers.
  - A visitor gets one notice however many messages they send meanwhile; all are answered in order.
- **The waiter** (a thread started with the webhook) checks every 5 s: once the model answers it
  replays the queue. A queued message is answered only inside **WhatsApp's 24-hour window** from the
  visitor's last message; older ones are dropped and logged (and recorded, if the visitor accepted).
- **Works without the model:** the picker, the privacy notice and its buttons, the language choice,
  campaign QRs (guide link), "guide"/"guia" and location pins. Accept tapped while the model sleeps:
  the acceptance counts at once and the question asked before it is queued.
- **Idle stop:** after `LLM_IDLE_MIN` minutes without an incoming message (and nothing queued) the
  waiter runs `docker stop levadinho-llm`. It never stops anything else.
- **Privacy:** a queued exchange is recorded (`app.record()`, same consent rules) when it's
  answered or dropped, not before. Queued messages live in the working store for at most 24 h and are
  covered by `store.erase()`; `privacy_request.py access` exports them (and the last-incoming time).

| Setting (`.env`) | Default | Meaning |
|---|---|---|
| `LLM_ON_DEMAND` | `1` | `0` = old behaviour: the model is started by hand with `start.sh` and never stopped by the webhook |
| `LLM_AUTO_STOP` | `1` | `1` = stop the idle model whoever started it; `0` = only if the webhook started it (a model started by `start.sh` stays up) |
| `LLM_IDLE_MIN` | `30` | Idle minutes before the model is stopped; `0` = never |
| `LLM_GPU_FREE_GB` | `88` | Free GPU memory (GiB) needed to start the model |
| `LLM_RETRY_S` | `300` | Minimum wait before another start attempt after one that didn't come up |

**Website links** pre-fill a greeting in the page's language plus the page tag: `Hello Levadinho! 👋 #web-pr1`
(EN), `Olá …` (PT), `Bonjour … !` (FR), `Hallo …` (DE), `Cześć …` (PL); see `WA_PREFIX` in `scripts/gen_cta.py`.
The bot takes the language from that greeting, so website visitors go straight to the privacy notice (no
language menu). The tag is kept as the visitor's source (`source` in the store, `campaign_id` in analytics)
and its guide or trail is used when a question names none. Campaign QRs (`#areeiro`, `#ely`) still get the
menu and then open their route's guide.

**Test phones (owner, 2026-10-05):** `TEST_NUMBERS` in `.env` (digits, comma-separated). Those numbers are
never recorded in the analytics database or guide logs; the working store is wiped when they write after an
hour of silence, and at once when they send `reset`. Test: `test_owner_test_number_leaves_nothing`.

**First contact (owner, 2026-10-05):** greetings need no model; anything that isn't a greeting waits for
Accept and is answered right after it (a waiting message starts loading the model); with nothing waiting,
Accept gets one short line. The language menu goes out only when the language can't be told, and only once.
A getting-from-A-to-B request first asks where the visitor is staying (the town is kept as `base`); the
answer uses `transport_facts.md` (official taxi numbers from IFCN's panels, Visit Madeira's contacts) and
never names a business that isn't in the facts. Tests: `tests/test_first_contact.py`.

## Logs and watchdog (since 2026-09-30)

- **`app.log` is never overwritten.** `start.sh` moves the previous one to
  `logs/app-<last write>.log` and keeps the 60 newest.
  - **Why:** on 30 Sep an overwrite destroyed the only record of why messages had stopped.
- **Every Meta delivery is logged:** accepted POSTs, with message and status counts; rejected
  POSTs, with the reason (bad or missing signature, not JSON); webhook verifications; and
  "reply delivery FAILED" statuses.
  - No phone numbers or IPs are logged.
- **`watchdog.sh`** runs from cron every 5 minutes, only while `.running` exists. `start.sh`
  creates the flag and `stop.sh` removes it, so a bot you switched off stays off.
  - **Checks:** the webhook, the public Funnel URL, Meta's API with our token (also catches "API
    access blocked"), and the model, if its container is running (asleep is normal with
    wake-on-demand).
  - **Output:** one line per run in `logs/watchdog.log`.
  - **Recovery:** after 3 failing runs in a row it does a FULL restart (`stop.sh --keep-running`,
    GPU logged, `start.sh`, GPU logged), at most once an hour. If another process still holds the
    GPU after the stop, it starts the webhook only and never the model.
- **"Restart the bot" always means the full cycle:** `stop.sh`, check that the GPU is empty,
  `start.sh`, check that it's reloaded. A webhook-only restart is just for code deploys, and must
  be called that.

## Analytics database (T6/T7, since 2026-09-28)

Every interaction is kept **permanently and pseudonymously** in Postgres + PostGIS, in the
Docker container `levadinho-db` (`127.0.0.1:5433`; data in
`/mnt/nvme8tb/levadinho_madeira/levadinho-db/`; `DB_URL` in `.env`). It runs always,
independently of the GPU bot.

- **Privacy notice first (T13, since 2026-09-28).** Levadinho answers nothing until the
  visitor taps **Accept** on a short notice (`brain.consent_prompt`, shown after the language
  pick, or straight away if the first message is a question). A question asked before Accept
  waits in the working store and is answered right after it. **Don't accept = no service.**
  - Legal basis: legitimate interest, not consent. Refusing service without acceptance rules
    consent out (GDPR Art. 7(4)); the policy says so.
  - Typing "privacy", "privacidade", "confidentialité", "Datenschutz" or "prywatność" shows the
    notice again; Don't accept then stops both recording and the service.
  - Before acceptance, or after declining, `app.record()` writes only an anonymous
    `message_unrecorded` / `consent_declined` event: no visitor id, text or position.
  - Accepts vs. declines: count `consent_given` vs. `consent_declined` events.
  - The acceptance is kept in `visitor.consent`, `consent_version` (the policy date,
    `brain.CONSENT_VERSION`) and `consent_at`.
  - The audio guide's GPS log is a true opt-in consent, asked in the guide itself. "Start · share my walk" sends the log; "Start without
    sharing" keeps everything on the phone.
  - **If the policy changes what is recorded,** bump `CONSENT_VERSION` in `brain.py` and
    `guide.js` together with the policy date.
- **Access and erasure requests:** `python bot/privacy_request.py access|erase <phone>`. Runbook in
  `db/PRIVACY_REQUESTS.md`.

- **No phone numbers or IP addresses.** A visitor is `visitor_id` = HMAC-SHA256 of the phone
  number with the key in `bot/.visitor_key`, which is git-ignored and backed up separately to
  `/mnt/tank/levadinho_backup/keys/`. Access and erasure requests recompute the id from the
  number (`privacy_request.py`).
- **Tables:**
  - `event`: every interaction;
  - `conversation_turn`: every message in and out, scrubbed. Rules replace phones, emails,
    codes and links; then the local model replaces names in the background. If the model is
    asleep, the row keeps `scrub_method='rules'` and a **sweep** (in the same background thread)
    re-scrubs it once `llm_control.is_up()`: every `SCRUB_SWEEP_S` (900 s), every `SCRUB_RETRY_S`
    (120 s) while a backlog is known, `SCRUB_BATCH` (25) rows at a time. The sweep never wakes the
    model or delays a reply. It only takes incoming text and the model's answers; a model output
    that fails the length guard is marked `rules+llm-rejected` and not retried;
  - `location_fix`: every GPS point and WhatsApp pin, stored individually;
  - `visitor`: country from the dialling code, and language;
  - lookups: `route`, `stop`, `campaign`, `event_type` (the catalogue). A `web-*` website tag
    is added to `campaign` (no route, description "website page link") the first time it's seen,
    fail-soft like every analytics write.
- **Self-describing:** every table and column has a `COMMENT`, e.g. `\d+ event` in psql.
- **Wiring:**
  - `app.py` calls `record()` after each reply, using the `meta` that `brain.handle()` fills
    (question labels come from the same `classify()` call);
  - the guide's `/guide/log` also writes to the database;
  - `analytics.py` is fail-soft: if the database is down, the bot keeps replying.
- **Setup / maintenance:** `python bot/analytics.py init` (schema + routes/campaigns, idempotent)
  and `python bot/analytics.py backfill` (imports `bot/tracklog/` test logs).
- **Backup:** `bot/db/backup.sh` runs at 03:30 from cron → `/mnt/tank/levadinho_backup/db/`,
  keeping 30 days.

## Twilio sandbox (since 2026-10-02)

Meta banned the WhatsApp Business account (below), so for the 19 October demo the bot also answers
on the **Twilio WhatsApp Sandbox**. The Meta path (`/webhook`) is untouched and works again as soon as
Meta lifts the ban; both can run at once.

```
WhatsApp → Twilio sandbox (+1 415 523 8886) → POST …/levadinho/twilio (app.py) → same process() / brain.py
         ← Twilio REST API (twilio_wa.send) ←───────────────────────────────────┘
```

- **Endpoint:** `https://microscopy-rig-system.tail53cc58.ts.net/levadinho/twilio` (the Funnel strips
  `/levadinho`, so uvicorn sees `/twilio`). Save it in Twilio console → Messaging → Try it out → Send a
  WhatsApp message → Sandbox settings → "When a message comes in", method POST.
- **How it differs from Meta:**
  - Twilio posts a form (`From`, `Body`, `ProfileName`, `MessageSid`, `NumMedia`, `Latitude`/`Longitude`),
    signed with `X-Twilio-Signature` over the **public** URL (`TWILIO_WEBHOOK_URL`); a bad signature gets 403.
  - `twilio_wa.normalise()` turns it into the dict the Meta path hands to `process()`, with
    `"channel": "twilio"` (a Meta message has no `channel` = Meta). The sender is the number as digits
    only, like Meta's, so the working store, the HMAC visitor id, the analytics, the privacy notice,
    `web-<tag>` sources and `privacy_request.py` all behave the same. `brain.py` is unchanged.
  - The webhook answers an empty `<Response/>` at once (Twilio gives up after 15 s) and replies in the
    background through the REST API. Replies over 1,500 characters go out as several messages, cut on
    paragraph boundaries. Each send logs Twilio's message SID; errors are logged as `Twilio API <status>`.
  - **No buttons or lists.** The picker is sent as text ending `1 Português · 2 English · 3 Français ·
    4 Deutsch · 5 Polski`; the visitor types the digit or the language. The privacy notice is the same
    text and policy link, with its last line replaced by "Reply *ACEITO / ACCEPT / ACCEPTER / AKZEPTIEREN /
    AKCEPTUJĘ* to continue, or NÃO ACEITAR / DON'T ACCEPT / REFUSER / ABLEHNEN / NIE AKCEPTUJĘ to decline"
    (in the visitor's language; the decline words are brain's Don't-accept button labels). Any of those
    words is accepted, case- and accent-insensitive. Declining works like the button: no service, or a
    withdrawal after "privacy". `CONSENT_VERSION` is recorded exactly as with the button. "guide" asks for a pin with "📎 → 📍" instead of the button.
  - **`join bark-wood`** (or any message starting `join `) counts as a first contact with no question:
    the picker, as for Meta's `request_welcome`. `join bark-wood #web-<tag>` becomes the website greeting,
    so the tag is recorded as the source.
- **`.env`:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WA_FROM=whatsapp:+14155238886`,
  `TWILIO_WEBHOOK_URL` (see `.env.example`). With the SID, token and FROM all set, `start.sh` only warns about a
  rejected Meta token (and checks the Twilio credentials), and the watchdog skips the Meta check
  (`meta=skipped:twilio` in `logs/watchdog.log`, also `skipped:no-token` when `WA_TOKEN` is empty).
- **Status (2026-10-02):** the webhook runs with the Twilio config; local `/health` and the Funnel
  `/levadinho/health` answer 200 and an unsigned `POST /twilio` gets 403. The first sends (12:04) failed
  with **401 / 20003 "Primary compliance profile is not approved"**: an account-level KYC check in
  Twilio's Trust Hub, not a code problem. The owner submitted the verification and the first reply went
  out at 12:16 (`Twilio sent SM…`, HTTP 201). A reply that fails this way is lost, not queued: the
  visitor must send the message again.
- **Log noise:** the `twilio` library logs every request (URL with the Account SID, response headers)
  at INFO into `app.log`. No token is written, but `logging.getLogger("twilio.http_client").setLevel(logging.WARNING)`
  in `app.py` would silence it (not done yet).
- **Switching the website CTA:** in `scripts/gen_cta.py` comment the Meta `WA_NUMBER` / `WA_PREFIX`
  pair, uncomment the sandbox pair (`14155238886`, `join bark-wood`), run `python scripts/gen_cta.py`
  and commit the pages. The links then pre-fill `join bark-wood #web-<tag>`. Reverse to switch back.
- **Sandbox limits:**
  - one **shared** number (+1 415 523 8886) that shows as "Twilio", not Levadinho;
  - every phone must first send the **join phrase** `join bark-wood`;
  - after **72 h without a message** the phone drops out of the sandbox and must send the join phrase again;
  - **no interactive messages** (lists, buttons, location request), and the usual 24 h window for replies;
  - delivery to international numbers is **not guaranteed**: test the demo phones in advance.
  - Unverified: whether Twilio passes the join message on to the webhook or answers it itself. If it
    keeps it, the `#web-<tag>` is lost and the visitor's next message starts the normal flow. On
    2026-10-02 the first two test messages reached the webhook as ordinary text and no bare
    `join bark-wood` arrived (it would log `twilio POST ok: request_welcome`); still unconfirmed.

## Meta setup status (2026-09-28) — LIVE on a real number

> **BANNED since 2026-09-30 ~16:12 (still banned on 2026-10-01 18:17).** Meta's API reports the phone
> number `status: BANNED`, WABA error 141014 "The WABA is banned", `account_review_status: REJECTED`,
> business not verified. A banned account gets **no webhook deliveries** (the sender sees a single grey
> tick) although the verify handshake still succeeds, so the bot looks up but silent. The owner
> submitted an appeal on 2026-09-30 (business.facebook.com/accountquality); the payment-method error
> 141006 that Meta also listed disappeared on 2026-10-01. **Before restarting anything when the bot is
> silent, ask Meta:**
> `set -a; . bot/.env; set +a; curl -s "https://graph.facebook.com/v23.0/$WA_PHONE_NUMBER_ID?fields=status,health_status" -H "Authorization: Bearer $WA_TOKEN"`
> Restarts neither cause nor fix this. Everything below describes the account as it was before the ban.


- **Meta app:** "Levadinho" (ID 1433947322205284), published. Business portfolio "Levadinho-Madeira".
  - Privacy policy: https://levadinho-madeira.com/privacy/ (contact hello@levadinho-madeira.com).
- **Bot number: +44 7405 754593** (UK virtual mobile).
  - Phone number ID `1252178464655857`, WABA "Levadinho Madeira" `1087386100886727`.
  - Status CONNECTED, display name "Levadinho Madeira" approved, messaging tier 250 (before the ban; on 2026-10-02 `health_status` reported the display name as NOT approved — cause unknown).
  - **Open to any phone.**
- **Token:** a permanent System User token (`levadinho-bot`, id 61595071312731, never
  expires), with `whatsapp_business_messaging` + `whatsapp_business_management`, stored in `.env`.
- **Webhooks:** the WABA is subscribed to the app (`POST /{WABA}/subscribed_apps`).
  `start.sh` points the app webhook at the permanent Funnel URL.
- **WhatsApp profile** (set via the API):
  - the avatar picture;
  - category TRAVEL (registration had set it to GOVT);
  - the description;
  - website https://levadinho-madeira.com/.
- **Welcome message:** enabled (`conversational_automation`) and handled in `app.py`
  (`request_welcome` → picker). **Meta never actually sent it in tests**, so the reliable
  path is the QR code with a pre-filled message.
- **QR code** (git-ignored): only one is kept (owner, 2026-09-28), `bot/qr/levadinho-qr-prefilled.png`
  (copy in `~/Downloads/levadinho-qr.png`) → `https://wa.me/447405754593?text=Olá Levadinho! 👋`.
  Generated locally: free, never expires. Campaign QRs (e.g. `#ely`) were deleted; regenerate one
  with the `qrcode` package when needed (pre-fill `Olá Levadinho! 👋 #<tag>`).
  - A QR code can't send the first message itself; WhatsApp always requires the user to tap send.
- **The chat header shows the number, not the name,** until Meta verifies the business
  (Official Business Account or Meta Verified). That needs a registered company, which the
  owner will only create **after the Region clears Stage 1 (the 3-month trial)**.
- **The old test number** +1 555 175 9350 (ID 1411459425373096, WABA 1417869493809954) is
  kept as a comment in `.env`; `.env.bak-testnumber` is a backup.

## Known limits / ideas

- **SIMplifica availability is behind a citizen login and reCAPTCHA.** Don't scrape it. Ask
  the Region for a read-only availability feed; booking inside WhatsApp comes later
  (WhatsApp Flows plus a payment link).
- The bot can't track location in the background. Visitors share a pin or say where they're
  going. Messages the bot initiates outside the 24 h window need approved templates.

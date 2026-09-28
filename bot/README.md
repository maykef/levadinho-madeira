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
wins. Other trails get a link to `/trails/`, and off-topic requests are declined.

## Files

| File | Purpose |
|------|---------|
| `pr1_facts.md` | PR1 knowledge compiled 2026-09-26 from the official page, our site and 2026 guides. It has a "not confirmed" section the bot must not state as fact |
| `brain.py` | Conversation flow, language handling, prompt, LLM calls. Knows nothing about WhatsApp |
| `store.py` | SQLite (`levadinho.db`): each visitor's language and state, the last 8 exchanges (24 h TTL), de-duplication of message ids |
| `chat.py` | Local test chat through the same brain: `python bot/chat.py` (interactive) or `python bot/chat.py "msg1" "msg2"` (scripted). A digit 1–5 answers the picker, `/reset` starts over |
| `app.py` | FastAPI webhook for the Meta Cloud API: GET verification, POST with X-Hub-Signature-256 check, background replies, list-message picker, fallback for non-text messages |
| `extract_facts.py` → `trail_facts.json` | Facts for all 37 trails (official scrape plus coordinates). **Not used by the trial**; kept for the multi-trail version |
| `.env` (git-ignored) | `WA_TOKEN`, `WA_PHONE_NUMBER_ID`, `WA_APP_SECRET`, `WA_VERIFY_TOKEN`; optionally `LLM_URL`, `LLM_MODEL`, `STATUS_URL` |

**Heads-up:** GitHub Pages publishes everything in the repo, so this folder's source code is
publicly readable at levadinho-madeira.com/bot/. Secrets live only in the git-ignored `.env`.

## Running it

```
bot/start.sh   # model → webhook → tunnel → re-points Meta's webhook → checks the token
bot/stop.sh    # stops all three, frees the GPU
```

**Check the GPU is free before starting.** The model takes about 85 GB. The container has
`--restart no`, so the bot is off after a reboot until started.
- **Model:** vLLM in Docker `levadinho-llm`, Qwen3.6-35B-A3B-FP8, `127.0.0.1:8001`. Takes about 2 min
  to load; answers take about 0.5–1.5 s with thinking disabled.
- **Webhook:** uvicorn `app:app` on `127.0.0.1:5020`, PID in `app.pid`, log in `app.log`. Each
  incoming message logs its type and the last 4 digits of the sender.
- **Tunnel:** a Cloudflare quick tunnel with `--config /tmp/claude-empty-cf.yml`. Without it,
  `~/.cloudflared/config.yml` (the epiproc named tunnel) answers 404. PID in `tunnel.pid`. The
  URL changes every start, so `start.sh` updates Meta via `POST /{app-id}/subscriptions`
  with the app token `APP_ID|APP_SECRET`.
- **Never touch** the system `cloudflared.service` (epiproc). Never `pkill -f`/`pgrep -f` a
  pattern that also appears in your own command line (it kills the shell); use the PID files.
- **To reset a phone to "new visitor" for testing,** delete its rows from `users` and `turns`
  in `levadinho.db`.

## Meta setup status (2026-09-28) — LIVE on a real number

- **Meta app:** "Levadinho" (ID 1433947322205284), published. Business portfolio "Levadinho-Madeira".
  - Privacy policy: https://levadinho-madeira.com/privacy/ (contact hello@levadinho-madeira.com).
- **Bot number: +44 7405 754593** (UK virtual mobile).
  - Phone number ID `1252178464655857`, WABA "Levadinho Madeira" `1087386100886727`.
  - Status CONNECTED, display name "Levadinho Madeira" approved, messaging tier 250.
  - **Open to any phone.**
- **Token:** a permanent System User token (`levadinho-bot`, id 61595071312731, never
  expires), with `whatsapp_business_messaging` + `whatsapp_business_management`, stored in `.env`.
- **Webhooks:** the WABA is subscribed to the app (`POST /{WABA}/subscribed_apps`).
  `start.sh` re-points the app webhook to each new tunnel URL.
- **WhatsApp profile** (set via the API):
  - the avatar picture;
  - category TRAVEL (registration had set it to GOVT);
  - the description;
  - website https://levadinho-madeira.com/.
- **Welcome message:** enabled (`conversational_automation`) and handled in `app.py`
  (`request_welcome` → picker). **Meta never actually sent it in tests**, so the reliable
  path is the QR code with a pre-filled message.
- **QR codes** (git-ignored, in `bot/qr/` and `/mnt/tank/levadinho_backup/bot/qr/`):
  - `levadinho-qr-prefilled-avatar.png` / `levadinho-qr-prefilled.png` →
    `https://wa.me/447405754593?text=Olá Levadinho! 👋`. Generated locally: free, never expire.
  - `levadinho-qr.png` is a plain `wa.me/447405754593` code, without the pre-filled message.
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

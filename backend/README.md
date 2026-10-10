# Levadinho backend: knowledge store + MCP server

One sourced knowledge store, read by three clients: the WhatsApp bot (tools-only answers, phase 3), the public
(read-only MCP, phase 4) and the site generators. Every record carries `source_id` + `checked_at`.

| File | What |
|---|---|
| `schema.sql` | Schema `kb` in `levadinho-db` (:5433) + the read-only role `kb_reader` (kb only, no visitor data, read-only transactions, 5 s timeout) |
| `seed.py` | Hand-curated records: sources, exact fees, the PR1 Areeiro bus, island-wide taxis, transport rules. Copied from `bot/pr1_facts.md` / `bot/transport_facts.md`: change both together |
| `load.py` | Loaders. `init` applies the schema; `all` loads everything; `daily` = sources, status + weather, history, forecasts |
| `kbtools.py` | The 14 read-only tools as plain functions (psycopg). The bot imports this directly |
| `mcp_server.py` | MCP server (official `mcp` SDK 2.x, `MCPServer`), streamable HTTP on `127.0.0.1:5040/mcp`, stateless JSON; `--stdio` for local clients |
| `tests/test_mcp.py` | End-to-end MCP test (spare port 5041) |
| `tests/regression.py` + `regression_questions.json` | The bot's 40-question regression set (PR1 + other trails, 5 languages); `heldout_questions.json` = 15 unseen questions |

The bot's tools-only path is `bot/brain_tools.py` (imports `kbtools` directly, no MCP hop). It is used only when
`BOT_TOOLS=1` is in `bot/.env`; without it the bot answers the old way (prompt-stuffed facts). The flag needs a full
restart. vLLM must run with `--enable-auto-tool-choice --tool-call-parser qwen3_coder` (`bot/start.sh`).

## Where the data comes from

| Table | Loader | Source |
|---|---|---|
| `trail` | trails | `bot/trail_facts.json` (Visit Madeira), `trail_extras.json` (IFCN panels), fees from `status.json` |
| `trail_status`, `weather_obs` | status (daily) | live `status.json` from the site (local copy as fallback) |
| `status_day` | history (daily) | live `history/status-daily.jsonl` |
| `fee` | fees | `seed.py` |
| `fact` | facts | `bot/pr1_facts.md` bullets (the "Not confirmed" section is stored with `confirmed=false` and never returned), `seed.py` transport rules, the bus sentences of `scripts/gen_bus.py` (5 languages) |
| `transport` | transport | taxi table in `bot/transport_facts.md` (IFCN panels) + `seed.py` |
| `bus_trip` | bus | `scripts/gen_bus.py` `TRAILS` + `gen_bus_hub.py` `EXTRA` + the PR1 Areeiro bus in `seed.py` |
| `doc` | docs | site pages in 5 languages (via `bot/build_kb.py`'s text extraction), split at headings; `pr1_facts.md` sections. Postgres full-text search |
| `forecast` | forecast (daily) | `reports/camtest/forecasts/*.json` (fog test, local) |
| `place` | places (daily) | `funchal.json` places + lidos (opening rules in `scripts/update_funchal.py`; the cable car row carries the Monte rule and the last buses down) |
| `notice` | notices (daily) | cruise ships in Funchal port, 14 days (APRAM calls, cargo and the Porto Santo ferry left out) + `funchal.json` events |
| (no table) | `webcam` tool | the newest frame of the Rabaçal / Achada do Teixeira / Pico do Areeiro NetMadeira cams on disk (`/mnt/tank/levadinho_webcams`), served by the webhook at `/cam/<id>.jpg` (`CAM_BASE`) |

Cron (this machine): `20 * * * *  backend/load.py daily >> backend/logs/load.log`; since 2026-10-10 `daily` also reloads
`docs` (the page text), `places` and `notices`, so the bot reads today's pages. After facts-file or `gen_bus.py`
changes, run `python3 backend/load.py trails facts transport bus docs`.

**Bot rule (owner, 2026-10-10):** every fact the bot states comes from this store through the tools; follow-ups are
answered by the model with tools only (the canned answers of `bot/answers.py` are no longer used for follow-ups).

## Run

```
python3 backend/load.py init && python3 backend/load.py all
python3 -m venv backend/.venv && backend/.venv/bin/pip install mcp "psycopg[binary]"
backend/.venv/bin/python backend/mcp_server.py          # http://127.0.0.1:5040/mcp
backend/.venv/bin/python backend/tests/test_mcp.py
```

The server reads `KB_URL` or `~/.config/levadinho/kb-reader-url` (chmod 600, outside the repo). Calls are logged
to stderr as tool + arguments only; uvicorn's access log is off (it would record IP addresses).

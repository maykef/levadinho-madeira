# Levadinho backend: knowledge store + MCP server

One sourced knowledge store, read by three clients: the WhatsApp bot (tools-only answers, phase 3), the public
(read-only MCP, phase 4) and the site generators. Every record carries `source_id` + `checked_at`.

| File | What |
|---|---|
| `schema.sql` | Schema `kb` in `levadinho-db` (:5433) + the read-only role `kb_reader` (kb only, no visitor data, read-only transactions, 5 s timeout) |
| `seed.py` | Hand-curated records: sources, exact fees, the PR1 Areeiro bus, island-wide taxis, transport rules. Copied from `bot/pr1_facts.md` / `bot/transport_facts.md`: change both together |
| `load.py` | Loaders. `init` applies the schema; `all` loads everything; `daily` = sources, status + weather, history, forecasts |
| `kbtools.py` | The 13 read-only tools as plain functions (psycopg). The bot imports this directly |
| `mcp_server.py` | MCP server (official `mcp` SDK 2.x, `MCPServer`), streamable HTTP on `127.0.0.1:5040/mcp`, stateless JSON; `--stdio` for local clients |
| `tests/test_mcp.py` | End-to-end MCP test (spare port 5041) |
| `tests/regression.py` + `regression_questions.json` | The bot's 40-question regression set (PR1 + other trails, 5 languages) |

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
| `place`, `notice` | (Funchal work) | empty for now |

Cron (this machine): `20 * * * *  backend/load.py daily >> backend/logs/load.log`. After page, facts-file or
`gen_bus.py` changes, run `python3 backend/load.py trails facts transport bus docs`.

## Run

```
python3 backend/load.py init && python3 backend/load.py all
python3 -m venv backend/.venv && backend/.venv/bin/pip install mcp "psycopg[binary]"
backend/.venv/bin/python backend/mcp_server.py          # http://127.0.0.1:5040/mcp
backend/.venv/bin/python backend/tests/test_mcp.py
```

The server reads `KB_URL` or `~/.config/levadinho/kb-reader-url` (chmod 600, outside the repo). Calls are logged
to stderr as tool + arguments only; uvicorn's access log is off (it would record IP addresses).

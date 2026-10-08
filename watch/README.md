# Levadinho watch: promenade part closures from official notices

The Funchal seafront promenade (Câmara de Lobos → Barreirinha, ~9.6 km, 8 areas in `areas.json`) is always open;
this service finds **part closures** in official notices and records them automatically.

| Container | Port (127.0.0.1) | Job |
|---|---|---|
| `lw-rsshub` | 18402 | Facebook / Instagram accounts → RSS (works logged out) |
| `lw-changedetection` + `lw-browser` | 18401 (dashboard) | Pages without a feed (`watches.json`): Câmara de Lobos news, Proteção Civil, lido hours and prices |
| `lw-apply` | 18403 (status page) | Polls `sources.json` every 45 min, receives changedetection alerts, classifies (`apply/classify.py`), writes the notices |

**Rules** (`apply/classify.py`, tests in `apply/test_classify.py` from real 2021–2026 notices):
- An **official** notice (council, Frente MarFunchal, Câmara de Lobos, Proteção Civil, regional government) that names an
  area and clearly says closed / reopened is **applied automatically**. Dates ("de 22 a 26 de junho", "até…", "no dia…")
  set start/end; storm closures without an end expire after 2 days; other open-ended ones go to review after 21 days.
- Press items, "condicionado" (restricted), lido-complex events and anything unclear go to `review.jsonl`, never to the map.
- "Acessos ao mar" closing is a sea-access note, not an area closure.

**Outputs** in `$LW_DATA` (default `../seo_research/funchal/data/`, local only), shaped like the backend's `kb.notice`:
`notices.json`, `promenade_status.json`, `review.jsonl`, `events.jsonl`. Runtime state in `state/` (git-ignored).

```
docker compose -f watch/docker-compose.yml up -d
python3 watch/setup_watches.py          # create / update the changedetection watches (idempotent)
curl -s 127.0.0.1:18403/                # status: 8 areas, review count, source errors
cd watch/apply && python3 -m unittest   # classifier tests
```

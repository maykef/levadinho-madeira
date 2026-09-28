#!/usr/bin/env bash
# Bring the Levadinho WhatsApp bot up: model (vLLM) → webhook (uvicorn) → quick tunnel →
# point Meta's webhook at the new tunnel URL. Check the GPU is free BEFORE running this.
#   bot/start.sh
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
APP_ID=1433947322205284

# 1. Model
if ! docker ps --format '{{.Names}}' | grep -qx levadinho-llm; then
  if docker ps -a --format '{{.Names}}' | grep -qx levadinho-llm; then
    docker start levadinho-llm >/dev/null
  else
    docker run -d --name levadinho-llm --gpus all --ipc=host --restart no \
      -p 127.0.0.1:8001:8000 -v /mnt/nvme8tb/huggingface_cache:/root/.cache/huggingface \
      -e HF_HUB_OFFLINE=1 vllm/vllm-openai:nightly --model Qwen/Qwen3.6-35B-A3B-FP8 \
      --served-model-name levadinho --max-model-len 32768 --gpu-memory-utilization 0.85 \
      --kv-cache-dtype fp8 --reasoning-parser qwen3 >/dev/null
  fi
fi
echo -n "Loading model"
for _ in $(seq 1 90); do curl -sf localhost:8001/v1/models >/dev/null && break; echo -n .; sleep 5; done
curl -sf localhost:8001/v1/models >/dev/null || { echo " FAILED — see: docker logs levadinho-llm"; exit 1; }
echo " ok"

# 2. Webhook
if ! curl -sf localhost:5020/health >/dev/null; then
  setsid nohup uvicorn app:app --host 127.0.0.1 --port 5020 > app.log 2>&1 & echo $! > app.pid
  sleep 4
fi
curl -sf localhost:5020/health >/dev/null && echo "Webhook ok (:5020)"

# 3. Tunnel (empty config: ~/.cloudflared/config.yml belongs to the epiproc tunnel)
if [ -f tunnel.pid ] && kill -0 "$(cat tunnel.pid)" 2>/dev/null; then :; else
  echo "{}" > /tmp/claude-empty-cf.yml
  setsid nohup cloudflared --config /tmp/claude-empty-cf.yml tunnel --no-autoupdate \
    --url http://127.0.0.1:5020 > tunnel.log 2>&1 & echo $! > tunnel.pid
  sleep 15
fi
URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1)
for _ in $(seq 1 10); do curl -sf "$URL/health" >/dev/null && break; sleep 5; done
curl -sf "$URL/health" >/dev/null || { echo "Tunnel not reachable: $URL"; exit 1; }
echo "Tunnel ok: $URL"

# 4. Point Meta at it
curl -s -X POST "https://graph.facebook.com/v23.0/$APP_ID/subscriptions" \
  --data-urlencode "object=whatsapp_business_account" \
  --data-urlencode "callback_url=$URL/webhook" \
  --data-urlencode "verify_token=$WA_VERIFY_TOKEN" \
  --data-urlencode "fields=messages" \
  --data-urlencode "access_token=$APP_ID|$WA_APP_SECRET" | grep -q '"success":true' \
  && echo "Meta webhook → $URL/webhook" || echo "WARNING: couldn't update Meta webhook — paste $URL/webhook in the dashboard"

# 5. The test access token expires every 24 h
code=$(curl -s -o /dev/null -w '%{http_code}' "https://graph.facebook.com/v23.0/$WA_PHONE_NUMBER_ID" -H "Authorization: Bearer $WA_TOKEN")
[ "$code" = 200 ] && echo "Access token ok" || echo "WARNING: access token rejected ($code) — generate a new one in Meta and update WA_TOKEN in bot/.env"

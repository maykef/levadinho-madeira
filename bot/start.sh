#!/usr/bin/env bash
# Bring the Levadinho WhatsApp bot up: model (vLLM) → webhook + audio guide (uvicorn) →
# Tailscale Funnel (permanent URL) → point Meta's webhook at it. Check the GPU is free BEFORE running this.
# With the Twilio sandbox configured (TWILIO_* in .env, see README "Twilio sandbox") the Meta steps
# only warn: the endpoint for Twilio's console is $URL/twilio.
#   bot/start.sh
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
APP_ID=1433947322205284
TWILIO=""
[ -n "${TWILIO_ACCOUNT_SID:-}" ] && [ -n "${TWILIO_AUTH_TOKEN:-}" ] && [ -n "${TWILIO_WA_FROM:-}" ] && TWILIO=1

# 1. Model
if ! docker ps --format '{{.Names}}' | grep -qx levadinho-llm; then
  if docker ps -a --format '{{.Names}}' | grep -qx levadinho-llm; then
    docker start levadinho-llm >/dev/null
  else
    docker run -d --name levadinho-llm --gpus all --ipc=host --restart no \
      -p 127.0.0.1:8001:8000 -v /mnt/nvme8tb/huggingface_cache:/root/.cache/huggingface \
      -e HF_HUB_OFFLINE=1 vllm/vllm-openai:nightly --model Qwen/Qwen3.6-35B-A3B-FP8 \
      --served-model-name levadinho --max-model-len 32768 --gpu-memory-utilization 0.85 \
      --kv-cache-dtype fp8 --reasoning-parser qwen3 \
      --enable-auto-tool-choice --tool-call-parser qwen3_coder >/dev/null
  fi
fi
echo -n "Loading model"
for _ in $(seq 1 90); do curl -sf localhost:8001/v1/models >/dev/null && break; echo -n .; sleep 5; done
curl -sf localhost:8001/v1/models >/dev/null || { echo " FAILED — see: docker logs levadinho-llm"; exit 1; }
echo " ok"

# 2. Webhook. The previous app.log is kept (moved to logs/app-<its last write>.log, 60 newest kept):
#    overwriting it on 30 Sep 2026 destroyed the only record of why messages had stopped arriving.
mkdir -p logs
touch .running          # "the bot should be up": the watchdog only acts while this exists (stop.sh removes it)
if ! curl -sf localhost:5020/health >/dev/null; then
  if [ -s app.log ]; then
    mv app.log "logs/app-$(date -r app.log +%Y%m%d-%H%M%S).log"
    ls -1t logs/app-*.log 2>/dev/null | tail -n +61 | xargs -r rm -f
  fi
  # --no-access-log: the access log would record visitors' IP addresses
  setsid nohup uvicorn app:app --host 127.0.0.1 --port 5020 --no-access-log >> app.log 2>&1 & echo $! > app.pid
  sleep 4
fi
curl -sf localhost:5020/health >/dev/null && echo "Webhook ok (:5020)"

# 3. Public URL: Tailscale Funnel path /levadinho → :5020 (the prefix is stripped). Other apps'
#    Funnel routes on this machine are left alone.
URL=https://microscopy-rig-system.tail53cc58.ts.net/levadinho
tailscale funnel status 2>/dev/null | grep -q '/levadinho proxy http://127.0.0.1:5020' \
  || tailscale funnel --bg --yes --set-path /levadinho http://127.0.0.1:5020 >/dev/null
curl -sf "$URL/health" >/dev/null || { echo "Funnel not reachable: $URL"; exit 1; }
echo "Funnel ok: $URL  (guide: $URL/guide/)"

# 4. Point Meta at it
curl -s -X POST "https://graph.facebook.com/v23.0/$APP_ID/subscriptions" \
  --data-urlencode "object=whatsapp_business_account" \
  --data-urlencode "callback_url=$URL/webhook" \
  --data-urlencode "verify_token=${WA_VERIFY_TOKEN:-}" \
  --data-urlencode "fields=messages" \
  --data-urlencode "access_token=$APP_ID|${WA_APP_SECRET:-}" | grep -q '"success":true' \
  && echo "Meta webhook → $URL/webhook" || echo "WARNING: couldn't update Meta webhook — paste $URL/webhook in the dashboard"

# 5. The Meta access token (with Twilio configured, a rejected token is only a warning)
code=$(curl -s -o /dev/null -w '%{http_code}' "https://graph.facebook.com/v23.0/${WA_PHONE_NUMBER_ID:-}" -H "Authorization: Bearer ${WA_TOKEN:-}")
if [ "$code" = 200 ]; then echo "Access token ok"
elif [ -n "$TWILIO" ]; then echo "WARNING: Meta access token rejected ($code) — not fatal, the Twilio sandbox is configured"
else echo "WARNING: access token rejected ($code) — generate a new one in Meta and update WA_TOKEN in bot/.env"; fi

# 6. Twilio sandbox: credentials (passed to curl on stdin, never on the command line) and the endpoint
if [ -n "$TWILIO" ]; then
  code=$(printf 'user = "%s:%s"\n' "$TWILIO_ACCOUNT_SID" "$TWILIO_AUTH_TOKEN" | curl -s -K - -o /dev/null -w '%{http_code}' \
    "https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json")
  [ "$code" = 200 ] && echo "Twilio credentials ok" || echo "WARNING: Twilio rejected the credentials ($code) — check TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN in bot/.env"
  echo "Twilio sandbox webhook (\"When a message comes in\", POST): ${TWILIO_WEBHOOK_URL:-$URL/twilio}"
fi

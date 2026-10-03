#!/usr/bin/env bash
# Levadinho watchdog — run from cron every 5 minutes:
#   */5 * * * * /mnt/nvme8tb/levadinho_madeira/Levadinho/bot/watchdog.sh
#
# Only acts while the bot is meant to be up (bot/.running, created by start.sh, removed by stop.sh).
# Each run appends ONE line to logs/watchdog.log:
#   webhook  local /health                      (uvicorn alive)
#   funnel   public https://…/levadinho/health  (Tailscale Funnel route → webhook)
#   meta     Graph API with our token           (token valid, app not blocked — "API access blocked");
#            skipped when WA_TOKEN is empty or the Twilio sandbox is configured (TWILIO_* in .env)
#   model    /v1/models, only if the levadinho-llm container is running
#            (with wake-on-demand a stopped container is normal: it wakes on the next message)
# After 3 consecutive failing runs it does a FULL restart (stop.sh --keep-running, GPU shown, start.sh,
# GPU shown), at most once an hour, and never if another process holds the GPU after the stop.
set -uo pipefail
# cron runs with a minimal PATH: uvicorn (conda), docker, tailscale, nvidia-smi
export PATH="/home/microscopy-rig/miniforge3/bin:/usr/bin:/usr/bin:/usr/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "$0")"
[ -f .running ] || exit 0
mkdir -p logs
LOG=logs/watchdog.log
STATE=logs/watchdog.state          # "<consecutive failures> <epoch of last auto-restart>"
URL=https://microscopy-rig-system.tail53cc58.ts.net/levadinho
set -a; . ./.env; set +a
now() { date '+%Y-%m-%d %H:%M:%S'; }
[ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 5000000 ] && mv "$LOG" "$LOG.1"

code() { curl -s -o /dev/null -m 10 -w '%{http_code}' "$@"; }
webhook=$(code http://127.0.0.1:5020/health)
funnel=$(code "$URL/health")
if [ -z "${WA_TOKEN:-}" ] || { [ -n "${TWILIO_ACCOUNT_SID:-}" ] && [ -n "${TWILIO_AUTH_TOKEN:-}" ]; }; then
  # Meta's account is banned and replies go through Twilio: a dead token mustn't trigger restarts.
  # The reason shows in this run's log line (meta=skipped:no-token / meta=skipped:twilio).
  meta="skipped:$([ -z "${WA_TOKEN:-}" ] && echo no-token || echo twilio)"
else
  meta_body=$(curl -s -m 15 "https://graph.facebook.com/v23.0/${WA_PHONE_NUMBER_ID:-}?fields=id" -H "Authorization: Bearer $WA_TOKEN")
  if echo "$meta_body" | grep -q '"id"'; then meta=ok
  else meta="FAIL:$(echo "$meta_body" | python3 -c 'import json,sys
try: e=json.load(sys.stdin).get("error",{}); print(str(e.get("code"))+" "+e.get("message","")[:60])
except Exception: print("no answer")' 2>/dev/null)"; fi
fi
if docker ps --format '{{.Names}}' | grep -qx levadinho-llm; then
  model=$(code http://127.0.0.1:8001/v1/models)
else
  model=asleep
fi

fails=0; last_restart=0
[ -f "$STATE" ] && read -r fails last_restart < "$STATE"
bad=()
[ "$webhook" = 200 ] || bad+=("webhook=$webhook")
[ "$funnel" = 200 ] || bad+=("funnel=$funnel")
[ "$meta" = ok ] || [ "${meta%%:*}" = skipped ] || bad+=("meta=$meta")
[ "$model" = 200 ] || [ "$model" = asleep ] || bad+=("model=$model")

if [ ${#bad[@]} -eq 0 ]; then
  echo "$(now) ok   webhook=200 funnel=200 meta=$meta model=$model" >> "$LOG"
  echo "0 $last_restart" > "$STATE"
  exit 0
fi

fails=$((fails + 1))
echo "$(now) FAIL ($fails in a row) ${bad[*]}" >> "$LOG"
echo "$fails $last_restart" > "$STATE"
[ "$fails" -ge 3 ] || exit 0

if [ $(( $(date +%s) - last_restart )) -lt 3600 ]; then
  echo "$(now)      restart skipped: one already done in the last hour" >> "$LOG"
  exit 0
fi

{
  echo "$(now) FULL RESTART after $fails failing checks (${bad[*]})"
  echo "  GPU before: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader)"
  ./stop.sh --keep-running 2>&1 | sed 's/^/  stop: /'
  sleep 5
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  echo "  GPU after stop: ${used} MiB used"
  if [ "${used:-0}" -gt 10000 ]; then
    echo "  NOT restarting the model: ${used} MiB still in use by another process. Webhook only."
    setsid nohup uvicorn app:app --host 127.0.0.1 --port 5020 --no-access-log >> app.log 2>&1 & echo $! > app.pid
  else
    ./start.sh 2>&1 | sed 's/^/  start: /'
  fi
  echo "  GPU after start: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader)"
} >> "$LOG"
echo "0 $(date +%s)" > "$STATE"

#!/usr/bin/env bash
# Shut the Levadinho bot down and free the GPU.   bot/stop.sh
cd "$(dirname "$0")"
for f in tunnel.pid app.pid; do
  [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null && echo "stopped ${f%.pid}"
  rm -f "$f"
done
docker stop levadinho-llm >/dev/null 2>&1 && echo "stopped model (levadinho-llm)"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

#!/usr/bin/env bash
# Nightly backup of the Levadinho analytics database (cron, 03:30). Keeps 30 days.
#   bot/db/backup.sh
set -euo pipefail
DEST=/mnt/tank/levadinho_backup/db
mkdir -p "$DEST"
f="$DEST/levadinho-$(date +%F).sql.gz"
docker exec levadinho-db pg_dump -U levadinho -d levadinho --no-owner | gzip > "$f.tmp" && mv "$f.tmp" "$f"
find "$DEST" -name 'levadinho-*.sql.gz' -mtime +30 -delete

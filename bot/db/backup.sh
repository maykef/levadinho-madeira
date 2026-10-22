#!/usr/bin/env bash
# Nightly backup of the Levadinho analytics database (cron, 03:30). Keeps 30 days.
#   bot/db/backup.sh
set -euo pipefail
DEST=/mnt/tank/levadinho_backup/db
mkdir -p "$DEST"
f="$DEST/levadinho-$(date +%F).sql.gz"
docker exec levadinho-db pg_dump -U levadinho -d levadinho --no-owner | gzip > "$f.tmp" && mv "$f.tmp" "$f"
find "$DEST" -name 'levadinho-*.sql.gz' -mtime +30 -delete
# Mobility flight/cruise/fare files (owner, 2026-10-22): the JSON day files are the source of truth
# for ota.arrivals/fare_ladder (--rebuild), so they ride along nightly. Keeps 30 days too.
MOB=/mnt/nvme8tb/levadinho_madeira/Levadinho/seo_research/funchal/mobility/data
m="$DEST/mobility-$(date +%F).tar.gz"
tar -czf "$m.tmp" -C "$MOB" arrivals cruise_calls.json ship_capacity.json ship_capacity_manual.json \
    $( [ -d "$MOB/fares" ] && echo fares ) 2>/dev/null && mv "$m.tmp" "$m"
find "$DEST" -name 'mobility-*.tar.gz' -mtime +30 -delete

#!/usr/bin/env bash
# Write the four TWILIO_* lines into bot/.env, asking for the SID and Auth Token without echoing them.
#   bash bot/twilio_env.sh
set -euo pipefail
cd "$(dirname "$0")"
# Claude Code's "!" prompt has no terminal on stdin: read would get end-of-input and save nothing.
[ -t 0 ] || { echo "No terminal on stdin: run this in a real terminal (ssh / local shell), not via Claude's ! prompt." >&2; exit 1; }
read -rsp "Twilio Account SID: " SID; echo
read -rsp "Twilio Auth Token: " TOK; echo
[[ "$SID" =~ ^AC[0-9a-f]{32}$ ]] || echo "WARNING: the SID doesn't look like AC + 32 hex characters (saved anyway)"
[[ "$TOK" =~ ^[0-9a-f]{32}$ ]] || echo "WARNING: the token doesn't look like 32 hex characters (saved anyway)"
umask 077
{ grep -v '^TWILIO_' .env || true
  printf 'TWILIO_ACCOUNT_SID=%s\n' "$SID"
  printf 'TWILIO_AUTH_TOKEN=%s\n' "$TOK"
  printf 'TWILIO_WA_FROM=whatsapp:+14155238886\n'
  printf 'TWILIO_WEBHOOK_URL=https://microscopy-rig-system.tail53cc58.ts.net/levadinho/twilio\n'
} > .env.new
chmod 600 .env.new && mv .env.new .env
unset SID TOK
echo "Saved: $(grep -c '^TWILIO_' .env) TWILIO_* lines in bot/.env"

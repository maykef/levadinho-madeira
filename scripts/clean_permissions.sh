#!/usr/bin/env bash
# Replace .claude/settings.local.json with a trimmed allow-list, dropping the
# one-off rules Claude Code accumulated (and the grep rule it warns about).
# Keeps a backup at .claude/settings.local.json.bak and restores it if the
# result isn't valid JSON. Run from anywhere: scripts/clean_permissions.sh
set -euo pipefail

cd "$(dirname "$0")/.."
F=.claude/settings.local.json

[ -f "$F" ] && cp "$F" "$F.bak" && echo "Backup: $F.bak"

cat > "$F" <<'EOF'
{
  "permissions": {
    "allow": [
      "Bash(git remote *)",
      "Bash(git fetch *)",
      "Bash(git pull *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git push *)",
      "Bash(git rm *)",
      "Bash(git rebase *)",
      "Bash(git checkout *)",
      "Bash(git -c core.editor=true rebase --continue)",
      "Bash(gh run *)",
      "Bash(python3 *)",
      "Bash(pip install *)",
      "Bash(python scripts/update_status.py)",
      "Bash(python scripts/gen_spokes.py)",
      "Bash(node --check dashboard.js)",
      "Read(//tmp/**)",
      "Read(//mnt/nvme8tb/3d_segmentation/**)",
      "WebSearch",
      "WebFetch(domain:visitmadeira.com)",
      "WebFetch(domain:www.rexby.com)",
      "WebFetch(domain:www.theroadreel.com)",
      "WebFetch(domain:www.picturetheworld.co)",
      "WebFetch(domain:beyondmadeira.com)",
      "WebFetch(domain:madeirahiking.org)",
      "WebFetch(domain:funchalnoticias.net)",
      "WebFetch(domain:www.picotransfers.com)"
    ]
  }
}
EOF

if python3 -m json.tool "$F" >/dev/null; then
  echo "OK: $F cleaned ($(grep -cE '^\s+"(Bash|Read|Web)' "$F") rules). Restart Claude Code to pick it up."
else
  echo "Invalid JSON — restoring backup" >&2
  mv "$F.bak" "$F"
  exit 1
fi

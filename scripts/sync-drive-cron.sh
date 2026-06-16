#!/usr/bin/env bash
# Weekly Google Drive invoice sync — install with: crontab -e
# 0 6 * * 1 /home/ubuntu/seben_project/scripts/sync-drive-cron.sh
set -euo pipefail

ROOT="/home/ubuntu/seben_project"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/drive-sync.log"
mkdir -p "$LOG_DIR"

{
  echo "=== Drive sync $(date -Iseconds) ==="
  cd "$ROOT/backend"
  source venv/bin/activate
  python scripts/sync_all_drive.py
} >> "$LOG_FILE" 2>&1

#!/usr/bin/env bash
# Daily copy of the SQLite database (it holds workout types and assessments,
# which can't be rebuilt from the TCX files). Run by cadence-backup.timer.
set -euo pipefail

DB_DIR="${CADENCE_DB_DIR:-$HOME/cadencia-ia/data}"
KEEP=14  # days of backups to keep

# SQLite's backup API gives a consistent copy even while the app is running.
docker exec -i cadence-ia python - <<'EOF'
import datetime, pathlib, sqlite3

backups = pathlib.Path("/data/db/backups")
backups.mkdir(exist_ok=True)
target = backups / f"cadence-{datetime.date.today()}.db"
source, copy = sqlite3.connect("/data/db/cadence.db"), sqlite3.connect(target)
source.backup(copy)
copy.close()
source.close()
print(f"Backup written: {target.name}")
EOF

# Remove the oldest backups, keeping the last $KEEP.
ls -1t "$DB_DIR"/backups/cadence-*.db | tail -n +$((KEEP + 1)) | xargs -r rm --

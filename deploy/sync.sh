#!/usr/bin/env bash
# Download new workouts from iCloud and store them in the database.
# Run every 15 minutes by cadence-sync.timer.
set -euo pipefail

TCX_DIR="${CADENCE_TCX_DIR:-$HOME/cadencia-ia/entrada}"

# `copy` never deletes anything, unlike `sync` or `move`.
rclone copy icloud:cadencia-ia/entrada "$TCX_DIR" --include "*.tcx"

# Analyze the new files inside the running container.
docker exec cadence-ia cadence-ia ingest

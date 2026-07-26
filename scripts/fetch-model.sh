#!/usr/bin/env bash
# Download a GGUF from Hugging Face into models/.
#
#   scripts/fetch-model.sh <repo-id> <filename>
#
# Resumable: re-run after an interrupted download and it picks up where it left
# off, which matters on a slow link with an 18 GB file.
set -euo pipefail

REPO="${1:?usage: fetch-model.sh <repo-id> <filename>}"
FILE="${2:?usage: fetch-model.sh <repo-id> <filename>}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/models/$(basename "$FILE")"
mkdir -p "$ROOT/models"

URL="https://huggingface.co/$REPO/resolve/main/$FILE"

echo "repo : $REPO"
echo "file : $FILE"
echo "dest : $DEST"

if [ -f "$DEST" ]; then
    echo "already present ($(du -h "$DEST" | cut -f1)); resuming if incomplete"
fi

curl -L --fail --progress-bar --retry 5 --retry-delay 5 -C - -o "$DEST" "$URL"

echo
echo "downloaded $(du -h "$DEST" | cut -f1) -> $DEST"

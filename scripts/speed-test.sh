#!/usr/bin/env bash
# Measure prompt-processing and generation speed at several thread counts, so
# you can pick THREADS for serve.sh with data instead of folklore.
#
#   scripts/speed-test.sh models/some-model.gguf
set -euo pipefail

MODEL="${1:?usage: speed-test.sh <model.gguf>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/vendor/llama.cpp/build/bin/llama-bench"

[ -x "$BIN" ] || { echo "llama-bench not built. Run scripts/build.sh" >&2; exit 1; }

# pp = prompt tokens processed/s, tg = tokens generated/s.
exec "$BIN" \
    --model "$MODEL" \
    --threads "1,2,4" \
    -p 128 -n 64 \
    --repetitions 2 \
    -o md

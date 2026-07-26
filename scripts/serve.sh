#!/usr/bin/env bash
# Start llama-server on a GGUF, CPU-only, tuned for this box.
#
#   scripts/serve.sh models/some-model.gguf [extra llama-server args...]
#
# Env overrides: THREADS, CTX, PORT, BATCH
set -euo pipefail

MODEL="${1:?usage: serve.sh <model.gguf> [extra args...]}"
shift || true

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="$ROOT/vendor/llama.cpp/build/bin/llama-server"

[ -x "$BIN" ] || { echo "llama-server not built. Run scripts/build.sh" >&2; exit 1; }
[ -f "$MODEL" ] || { echo "no such model: $MODEL" >&2; exit 1; }

# Physical cores, not hyperthreads: generation is memory-bound, so the extra
# logical cores mostly add contention. Override with THREADS= if you disagree.
DEFAULT_THREADS="$(lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l)"

THREADS="${THREADS:-$DEFAULT_THREADS}"

# Context has to hold the prompt *and* the whole response. A reasoning model can
# burn 8k tokens thinking before it writes a line of code, and when it hits the
# ceiling mid-thought you get a truncated response with no answer in it -- which
# scores as a failure that looks like incompetence. 8192 was measurably too
# small for gpt-oss-20b: it hit the wall on 7 of 12 spec attempts. Raise it
# further (CTX=32768) for reasoning models; lower it to save RAM for the rest.
CTX="${CTX:-16384}"
PORT="${PORT:-8080}"
BATCH="${BATCH:-512}"

echo "model   : $MODEL"
echo "threads : $THREADS   ctx: $CTX   port: $PORT"
echo

# MLOCK=1 pins weights in RAM, but needs a raised RLIMIT_MEMLOCK ('ulimit -l')
# or it just warns and carries on. Off by default: with 30 GB of RAM and nothing
# else running, the page cache keeps the weights resident anyway.
MLOCK_FLAG=()
[ "${MLOCK:-0}" = "1" ] && MLOCK_FLAG=(--mlock)

# --jinja uses the chat template embedded in the GGUF rather than a built-in
# guess. Qwen3 and gpt-oss have templates the legacy path renders wrong, which
# shows up as a model that looks much dumber than it is.
exec "$BIN" \
    --model "$MODEL" \
    --jinja \
    --host 127.0.0.1 --port "$PORT" \
    --threads "$THREADS" \
    --threads-batch "$THREADS" \
    --ctx-size "$CTX" \
    --batch-size "$BATCH" \
    --parallel 1 \
    --gpu-layers 0 \
    --no-webui \
    "${MLOCK_FLAG[@]}" \
    "$@"

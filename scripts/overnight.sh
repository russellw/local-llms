#!/usr/bin/env bash
# Benchmark several models back to back, unattended.
#
#   scripts/overnight.sh models/*.gguf
#   REPEATS=3 scripts/overnight.sh models/a.gguf models/b.gguf
#   SUITES=toolloop scripts/overnight.sh models/a.gguf     # agent loop only
#
# For each model: start a server, wait for it to answer, run both suites, stop
# the server, move on. A model that fails to load is logged and skipped rather
# than killing the whole night's run.
#
# Loading a model takes minutes on a cold page cache, so both suites run against
# the one server rather than paying that twice. The tool-loop suite is much the
# cheaper of the two -- a few hundred tokens per episode against a few thousand
# per coding task -- so putting it first means a model that is hopeless at
# driving a loop tells you so in the first few minutes.
#
# Results land in results/<model-basename>.jsonl and are resumable: if the run
# is interrupted, re-run the same command and it picks up the unfinished tasks.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPEATS="${REPEATS:-1}"
PORT="${PORT:-8080}"
# Generous by default: reasoning models need room to think before they answer,
# and a cap costs nothing for a model that stops on its own.
TOKEN_SCALE="${TOKEN_SCALE:-3}"
LOAD_TIMEOUT="${LOAD_TIMEOUT:-600}"   # seconds to wait for a big model to load
SUITES="${SUITES:-toolloop code}"     # which suites to run, in order
LOGDIR="$ROOT/results/logs"
mkdir -p "$LOGDIR"

[ $# -gt 0 ] || { echo "usage: overnight.sh <model.gguf> [model.gguf...]" >&2; exit 1; }

SERVER_PID=""
stop_server() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null
        for _ in $(seq 20); do
            kill -0 "$SERVER_PID" 2>/dev/null || break
            sleep 1
        done
        kill -9 "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null
    fi
    SERVER_PID=""
}
trap 'echo; echo "interrupted, stopping server"; stop_server; exit 130' INT TERM

echo "=== overnight run started $(date -Is) ==="
echo "models: $#   repeats: $REPEATS"
echo

for MODEL in "$@"; do
    LABEL="$(basename "$MODEL" .gguf)"
    LOG="$LOGDIR/$LABEL.server.log"

    echo "--- $LABEL ---"
    if [ ! -f "$MODEL" ]; then
        echo "  missing file, skipping"
        continue
    fi
    echo "  size: $(du -h "$MODEL" | cut -f1)   started: $(date +%H:%M:%S)"

    PORT="$PORT" "$ROOT/scripts/serve.sh" "$MODEL" > "$LOG" 2>&1 &
    SERVER_PID=$!

    ready=0
    for _ in $(seq "$LOAD_TIMEOUT"); do
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            echo "  server exited during load; see $LOG"
            break
        fi
        if curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
            ready=1
            break
        fi
        sleep 1
    done

    if [ "$ready" != 1 ]; then
        echo "  never became ready, skipping"
        stop_server
        continue
    fi

    echo "  loaded"
    for SUITE in $SUITES; do
        case "$SUITE" in
            toolloop) CMD=toolloop ;;
            code)     CMD=run ;;
            *) echo "  unknown suite '$SUITE', skipping"; continue ;;
        esac
        echo "  running $SUITE suite"
        python3 -m bench "$CMD" \
            --label "$LABEL" \
            --url "http://127.0.0.1:$PORT" \
            --repeats "$REPEATS" \
            --max-tokens-scale "$TOKEN_SCALE" \
            2>&1 | sed 's/^/    /'
    done

    stop_server
    echo "  finished: $(date +%H:%M:%S)"
    echo
done

echo "=== all models done $(date -Is) ==="
python3 -m bench report --write

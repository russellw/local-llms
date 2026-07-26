#!/usr/bin/env bash
# Build (or rebuild) llama.cpp in vendor/. Takes a while on a 2-core box.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/vendor/llama.cpp"

if [ ! -d "$SRC" ]; then
    mkdir -p "$ROOT/vendor"
    git clone --depth 1 https://github.com/ggml-org/llama.cpp "$SRC"
fi

cd "$SRC"

# LLAMA_CURL=OFF avoids a libcurl-dev build dependency; we fetch models with
# scripts/fetch-model.sh instead of llama-server's -hf flag.
cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=ON \
    -DLLAMA_CURL=OFF \
    -DLLAMA_BUILD_TESTS=OFF \
    -DLLAMA_BUILD_EXAMPLES=OFF

nice -n 5 cmake --build build --config Release -j"$(nproc)"

echo
echo "built: $SRC/build/bin"
"$SRC/build/bin/llama-server" --version

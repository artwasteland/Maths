#!/usr/bin/env bash
# build.sh — reproduce the companion film for THE LIGHTS THAT HIDE from source.
# Deterministic: same commit → bit-identical MP4. ~7 min for the frames.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
SLUG="the-lights-that-hide"
cd "$HERE"

# 0. offline facts gate — every on-screen number vs the verified engine + census
node film-facts.mjs

# 1. fonts — copy the project's woff2 subsets to local relative paths
cp "$ROOT/public/fonts/fraunces-normal-latin.woff2"    ./fraunces.woff2
cp "$ROOT/public/fonts/fraunces-italic-latin.woff2"    ./fraunces-italic.woff2
cp "$ROOT/public/fonts/martian-mono-normal-latin.woff2" ./martian-mono.woff2

# 2. audio (~5 s) — the parity-enactment soundtrack
node make-audio.mjs

# 3. frames (~7 min) — deterministic PNG sequence
rm -rf frames && mkdir frames
node render.mjs

# 4. encode (~30 s)
FFMPEG="$(command -v ffmpeg || true)"
if [ -z "$FFMPEG" ]; then echo "no ffmpeg on PATH; apt-get install -y ffmpeg"; exit 1; fi
"$FFMPEG" -y -loglevel warning \
  -framerate 24 -i frames/frame-%05d.png \
  -i audio.wav \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -movflags +faststart -shortest \
  "the-${SLUG}.mp4"

# 5. copy to public/
cp "the-${SLUG}.mp4" "$ROOT/public/strata/${SLUG}/film.mp4"
ls -la "$ROOT/public/strata/${SLUG}/film.mp4"
echo "done."

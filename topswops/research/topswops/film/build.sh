#!/usr/bin/env bash
# build.sh — reproduce the 150-second companion film for THE TOPSWOPS MACHINE.
#
#   bash research/topswops/film/build.sh
#
# Output: public/strata/topswops-machine/film.mp4 (1920×1080, 24 fps, H.264+AAC)
#
# Deterministic — same commit ⇒ bit-identical MP4. Everything the film draws is
# computed live from the stratum's own engine (research/topswops/engine.mjs):
# the 16-flip longest game, the exhaustive 5,040-deal histogram, the live
# sequence table, the Garden-of-Eden count. The audio's melody is that same
# longest game, played note-per-flip (declared in make-audio.mjs).

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
cd "$HERE"

echo "[1/5] copying fonts …"
cp "$ROOT/public/fonts/fraunces-normal-latin.woff2"     ./fraunces.woff2
cp "$ROOT/public/fonts/fraunces-italic-latin.woff2"     ./fraunces-italic.woff2
cp "$ROOT/public/fonts/martian-mono-normal-latin.woff2" ./martian-mono.woff2

echo "[2/5] generating audio.wav …"
node make-audio.mjs

echo "[3/5] rendering frames …"
rm -rf frames && mkdir frames
node render.mjs

echo "[4/5] resolving ffmpeg …"
# Use a FULL ffmpeg (libx264 + -preset/-crf). NOTE: the Playwright-bundled
# /opt/pw-browsers/ffmpeg-*/ffmpeg-linux is a STRIPPED build that rejects
# '-preset' — do not use it. Reliable path in this environment:
#   apt-get update && apt-get install -y ffmpeg   (system ffmpeg 6.x)
# Prefer a system ffmpeg, then npm's ffmpeg-static as a fallback.
FFMPEG="$(command -v ffmpeg || true)"
if [ -z "$FFMPEG" ]; then
  echo "  no system ffmpeg — install with: apt-get install -y ffmpeg"
  echo "  trying npm ffmpeg-static (can arrive truncated through a proxy) …"
  npm install --no-save ffmpeg-static >/dev/null 2>&1
  FFMPEG="$(node -e 'process.stdout.write(require("ffmpeg-static"))')"
fi
echo "  using: $FFMPEG"

echo "      encoding MP4 …"
"$FFMPEG" -y -loglevel warning \
  -framerate 24 -i frames/frame-%05d.png \
  -i audio.wav \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 192k \
  -movflags +faststart -shortest \
  the-topswops-machine.mp4

echo "[5/5] copying to public/ …"
mkdir -p "$ROOT/public/strata/topswops-machine"
cp the-topswops-machine.mp4 "$ROOT/public/strata/topswops-machine/film.mp4"
ls -lh "$ROOT/public/strata/topswops-machine/film.mp4"
echo "  → $ROOT/public/strata/topswops-machine/film.mp4"

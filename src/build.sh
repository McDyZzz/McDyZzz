#!/bin/sh
# Regenerates every generated image in ../assets/ from the generators in gen/.
# assets/header.svg is hand-maintained: no generator writes it, and the footer is built from it.
#
# Usage: ./build.sh           regenerate the assets (needs python3 only)
#        ./build.sh --check   also build the preview (index.html) and run check.mjs
#                             (needs the gh CLI signed in, Node 22+, Google Chrome, xmllint)
set -eu
cd "$(dirname "$0")"
OUT=../assets

python3 gen/about/build.py "$OUT"
python3 gen/headings.py "$OUT"
python3 gen/cards/build_cards.py "$OUT"
python3 gen/back/build_back.py "$OUT"
python3 gen/egg/build.py "$OUT"
python3 gen/footer/build.py "$OUT"

if [ "${1:-}" = "--check" ]; then
  python3 build_preview.py
  node check.mjs
fi

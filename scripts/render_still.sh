#!/usr/bin/env bash
# usage: render_still.sh file.blend out_prefix percent samples frame [frame ...]
# Renders Cycles stills in a separate background Blender (GPU if available).
set -euo pipefail
if [ -z "${BLENDER:-}" ]; then
  if [ -x /Applications/Blender.app/Contents/MacOS/Blender ]; then
    BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
  else
    BLENDER=$(command -v blender) || { echo "blender not found; set BLENDER=/path/to/blender" >&2; exit 1; }
  fi
fi
here="$(cd "$(dirname "$0")" && pwd)"
blend=$1; out=$2; pct=$3; spp=$4; shift 4
frames=(); for f in "$@"; do frames+=(-f "$f"); done
"$BLENDER" -b "$blend" --python "$here/gpu_setup.py" -o "${out}_####" -F PNG "${frames[@]}" -- "$pct" "$spp" 2>&1 \
  | grep -E "render devices|Saved:|Error" || true

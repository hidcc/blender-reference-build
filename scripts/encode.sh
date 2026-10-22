#!/usr/bin/env bash
# usage: encode.sh frames_dir out.mp4 [fps]   (expects frame_0001.png ...)
set -euo pipefail
ffmpeg -loglevel error -y -framerate "${3:-24}" -i "$1/frame_%04d.png" -c:v libx264 -pix_fmt yuv420p -crf 16 "$2"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$2"

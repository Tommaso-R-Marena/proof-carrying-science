#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 scripts/verify_v07_release.py
printf '\nLocal mathematical evidence replay succeeded. This is NOT Lean or ONNX Runtime certification.\n'

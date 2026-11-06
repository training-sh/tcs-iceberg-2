#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.crc/bin/oc:$PATH"
# Host-level lock prevents two copies of this runner from overlapping.
exec 9>"$HOME/.movielens-classroom.lock"
flock -n 9 || { echo 'Another MovieLens pipeline is running.' >&2; exit 1; }
for stage in 01 02 03 04; do
  python3 run-stage.py "$stage"
done

#!/usr/bin/env bash
# Copy the provided scripts and dataset to the shared Kubernetes volume.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.crc/bin/oc:$PATH"
source_dir="$HOME/data/movielens-small"
for name in movies.csv ratings.csv tags.csv links.csv README.txt; do
  test -r "$source_dir/$name"
done
oc exec -n bigdata spark-master-0 -c jupyter -- mkdir -p /workspace/movielens-classroom/source
for file in 0*.py; do
  oc cp "$file" "bigdata/spark-master-0:/workspace/movielens-classroom/$(basename "$file")" -c jupyter
done
for name in movies.csv ratings.csv tags.csv links.csv README.txt; do
  oc cp "$source_dir/$name" "bigdata/spark-master-0:/workspace/movielens-classroom/source/$name" -c jupyter
done
printf '%s\n' 'Published source and scripts. No Spark jobs have been started.'

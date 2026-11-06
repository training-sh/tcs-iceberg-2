#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.crc/bin/oc:$PATH"
# Supporting JSON first, paused DAG entrypoint last.
oc cp spark-job-template.json bigdata/airflow-0:/opt/airflow/dags/spark-job-template.json -c airflow
oc cp airflow_movielens.py bigdata/airflow-0:/opt/airflow/dags/airflow_movielens_classroom.py -c airflow
printf '%s\n' 'Published the paused classroom DAG. Allow up to five minutes for discovery.'

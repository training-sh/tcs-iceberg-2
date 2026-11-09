#!/usr/bin/env bash
# Publish supplied source files. This does not trigger DAG runs or Spark Jobs.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.crc/bin/oc:$PATH"

# Check every source before making any cluster changes.
helpers=(
    ./dags/course_airflow_ecomm/__init__.py
    ./dags/course_airflow_ecomm/settings.py
    ./dags/course_airflow_ecomm/sql.py
    ./dags/course_airflow_ecomm/tasks.py
    ./dags/course_airflow_ecomm/trino_http.py
    ./dags/course_airflow_ecomm/spark_job.py
)
for file in "${helpers[@]}" \
    ./dags/sql/hello_trino.sql ./spark/spark_ecomm.py \
    ./dags/airflow_hello_trino.py ./dags/airflow_ecomm_dags.py; do
    test -r "$file" || { printf 'Missing source file: %s\n' "$file" >&2; exit 1; }
done
command -v oc >/dev/null
oc get pod -n bigdata airflow-0 spark-master-0 >/dev/null
oc exec -n bigdata airflow-0 -c airflow -- test -d /opt/airflow/dags
oc exec -n bigdata airflow-0 -c airflow -- sh -c 'command -v tar >/dev/null'
oc exec -n bigdata spark-master-0 -c jupyter -- sh -c 'command -v tar >/dev/null'

# Run only while these course DAGs and their Spark Jobs are idle.
oc exec -n bigdata airflow-0 -c airflow -- mkdir -p /opt/airflow/dags/course_airflow_ecomm /opt/airflow/dags/sql
oc exec -n bigdata spark-master-0 -c jupyter -- mkdir -p /workspace/user_notebooks/09-airflow-ecommerce

# Supporting files first. Individual copies prevent nested directories on reruns.
for file in "${helpers[@]}"; do
    oc cp "$file" "bigdata/airflow-0:/opt/airflow/dags/course_airflow_ecomm/$(basename "$file")" -c airflow
done
oc cp ./dags/sql/hello_trino.sql bigdata/airflow-0:/opt/airflow/dags/sql/hello_trino.sql -c airflow
oc cp ./spark/spark_ecomm.py bigdata/spark-master-0:/workspace/user_notebooks/09-airflow-ecommerce/spark_ecomm.py -c jupyter

# Publish DAG entrypoints last.
oc cp ./dags/airflow_hello_trino.py bigdata/airflow-0:/opt/airflow/dags/airflow_hello_trino.py -c airflow
oc cp ./dags/airflow_ecomm_dags.py bigdata/airflow-0:/opt/airflow/dags/airflow_ecomm_dags.py -c airflow
printf '%s\n' 'Course source files copied. No DAG runs or Spark Jobs were triggered.'
printf '%s\n' 'Allow discovery to complete, then check the Airflow DAG list and import errors.'
oc exec -n bigdata airflow-0 -c airflow -- airflow dags list-import-errors

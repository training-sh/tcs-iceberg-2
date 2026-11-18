#!/usr/bin/env bash
# Publish only. The generated Airflow DAG performs all database and Spark work.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.crc/bin/oc:$PATH"

run_id="$(date +airflow_%Y%m%d_%H%M)"
airflow=(oc exec -n bigdata airflow-0 -c airflow --)
dag_dir=/opt/airflow/dags
helper_dir="$dag_dir/course_airflow_ecomm"
spark_dir=/workspace/user_notebooks/09-airflow-ecommerce
helpers=(__init__.py settings.py sql.py tasks.py trino_http.py spark_job.py classroom.py mysql_seed.sql)

for file in "${helpers[@]}"; do test -r "dags/course_airflow_ecomm/$file"; done
test -r spark/spark_ecomm.py
oc wait -n bigdata --for=condition=Ready pod/airflow-0 pod/mysql-0 --timeout=120s
"${airflow[@]}" test -r /opt/course/job-template.json
printf '%s\n' 'Before publish:'
"${airflow[@]}" sh -c 'if test -f "$1"; then grep "^RUN_ID =" "$1"; else echo "No classroom DAG file yet."; fi' sh "$dag_dir/airflow_ecommerce.py"

# Read the existing MySQL image and the Secret reference from this cluster.
mysql_image="$(oc get pod -n bigdata mysql-0 -o 'jsonpath={.spec.containers[?(@.name=="mysql")].image}')"
root_secret="$(oc get pod -n bigdata mysql-0 -o 'jsonpath={.spec.containers[?(@.name=="mysql")].env[?(@.name=="MYSQL_ROOT_PASSWORD")].valueFrom.secretKeyRef}')"
if [[ -z "$mysql_image" || -z "$root_secret" ]]; then
    printf '%s\n' 'Expected mysql-0 to reference a Secret in MYSQL_ROOT_PASSWORD.' >&2
    exit 1
fi

"${airflow[@]}" mkdir -p "$helper_dir"
oc exec -n bigdata spark-master-0 -c jupyter -- mkdir -p "$spark_dir"
for file in "${helpers[@]}"; do
    oc cp "dags/course_airflow_ecomm/$file" "bigdata/airflow-0:$helper_dir/$file" -c airflow
done
oc cp spark/spark_ecomm.py "bigdata/spark-master-0:$spark_dir/spark_ecomm.py" -c jupyter

# Replace the same DAG entrypoint after the generated code has been checked.
oc exec -i -n bigdata airflow-0 -c airflow -- python - "$dag_dir" "$run_id" "$mysql_image" "$root_secret" <<'PY'
import json
import os
from pathlib import Path
import re
import runpy
import sys
import tempfile
from fcntl import flock, LOCK_EX

dag_dir, run_id, image, secret_json = sys.argv[1:]
secret = json.loads(secret_json)
target = Path(dag_dir) / "airflow_ecommerce.py"
with tempfile.NamedTemporaryFile(mode="w", dir=dag_dir, delete=False) as handle:
    temporary = Path(handle.name)
    handle.write(
        "from pathlib import Path\n"
        "import sys\n\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
        "from course_airflow_ecomm.classroom import build_dag\n\n"
        f"RUN_ID = {run_id!r}\n"
        f"ecommerce_dag = build_dag(RUN_ID, {image!r}, {secret!r}, dag_id='airflow_ecommerce')\n"
    )
try:
    if runpy.run_path(str(temporary))["ecommerce_dag"].dag_id != "airflow_ecommerce":
        raise ValueError("Expected the airflow_ecommerce DAG")
    os.chmod(temporary, 0o644)
    with target.with_suffix(".lock").open("a") as lock:
        flock(lock, LOCK_EX)
        previous = target.read_text() if target.exists() else ""
        if (re.search(rf"^RUN_ID = ['\"]{run_id}['\"]$", previous, re.M)
                or target.with_name(f"{run_id}.py").exists()):
            sys.exit(f"RUN_ID {run_id} is already in use. Publish in a new minute.")
        os.replace(temporary, target)
finally:
    temporary.unlink(missing_ok=True)
PY
printf 'RUN_ID=%s\n' "$run_id"
printf '%s\n' 'After publish:'
"${airflow[@]}" grep '^RUN_ID =' "$dag_dir/airflow_ecommerce.py"
printf '%s\n' 'In Airflow, unpause and trigger airflow_ecommerce after discovery.'

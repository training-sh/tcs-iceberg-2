"""Wait for the supplied DAG, run it once, check every task, and pause it again."""
import uuid
import json
from pathlib import Path
import subprocess
import time

DAG = "classroom_movielens_s01"


def cli(*args):
    result = subprocess.run(["oc", "exec", "-n", "bigdata", "airflow-0", "-c", "airflow", "--", "airflow", *args],
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2500:] or result.stdout[-2500:])
    return result.stdout


def main():
    deadline = time.monotonic() + 420
    print("Waiting for classroom DAG discovery (up to seven minutes)...", flush=True)
    while time.monotonic() < deadline:
        errors = json.loads(cli("dags", "list-import-errors", "-o", "json"))
        if any("airflow_movielens_classroom.py" in str(item) for item in errors):
            raise RuntimeError("Classroom DAG has an import error; stop and report the output")
        dags = json.loads(cli("dags", "list", "-o", "json"))
        if any(item["dag_id"] == DAG for item in dags):
            break
        time.sleep(10)
    else:
        raise TimeoutError("DAG not discovered; stop and report the output")
    existing = json.loads(cli("dags", "list-runs", DAG, "-o", "json"))
    if any(item["state"] in ("queued", "running") for item in existing):
        raise RuntimeError("A classroom Airflow run is already active; wait before starting another")
    run_id = "manual__classroom_" + uuid.uuid4().hex[:12]
    try:
        cli("dags", "unpause", DAG)
        cli("dags", "trigger", DAG, "--run-id", run_id)
        print("AIRFLOW_RUN", run_id, flush=True)
        deadline = time.monotonic() + 4200
        previous = None
        while time.monotonic() < deadline:
            rows = json.loads(cli("dags", "list-runs", DAG, "-o", "json"))
            run = next((row for row in rows if row.get("run_id", row.get("dag_run_id")) == run_id), None)
            if run:
                state = run["state"]
                if state != previous:
                    print("AIRFLOW_STATE", state, flush=True)
                    previous = state
                if state in ("success", "failed"):
                    tasks = json.loads(cli("tasks", "states-for-dag-run", DAG, run_id, "-o", "json"))
                    for item in tasks:
                        print("AIRFLOW_TASK", item["task_id"], item["state"], flush=True)
                    if state != "success" or len(tasks) != 4 or any(t["state"] != "success" for t in tasks):
                        raise RuntimeError("Classroom DAG failed; inspect the task and its Spark Job logs")
                    print("AIRFLOW_PASS", run_id, flush=True)
                    folder = Path(__file__).resolve().parent / "logs"
                    folder.mkdir(exist_ok=True)
                    (folder / (run_id + ".json")).write_text(json.dumps({"dag_id": DAG, "run_id": run_id, "tasks": tasks}, indent=2))
                    return
            time.sleep(15)
        raise TimeoutError("DAG completion deadline exceeded; inspect its active task")
    finally:
        cli("dags", "pause", DAG)
        print("AIRFLOW_PAUSED", DAG, flush=True)


if __name__ == "__main__":
    main()

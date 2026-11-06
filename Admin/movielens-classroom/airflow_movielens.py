"""Optional manual Airflow orchestration; transformation files stay independent."""
from datetime import timedelta
from airflow.sdk import dag, task


@dag(
    dag_id="classroom_movielens_s01",
    schedule=None,
    catchup=False,
    is_paused_upon_creation=True,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={"retries": 0, "execution_timeout": timedelta(minutes=18)},
    tags=["course", "movielens"],
)
def movielens():
    @task
    def run_stage(stage):
        import copy
        import hashlib
        import json
        from pathlib import Path
        import time
        import requests
        from airflow.sdk import get_current_context

        scripts = {"01": "01_upload_bronze.py", "02": "02_bronze_to_silver.py",
                   "03": "03_silver_to_gold.py", "04": "04_gold_to_mysql.py"}
        identity = get_current_context()["run_id"] + ":" + stage
        name = "ml-classroom-af-" + stage + "-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
        sa = Path("/var/run/secrets/kubernetes.io/serviceaccount")
        session = requests.Session()
        session.trust_env = False
        session.headers["Authorization"] = "Bearer " + (sa / "token").read_text().strip()
        session.verify = str(sa / "ca.crt")

        def api(method, path, **kwargs):
            response = session.request(method, "https://kubernetes.default.svc" + path, timeout=20, **kwargs)
            if response.status_code == 409:
                return None
            if not response.ok:
                raise RuntimeError("Kubernetes API status " + str(response.status_code))
            return response.json()

        try:
            job = copy.deepcopy(json.loads(Path(__file__).with_name("spark-job-template.json").read_text()))
            job["metadata"] = {"name": name, "namespace": "bigdata", "labels": {"app": "movielens-classroom"}}
            spec = job["spec"]
            spec.update(backoffLimit=0, activeDeadlineSeconds=900, ttlSecondsAfterFinished=3600)
            pod = spec["template"]["spec"]
            if len(pod["containers"]) != 1:
                raise ValueError("Expected one existing driver container")
            pod["restartPolicy"] = "Never"
            driver = pod["containers"][0]
            driver["args"] = ["submit", "--master", "spark://spark-master:7077", "--deploy-mode", "client",
                              "--driver-memory", "512m", "--conf", "spark.driver.host=$(POD_IP)",
                              "--conf", "spark.driver.bindAddress=0.0.0.0", "--conf", "spark.cores.max=1",
                              "--conf", "spark.executor.cores=1", "--conf", "spark.executor.memory=512m",
                              "--conf", "spark.sql.shuffle.partitions=2",
                              "/workspace/movielens-classroom/" + scripts[stage]]
            driver["resources"] = {"requests": {"cpu": "100m", "memory": "512Mi"},
                                   "limits": {"cpu": "1", "memory": "1536Mi"}}
            if not any(e["name"] == "POD_IP" for e in driver.get("env", [])):
                driver.setdefault("env", []).append({"name": "POD_IP", "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}})
            path = "/apis/batch/v1/namespaces/bigdata/jobs"
            created = api("POST", path, json=job)
            if created is None:
                existing = api("GET", path + "/" + name)
                if existing["metadata"].get("labels", {}).get("app") != "movielens-classroom":
                    raise RuntimeError("Conflicting Job is not a MovieLens course Job")
            deadline = time.monotonic() + 960
            while time.monotonic() < deadline:
                status = api("GET", path + "/" + name).get("status", {})
                if status.get("succeeded", 0) >= 1:
                    print("MOVIELENS_STAGE_PASS", stage, name)
                    return {"stage": stage, "job": name}
                if any(c.get("type") == "Failed" and c.get("status") == "True" for c in status.get("conditions", [])):
                    raise RuntimeError("MovieLens stage failed; inspect Job " + name)
                time.sleep(5)
            raise TimeoutError("Job wait expired: " + name)
        finally:
            session.close()

    bronze = run_stage.override(task_id="upload_bronze")("01")
    silver = run_stage.override(task_id="bronze_to_silver")("02")
    gold = run_stage.override(task_id="silver_to_gold")("03")
    mysql = run_stage.override(task_id="gold_to_mysql")("04")
    bronze >> silver >> gold >> mysql


movielens_dag = movielens()

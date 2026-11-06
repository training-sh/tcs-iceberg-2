"""Run one independent script as a bounded driver Job on the existing Spark master."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import time
import uuid

STAGES = {
    "01": "01_upload_bronze.py",
    "02": "02_bronze_to_silver.py",
    "03": "03_silver_to_gold.py",
    "04": "04_gold_to_mysql.py",
}


def oc(*args):
    return subprocess.check_output(["oc", *args], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    args = parser.parse_args()
    # Load the manifest shipped in this downloaded exercise.
    job = copy.deepcopy(json.loads(Path(__file__).with_name("spark-job-template.json").read_text()))
    name = "ml-classroom-" + args.stage + "-" + uuid.uuid4().hex[:10]
    job["metadata"] = {"name": name, "namespace": "bigdata", "labels": {"app": "movielens-classroom"}}
    spec = job["spec"]
    spec.update(backoffLimit=0, activeDeadlineSeconds=900, ttlSecondsAfterFinished=3600)
    pod = spec["template"]["spec"]
    if len(pod["containers"]) != 1:
        raise ValueError("Expected the existing one-container driver template")
    pod["restartPolicy"] = "Never"
    driver = pod["containers"][0]
    driver["args"] = [
        "submit", "--master", "spark://spark-master:7077", "--deploy-mode", "client",
        "--driver-memory", "512m", "--conf", "spark.driver.host=$(POD_IP)",
        "--conf", "spark.driver.bindAddress=0.0.0.0", "--conf", "spark.cores.max=1",
        "--conf", "spark.executor.cores=1", "--conf", "spark.executor.memory=512m",
        "--conf", "spark.sql.shuffle.partitions=2",
        "/workspace/movielens-classroom/" + STAGES[args.stage],
    ]
    driver["resources"] = {"requests": {"cpu": "100m", "memory": "512Mi"},
                           "limits": {"cpu": "1", "memory": "1536Mi"}}
    if not any(e["name"] == "POD_IP" for e in driver.get("env", [])):
        driver.setdefault("env", []).append({"name": "POD_IP", "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}})
    subprocess.run(["oc", "create", "-f", "-"], input=json.dumps(job), text=True, check=True)
    print("JOB", name, flush=True)
    deadline = time.monotonic() + 960
    while time.monotonic() < deadline:
        status = json.loads(oc("get", "job", name, "-n", "bigdata", "-o", "json"))["status"]
        done = status.get("succeeded", 0) >= 1
        failed = any(c.get("type") == "Failed" and c.get("status") == "True" for c in status.get("conditions", []))
        if done or failed:
            log = oc("logs", "job/" + name, "-n", "bigdata")
            folder = Path(__file__).resolve().parent / "logs"
            folder.mkdir(exist_ok=True)
            (folder / (name + ".log")).write_text(log)
            for line in log.splitlines():
                if any(marker in line for marker in ("_PASS", "BUCKET_CREATED", "BUCKET_REUSED")):
                    print(line)
            if failed:
                raise RuntimeError("Job failed; inspect " + str(folder / (name + ".log")))
            print("STAGE_PASS", args.stage, name)
            return
        time.sleep(5)
    raise TimeoutError("Job wait expired: " + name)


if __name__ == "__main__":
    main()

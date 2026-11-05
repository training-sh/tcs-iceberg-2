"""Reuse the existing lab Job template with one Job per task-run identity."""
import copy
import hashlib
import json
from pathlib import Path
import time
from .settings import JOB_TEMPLATE, NAMESPACE, SCHEMA_NAME, SPARK_SCRIPT, RUN_SUFFIX

SA = Path("/var/run/secrets/kubernetes.io/serviceaccount")


def kube(method, path, **kwargs):
    import requests
    response = requests.request(
        method, "https://kubernetes.default.svc" + path,
        headers={"Authorization": "Bearer " + (SA / "token").read_text().strip()},
        verify=str(SA / "ca.crt"), timeout=20, **kwargs,
    )
    if response.status_code == 409:
        return {"course_conflict": True}
    if not response.ok:
        raise RuntimeError(f"Kubernetes API status {response.status_code}; inspect RBAC and Job events")
    return response.json()


def job_name(identity):
    return f"af-ecomm-{RUN_SUFFIX}-" + hashlib.sha256(identity.encode()).hexdigest()[:20]


def build_job(template, identity, input_table, output_table):
    job = copy.deepcopy(template)
    job["metadata"] = {
        "name": job_name(identity), "namespace": NAMESPACE,
        "labels": {"app": "airflow-ecommerce-course", "suffix": RUN_SUFFIX},
    }
    spec = job["spec"]
    spec.update(backoffLimit=0, activeDeadlineSeconds=600, ttlSecondsAfterFinished=3600)
    spec["template"].setdefault("metadata", {}).setdefault("labels", {}).update(
        {"app": "airflow-ecommerce-course", "suffix": RUN_SUFFIX}
    )
    pod = spec["template"]["spec"]
    if len(pod.get("containers", [])) != 1:
        raise ValueError("Expected one driver container in the existing Job template")
    if not any(v.get("persistentVolumeClaim", {}).get("claimName") == "spark-notebooks"
               for v in pod.get("volumes", [])):
        raise ValueError("Existing template must mount the spark-notebooks PVC")
    pod["restartPolicy"] = "Never"
    driver = pod["containers"][0]
    driver["args"] = [
        "submit", "--master", "spark://spark-master:7077", "--deploy-mode", "client",
        "--driver-memory", "512m", "--conf", "spark.driver.host=$(POD_IP)",
        "--conf", "spark.driver.bindAddress=0.0.0.0", "--conf", "spark.cores.max=1",
        "--conf", "spark.executor.cores=1", "--conf", "spark.executor.memory=512m",
        "--conf", "spark.sql.shuffle.partitions=2", SPARK_SCRIPT,
        "--schema", SCHEMA_NAME, "--input-table", input_table, "--output-table", output_table,
    ]
    env = driver.setdefault("env", [])
    if not any(v["name"] == "POD_IP" for v in env):
        env.append({"name": "POD_IP", "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}})
    # Preserve existing image, service account, Secret references and mounts.
    driver["resources"] = {
        "requests": {"cpu": "100m", "memory": "512Mi"},
        "limits": {"cpu": "1", "memory": "1536Mi"},
    }
    return job


def run_spark(identity, input_table, output_table):
    job = build_job(json.loads(Path(JOB_TEMPLATE).read_text()), identity, input_table, output_table)
    name = job["metadata"]["name"]
    path = f"/apis/batch/v1/namespaces/{NAMESPACE}/jobs"
    created = kube("POST", path, json=job)
    if created.get("course_conflict"):
        existing = kube("GET", path + "/" + name)
        labels = existing.get("metadata", {}).get("labels", {})
        if labels.get("app") != "airflow-ecommerce-course" or labels.get("suffix") != RUN_SUFFIX:
            raise RuntimeError("Existing Job is not owned by this course identifier")
    deadline = time.monotonic() + 660
    while time.monotonic() < deadline:
        current = kube("GET", path + "/" + name)
        status = current.get("status", {})
        if status.get("succeeded", 0) >= 1:
            return {"job": name, "output_table": output_table}
        if any(c.get("type") == "Failed" and c.get("status") == "True"
               for c in status.get("conditions", [])):
            raise RuntimeError(f"Spark Job failed: {name}; inspect its pod logs privately")
        time.sleep(5)
    raise TimeoutError(f"Job wait expired: {name}; its server-side deadline bounds remaining work")

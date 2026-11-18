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


def job_name(identity, suffix=RUN_SUFFIX):
    return f"af-ecomm-{suffix.replace('_', '-')}-" + hashlib.sha256(identity.encode()).hexdigest()[:20]


def build_job(template, identity, input_table, output_table, *, schema=SCHEMA_NAME):
    job = copy.deepcopy(template)
    suffix = RUN_SUFFIX if schema == SCHEMA_NAME else schema
    labels = {"app": "airflow-ecommerce-course", "suffix": suffix}
    job["metadata"] = {
        "name": job_name(identity, suffix), "namespace": NAMESPACE,
        "labels": labels,
    }
    spec = job["spec"]
    spec.update(backoffLimit=0, activeDeadlineSeconds=600, ttlSecondsAfterFinished=3600)
    spec["template"].setdefault("metadata", {}).setdefault("labels", {}).update(labels)
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
        "--schema", schema, "--input-table", input_table, "--output-table", output_table,
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


def run_spark(identity, input_table, output_table, *, schema=SCHEMA_NAME):
    job = build_job(json.loads(Path(JOB_TEMPLATE).read_text()), identity, input_table,
                    output_table, schema=schema)
    name = run_job(job)
    return {"job": name, "output_table": output_table}


def run_job(job):
    from requests.exceptions import ConnectionError, Timeout

    name = job["metadata"]["name"]
    path = f"/apis/batch/v1/namespaces/{NAMESPACE}/jobs"
    created = kube("POST", path, json=job)
    if created.get("course_conflict"):
        existing = kube("GET", path + "/" + name)
        labels = existing.get("metadata", {}).get("labels", {})
        if any(labels.get(key) != value for key, value in job["metadata"]["labels"].items()):
            raise RuntimeError("Existing Job is not owned by this course identifier")
    deadline = time.monotonic() + 660
    while time.monotonic() < deadline:
        try:
            current = kube("GET", path + "/" + name)
        except (ConnectionError, Timeout):
            print(f"Job status temporarily unavailable for {name}; checking again")
            time.sleep(5)
            continue
        status = current.get("status", {})
        if status.get("succeeded", 0) >= 1:
            return name
        if any(c.get("type") == "Failed" and c.get("status") == "True"
               for c in status.get("conditions", [])):
            raise RuntimeError(f"Job failed: {name}; inspect with oc logs -n {NAMESPACE} job/{name}")
        time.sleep(5)
    raise TimeoutError(f"Job wait expired: {name}; its server-side deadline bounds remaining work")

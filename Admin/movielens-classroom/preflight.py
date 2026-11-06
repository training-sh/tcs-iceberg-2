"""Check the provided classroom services; change no cluster resources."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def oc(*args):
    return subprocess.check_output(["oc", *args], text=True).strip()


def resource(kind, name):
    return json.loads(oc("get", kind, name, "-n", "bigdata", "-o", "json"))


def require(condition, message):
    if not condition:
        raise RuntimeError(message + "; stop here and report this prerequisite failure")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--airflow", action="store_true")
    args = parser.parse_args()
    require(shutil.which("oc"), "oc is not on PATH")
    require(shutil.which("flock"), "flock is unavailable")
    print("LOGIN", oc("whoami"))
    for name in ("spark-master-0", "spark-worker-0", "spark-worker-1", "mysql-0", "trino-0", "seaweedfs-0"):
        pod = resource("pod", name)
        statuses = pod["status"].get("containerStatuses", [])
        require(bool(statuses) and all(c["ready"] for c in statuses), "Pod not Ready: " + name)
        print("POD_READY", name)
    for name in ("spark-master", "mysql", "trino", "seaweedfs", "polaris"):
        slices = json.loads(oc("get", "endpointslices.discovery.k8s.io", "-n", "bigdata", "-l",
                               "kubernetes.io/service-name=" + name, "-o", "json"))
        require(any(e.get("conditions", {}).get("ready") for s in slices["items"] for e in s.get("endpoints", [])),
                "Service has no ready endpoint: " + name)
    require(resource("pvc", "spark-notebooks")["status"]["phase"] == "Bound", "Notebook PVC not Bound")
    resource("serviceaccount", "bigdata-workloads")
    keys = set(oc("get", "secret", "lab-credentials", "-n", "bigdata", "-o",
                  'go-template={{range $k,$v := .data}}{{$k}}{{"\\n"}}{{end}}').splitlines())
    required = {"s3-access-key", "s3-secret-key", "polaris-client-id", "polaris-client-secret", "database-user", "database-password"}
    require(required <= keys, "Required credential references are missing")
    for verb, kind in (("create", "jobs.batch"), ("get", "jobs.batch"), ("get", "pods/log"), ("create", "pods/exec")):
        require(oc("auth", "can-i", verb, kind, "-n", "bigdata") == "yes", "Missing permission: " + verb + " " + kind)
    manifest = json.loads(Path(__file__).with_name("spark-job-template.json").read_text())
    expected_image = manifest["spec"]["template"]["spec"]["containers"][0]["image"]
    actual_image = oc("get", "istag", "dataeng-spark:3.5.9-5", "-n", "bigdata", "-o", "jsonpath={.image.dockerImageReference}")
    require(actual_image == expected_image, "Classroom Spark image differs from the supplied manifest")
    code = "import urllib.request,json; d=json.load(urllib.request.urlopen('http://spark-master:8080/json/',timeout=10)); assert not d.get('activeapps'), 'Other Spark applications are active'; assert any(w.get('state')=='ALIVE' and w.get('coresfree',0)>=1 and w.get('memoryfree',0)>=512 for w in d.get('workers',[])), 'No free Spark capacity'; print('SPARK_CAPACITY_PASS')"
    print(oc("exec", "-n", "bigdata", "spark-master-0", "-c", "jupyter", "--", "python3", "-c", code))
    if args.airflow:
        print("Checking Airflow health (allowing up to one minute for fresh heartbeats)...", flush=True)
        code = '''import urllib.request,json,time
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8080/api/v2/monitor/health',timeout=4) as response:
            h=json.load(response)
        if all(h.get(k,{}).get('status')=='healthy' for k in ('metadatabase','scheduler','dag_processor','triggerer')):
            print('AIRFLOW_HEALTH_PASS')
            break
    except OSError:
        pass
    time.sleep(5)
else:
    raise RuntimeError('Airflow stayed unhealthy for one minute; stop before continuing')
'''
        print(oc("exec", "-n", "bigdata", "airflow-0", "-c", "airflow", "--", "python", "-c", code))
        for verb in ("create", "get"):
            require(oc("auth", "can-i", verb, "jobs.batch", "-n", "bigdata", "--as=system:serviceaccount:bigdata:airflow-runner") == "yes", "Airflow Job permission missing")
    print("PREFLIGHT_PASS")


if __name__ == "__main__":
    main()

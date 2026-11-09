"""Offline verification: python3 -B -m unittest discover -s tests -v."""
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dags"))
from course_airflow_ecomm import spark_job, trino_http


def response(payload, status=200):
    result = Mock(status_code=status)
    result.json.return_value = payload
    return result


def template():
    return {"metadata": {"name": "old"}, "spec": {"template": {"spec": {
        "serviceAccountName": "existing-runner",
        "containers": [{"name": "driver", "image": "existing-image",
                        "env": [{"name": "POLARIS_CLIENT_SECRET", "valueFrom": {
                            "secretKeyRef": {"name": "existing-secret", "key": "client-secret"}}}],
                        "volumeMounts": [{"name": "notebooks", "mountPath": "/workspace"}]}],
        "volumes": [{"name": "notebooks", "persistentVolumeClaim": {"claimName": "spark-notebooks"}}],
    }}}}


class ClientTests(unittest.TestCase):
    def test_pagination(self):
        session = Mock()
        session.post.return_value = response({"nextUri": "http://trino/page1"})
        session.get.side_effect = [response({"data": [[1]], "nextUri": "http://trino/page2"}), response({"data": [[2]]})]
        self.assertEqual(trino_http.query("SELECT 1", session=session), [[1], [2]])
        session.post.assert_called_once()
        self.assertEqual(session.get.call_count, 2)

    def test_sql_error_is_not_http_success(self):
        session = Mock()
        session.post.return_value = response({"error": {"message": "PRIVATE_DETAIL"}})
        with self.assertRaises(RuntimeError) as error:
            trino_http.query("SELECT 1", session=session)
        self.assertNotIn("PRIVATE_DETAIL", str(error.exception))

    def test_timeout_cancels_query(self):
        session = Mock()
        session.post.return_value = response({"nextUri": "http://trino/page"})
        with patch.object(trino_http.time, "monotonic", side_effect=[0, 2]):
            with self.assertRaises(TimeoutError):
                trino_http.query("SELECT 1", timeout_seconds=1, session=session)
        session.delete.assert_called_once_with("http://trino/page", timeout=5)

    def test_page_error_cancels_query(self):
        session = Mock()
        session.post.return_value = response({"nextUri": "http://trino/page"})
        session.get.return_value = response({}, 503)
        with self.assertRaises(RuntimeError):
            trino_http.query("SELECT 1", session=session)
        session.delete.assert_called_once()


class JobTests(unittest.TestCase):
    def test_limits_and_existing_identity(self):
        original = template()
        before = json.dumps(original, sort_keys=True)
        job = spark_job.build_job(original, "dag|run|task", "polaris.source.table", "daily_sales")
        self.assertEqual(before, json.dumps(original, sort_keys=True))
        spec, pod = job["spec"], job["spec"]["template"]["spec"]
        driver = pod["containers"][0]
        self.assertEqual((spec["backoffLimit"], spec["activeDeadlineSeconds"], spec["ttlSecondsAfterFinished"]), (0, 600, 3600))
        self.assertEqual(pod["serviceAccountName"], "existing-runner")
        self.assertEqual(driver["image"], "existing-image")
        self.assertEqual(driver["env"][0], original["spec"]["template"]["spec"]["containers"][0]["env"][0])
        self.assertEqual(driver["resources"]["limits"], {"cpu": "1", "memory": "1536Mi"})
        self.assertEqual(job["metadata"]["name"], spark_job.job_name("dag|run|task"))
        self.assertNotEqual(spark_job.job_name("another-run"), job["metadata"]["name"])

    def check_run(self, replies):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "template.json"
            file.write_text(json.dumps(template()))
            with patch.object(spark_job, "JOB_TEMPLATE", str(file)), patch.object(spark_job, "kube") as kube:
                kube.side_effect = replies
                return spark_job.run_spark("identity", "polaris.source.table", "daily_sales")

    def test_existing_job_reattachment(self):
        labels = {"app": "airflow-ecommerce-course", "suffix": spark_job.RUN_SUFFIX}
        result = self.check_run([{"course_conflict": True}, {"metadata": {"labels": labels}}, {"status": {"succeeded": 1}}])
        self.assertEqual(result["job"], spark_job.job_name("identity"))

    def test_failed_job_fails_task(self):
        with self.assertRaisesRegex(RuntimeError, "Spark Job failed"):
            self.check_run([{}, {"status": {"conditions": [{"type": "Failed", "status": "True"}]}}])


class DefinitionTests(unittest.TestCase):
    def test_graphs_without_task_execution(self):
        records, active = [], []

        class Node:
            def __init__(self, name):
                self.name = name

            def __rshift__(self, other):
                active[-1]["edges"].add((self.name, other.name))
                return other

        def task(function=None, **options):
            def decorate(fn):
                def build(*args, **kwargs):
                    node = Node(fn.__name__)
                    for arg in (*args, *kwargs.values()):
                        if isinstance(arg, Node):
                            arg >> node
                    return node
                return build
            return decorate(function) if function else decorate

        def dag(**options):
            def decorate(fn):
                def build():
                    record = {"options": options, "edges": set()}
                    records.append(record)
                    active.append(record)
                    try:
                        fn()
                    finally:
                        active.pop()
                    return record
                return build
            return decorate

        sdk = types.ModuleType("airflow.sdk")
        sdk.dag, sdk.task = dag, task
        sdk.get_current_context = Mock(side_effect=AssertionError("Task ran during parsing"))
        airflow = types.ModuleType("airflow")
        airflow.sdk = sdk
        with patch.dict(sys.modules, {"airflow": airflow, "airflow.sdk": sdk}):
            runpy.run_path(str(ROOT / "dags/airflow_hello_trino.py"))
            runpy.run_path(str(ROOT / "dags/airflow_ecomm_dags.py"))
        expected = [
            {("begin", "query_trino"), ("query_trino", "finish")},
            {("validate_sources", "compare_gold")},
            {("prepare", "run_spark_report"), ("run_spark_report", "verify_with_trino")},
            {("validate_mysql", "mysql_to_iceberg"), ("mysql_to_iceberg", "spark_gold"), ("spark_gold", "reconcile")},
        ]
        self.assertEqual(len(records), 4)
        for record, edges in zip(records, expected):
            self.assertEqual(record["edges"], edges)
            opts = record["options"]
            self.assertIsNone(opts["schedule"])
            self.assertFalse(opts["catchup"])
            self.assertTrue(opts["is_paused_upon_creation"])
            self.assertEqual((opts["max_active_runs"], opts["max_active_tasks"]), (1, 1))
            self.assertEqual(opts["default_args"]["retries"], 0)

    def test_heredocs_match_supplied_files(self):
        text = (ROOT / "00-airflow-introduction.md").read_text(encoding="utf-8")
        for relative, delimiter in (("dags/sql/hello_trino.sql", "SQL"), ("dags/airflow_hello_trino.py", "PY")):
            match = re.search(r"cat > " + re.escape(relative) + r" <<'" + delimiter + r"'\n(.*?)\n" + delimiter, text, re.S)
            self.assertIsNotNone(match, relative)
            self.assertEqual(match.group(1).strip(), (ROOT / relative).read_text(encoding="utf-8").strip())

    def test_links_and_diagrams(self):
        for file in ROOT.glob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
                if not re.match(r"[a-z]+://|#", target):
                    resolved = (file.parent / target.split("#")[0]).resolve()
                    # Other course guides are contextual links, not required publication files.
                    if ROOT.resolve() in resolved.parents or resolved == ROOT.resolve():
                        self.assertTrue(resolved.exists(), (file.name, target))
        for file in (ROOT / "assets").glob("*.svg"):
            ET.parse(file)


class PublicationTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "Bash publication simulation runs on Linux")
    def test_copy_order_rerun_and_missing_source(self):
        with tempfile.TemporaryDirectory(prefix="course publication ") as folder:
            base = Path(folder)
            course = base / "exercise"
            shutil.copytree(ROOT, course, ignore=shutil.ignore_patterns("__pycache__"))
            tools = base / "tools"
            tools.mkdir()
            recorder = tools / "oc"
            recorder.write_text('#!/usr/bin/env python3\nimport os,sys,json\nwith open(os.environ["OC_RECORD"],"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n')
            recorder.chmod(0o755)
            log = base / "calls.jsonl"
            env = {**os.environ, "HOME": str(base / "home"), "PATH": str(tools) + os.pathsep + os.environ["PATH"], "OC_RECORD": str(log)}
            command = ["bash", str(course / "publish-course.sh")]
            subprocess.run(["bash", "-n", command[1]], check=True)
            for _ in range(2):
                subprocess.run(command, cwd=base, env=env, check=True, capture_output=True)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            copies = [call for call in calls if call[0] == "cp"]
            self.assertEqual(len(copies), 20)
            self.assertEqual(copies[:10], copies[10:])
            self.assertTrue(copies[8][1].endswith("airflow_hello_trino.py"))
            self.assertTrue(copies[9][1].endswith("airflow_ecomm_dags.py"))
            for call in copies[:6]:
                self.assertEqual(Path(call[1]).name, call[2].rsplit("/", 1)[-1])
            self.assertFalse(any(call[0] in {"apply", "create", "delete", "patch", "scale", "rollout"} or "trigger" in call for call in calls))
            previous = log.read_text()
            for relative in ("dags/sql/hello_trino.sql", "dags/course_airflow_ecomm/tasks.py"):
                source = course / relative
                contents = source.read_bytes()
                source.unlink()
                result = subprocess.run(command, cwd=base, env=env, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(previous, log.read_text())
                source.write_bytes(contents)


if __name__ == "__main__":
    unittest.main()

"""One manual DAG that builds and checks an isolated ecommerce pipeline."""
from datetime import timedelta
from pathlib import Path
import re

from airflow.sdk import dag, get_current_context, task

from . import sql, tasks
from .settings import NAMESPACE
from .spark_job import job_name, run_job, run_spark
from .trino_http import query


def task_attempt():
    context = get_current_context()
    ti = context["ti"]
    return f"{ti.dag_id}|{ti.run_id}|{ti.task_id}|{ti.try_number}"


def mysql_seed_job(database, image, root_secret):
    seed = Path(__file__).with_name("mysql_seed.sql").read_text(encoding="utf-8")
    name = job_name(task_attempt(), database)
    return {
        "apiVersion": "batch/v1", "kind": "Job",
        "metadata": {
            "name": name,
            "labels": {"app": "airflow-ecommerce-mysql", "deployment": database},
        },
        "spec": {
            "backoffLimit": 0, "activeDeadlineSeconds": 120,
            "ttlSecondsAfterFinished": 3600,
            "template": {"spec": {
                "restartPolicy": "Never",
                "automountServiceAccountToken": False,
                "containers": [{
                    "name": "mysql-client", "image": image,
                    "command": ["mysql"],
                    "args": ["--host=mysql", "--user=root", "--connect-timeout=10",
                             "--execute", seed.format(database=database)],
                    "env": [{"name": "MYSQL_PWD", "valueFrom": {"secretKeyRef": root_secret}}],
                }],
            }},
        },
    }


def build_dag(deployment_id, mysql_image, root_secret, *, dag_id=None):
    if not re.fullmatch(r"airflow_[0-9]{8}_[0-9]{4}", deployment_id):
        raise ValueError("Use a deployment ID such as airflow_20261118_1435")
    lake = f"iceberg_polaris.{deployment_id}"
    storage = f"s3://warehouse/iceberg/{deployment_id}"
    source = sql.source_lines(f"mysql.{deployment_id}.")

    @dag(dag_id=dag_id or deployment_id, description=f"Course data RUN_ID={deployment_id}",
         schedule=None, catchup=False, max_active_runs=1,
         is_paused_upon_creation=True, tags=["course", "ecommerce"],
         default_args={"execution_timeout": timedelta(minutes=4)})
    def ecommerce():
        @task
        def seed_mysql():
            job = run_job(mysql_seed_job(deployment_id, mysql_image, root_secret))
            print(f"MYSQL_READY mysql.{deployment_id} (Job {job} in {NAMESPACE})")

        @task
        def validate_mysql():
            totals = query("SELECT count(*), count(DISTINCT order_id), "
                           f"CAST(sum(line_amount) AS VARCHAR) FROM ({source}) sales")
            tasks.require_totals(totals, source=f"mysql.{deployment_id}")
            print(f"MYSQL_VALIDATED {totals[0]}")

        @task
        def load_iceberg():
            query(f"CREATE SCHEMA IF NOT EXISTS {lake} WITH (location = '{storage}')")
            query(f"CREATE TABLE IF NOT EXISTS {lake}.sales_input "
                  f"WITH (format = 'PARQUET', format_version = 2, "
                  f"location = '{storage}/sales_input') AS {source}")
            print(f"ICEBERG_READY {lake}.sales_input")

        @task(execution_timeout=timedelta(minutes=13))
        def aggregate_with_spark():
            result = run_spark(task_attempt(), f"polaris.{deployment_id}.sales_input",
                               "daily_sales", schema=deployment_id)
            print(f"SPARK_READY {lake}.daily_sales (Job {result['job']})")

        @task
        def validate_report():
            result = tasks.verify_report(f"({source}) sales", f"{lake}.daily_sales")
            if result["groups"] != 4:
                raise ValueError(f"Expected four day/country groups, got {result['groups']}")
            print(f"ECOMMERCE_READY {lake}.daily_sales")
            return result

        seed_mysql() >> validate_mysql() >> load_iceberg() >> aggregate_with_spark() >> validate_report()

    return ecommerce()

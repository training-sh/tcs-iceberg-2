"""Three paused, manual Airflow 3 DAGs. Manual execution only."""
from datetime import timedelta
from airflow.sdk import dag, task, get_current_context
from course_airflow_ecomm import tasks, sql
from course_airflow_ecomm.settings import LAKE_SCHEMA, RUN_SUFFIX, TRINO_LESSON_SCHEMA
from course_airflow_ecomm.spark_job import run_spark

OPTIONS = dict(
    schedule=None, catchup=False, max_active_runs=1, max_active_tasks=1,
    is_paused_upon_creation=True,
    default_args={"retries": 0, "execution_timeout": timedelta(minutes=4)},
    tags=["course", "ecommerce", RUN_SUFFIX],
)


@dag(dag_id=f"course_{RUN_SUFFIX}_01_trino_checks", **OPTIONS)
def trino_checks():
    @task(do_xcom_push=False)
    def validate_sources():
        tasks.preflight()

    @task
    def compare_gold():
        return tasks.verify_report(
            f"{TRINO_LESSON_SCHEMA}.silver_order_lines",
            f"{TRINO_LESSON_SCHEMA}.gold_daily_sales",
        )

    validate_sources() >> compare_gold()


@dag(dag_id=f"course_{RUN_SUFFIX}_02_spark_report", **OPTIONS)
def spark_report():
    @task(do_xcom_push=False)
    def prepare():
        tasks.preflight()
        tasks.prepare_schema()

    @task(execution_timeout=timedelta(minutes=13))
    def run_spark_report():
        context = get_current_context()
        identity = f"{context['dag'].dag_id}|{context['run_id']}|run_spark_report"
        return run_spark(identity,
                         f"polaris.trino_ecomm_{RUN_SUFFIX}.silver_order_lines",
                         "spark_daily_preview")

    @task
    def verify_with_trino(job):
        result = tasks.verify_report(f"{TRINO_LESSON_SCHEMA}.silver_order_lines",
                                     f"{LAKE_SCHEMA}.spark_daily_preview")
        return {**result, "job": job["job"]}

    started = run_spark_report()
    prepare() >> started
    verify_with_trino(started)


@dag(dag_id=f"course_{RUN_SUFFIX}_03_end_to_end", **OPTIONS)
def end_to_end():
    @task(do_xcom_push=False)
    def validate_mysql():
        tasks.preflight(include_lesson=False)

    @task(do_xcom_push=False)
    def mysql_to_iceberg():
        tasks.prepare_input()

    @task(execution_timeout=timedelta(minutes=13))
    def spark_gold():
        context = get_current_context()
        identity = f"{context['dag'].dag_id}|{context['run_id']}|spark_gold"
        return run_spark(identity, f"polaris.airflow_ecomm_{RUN_SUFFIX}.sales_input", "daily_sales")

    @task
    def reconcile(job):
        # Compare with live MySQL, not just the staged table Spark has already read.
        result = tasks.verify_report(f"({sql.source_lines()}) mysql_source", f"{LAKE_SCHEMA}.daily_sales")
        return {**result, "job": job["job"]}

    loaded = mysql_to_iceberg()
    validate_mysql() >> loaded
    gold = spark_gold()
    loaded >> gold
    reconcile(gold)


trino_checks_dag = trino_checks()
spark_report_dag = spark_report()
end_to_end_dag = end_to_end()

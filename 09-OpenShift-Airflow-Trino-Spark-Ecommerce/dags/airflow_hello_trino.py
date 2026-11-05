"""Small first DAG: read one SQL file, call Trino and check the result."""
from datetime import timedelta
from pathlib import Path
from airflow.sdk import dag, task


@dag(
    dag_id="course_00_hello_trino",
    schedule=None,
    catchup=False,
    is_paused_upon_creation=True,
    max_active_runs=1,
    max_active_tasks=1,
    default_args={"retries": 0, "execution_timeout": timedelta(minutes=4)},
    tags=["course", "introduction"],
)
def hello_trino():
    @task(do_xcom_push=False)
    def begin():
        print("HELLO_BEGIN: starting the Trino check")

    @task
    def query_trino():
        from course_airflow_ecomm.trino_http import query
        statement = (Path(__file__).resolve().parent / "sql" / "hello_trino.sql").read_text().strip().removesuffix(";")
        rows = query(statement)
        if rows != [[25]]:
            raise ValueError("Expected 25 nations from the existing TPCH tiny catalog")
        print("HELLO_TRINO_QUERY_PASS: nations=25")
        return {"nations": 25}

    @task(do_xcom_push=False)
    def finish(result):
        if result["nations"] != 25:
            raise ValueError("Unexpected Trino summary")
        print("HELLO_FINISH: all checks passed")

    result = query_trino()
    begin() >> result
    finish(result)


hello_trino_dag = hello_trino()

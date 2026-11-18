"""Edit before installation; no credentials belong here."""
import re

RUN_SUFFIX = "s01"
EXPECTED_LINES = 8
EXPECTED_ORDERS = 5
EXPECTED_REVENUE = "225.00"
if not re.fullmatch(r"s[0-9]{2,3}", RUN_SUFFIX):
    raise ValueError("Use a run suffix such as s01 or s025")
NAMESPACE = "bigdata"
TRINO_URL = "http://trino:8080"
TRINO_USER = "team"
MYSQL_PREFIX = f"mysql.trino_ecomm.trino_{RUN_SUFFIX}_"
TRINO_LESSON_SCHEMA = f"iceberg_polaris.trino_ecomm_{RUN_SUFFIX}"
SCHEMA_NAME = f"airflow_ecomm_{RUN_SUFFIX}"
LAKE_SCHEMA = f"iceberg_polaris.{SCHEMA_NAME}"
STORAGE_ROOT = f"s3://warehouse/iceberg/{SCHEMA_NAME}"
SPARK_SCRIPT = "/workspace/user_notebooks/09-airflow-ecommerce/spark_ecomm.py"
JOB_TEMPLATE = "/opt/course/job-template.json"

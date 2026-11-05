"""One-core batch aggregation executed inside the existing Spark-image Job."""
import argparse
import os
import re


def aggregate_sql(source):
    return f"""
SELECT order_date, country, count(DISTINCT order_id) AS completed_orders,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM {source} GROUP BY order_date, country
"""


def merge_sql(target):
    return f"""
MERGE INTO {target} t USING ecomm_course_daily s
ON t.order_date = s.order_date AND t.country = s.country
WHEN MATCHED AND (NOT (t.completed_orders <=> s.completed_orders)
                  OR NOT (t.revenue <=> s.revenue))
THEN UPDATE SET completed_orders = s.completed_orders, revenue = s.revenue
WHEN NOT MATCHED THEN INSERT (order_date, country, completed_orders, revenue)
VALUES (s.order_date, s.country, s.completed_orders, s.revenue)
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("--input-table", required=True)
    parser.add_argument("--output-table", choices=["spark_daily_preview", "daily_sales"], required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"airflow_ecomm_s[0-9]{2,3}", args.schema):
        raise ValueError("Invalid course schema")
    suffix = args.schema.removeprefix("airflow_ecomm_")
    allowed = {f"polaris.trino_ecomm_{suffix}.silver_order_lines",
               f"polaris.{args.schema}.sales_input"}
    if args.input_table not in allowed:
        raise ValueError("Input must be one of the assigned course tables")

    from pyspark.sql import SparkSession
    builder = (SparkSession.builder.appName("airflow-ecomm-" + suffix)
        .config("spark.cores.max", "1")
        .config("spark.executor.cores", "1")
        .config("spark.executor.memory", "512m")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.polaris", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.polaris.type", "rest")
        .config("spark.sql.catalog.polaris.uri", "http://polaris:8181/api/catalog")
        .config("spark.sql.catalog.polaris.warehouse", "training")
        .config("spark.sql.catalog.polaris.rest.auth.type", "oauth2")
        .config("spark.sql.catalog.polaris.scope", "PRINCIPAL_ROLE:ALL")
        .config("spark.sql.catalog.polaris.oauth2-server-uri", "http://polaris:8181/api/catalog/v1/oauth/tokens")
        .config("spark.sql.catalog.polaris.header.Polaris-Realm", "POLARIS")
        .config("spark.sql.catalog.polaris.rest-metrics-reporting-enabled", "false")
        .config("spark.sql.catalog.polaris.credential", os.environ["POLARIS_CLIENT_ID"] + ":" + os.environ["POLARIS_CLIENT_SECRET"])
        .config("spark.sql.catalog.polaris.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.polaris.s3.endpoint", "http://seaweedfs:8333")
        .config("spark.sql.catalog.polaris.s3.path-style-access", "true")
        .config("spark.sql.catalog.polaris.s3.access-key-id", os.environ["AWS_ACCESS_KEY_ID"])
        .config("spark.sql.catalog.polaris.s3.secret-access-key", os.environ["AWS_SECRET_ACCESS_KEY"])
        .config("spark.sql.catalog.polaris.client.region", "us-east-1")
        .config("spark.redaction.regex", "(?i)secret|password|token|access.?key|credential"))
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        if spark.sql(f"SELECT line_id FROM {args.input_table} GROUP BY line_id "
                     "HAVING count(*) > 1 OR line_id IS NULL").take(1):
            raise ValueError("Invalid input line keys")
        target = f"polaris.{args.schema}.{args.output_table}"
        location = f"s3://warehouse/iceberg/{args.schema}/{args.output_table}"
        spark.sql(f"""CREATE TABLE IF NOT EXISTS {target} (
            order_date DATE, country STRING, completed_orders BIGINT, revenue DECIMAL(18,2)
        ) USING iceberg LOCATION '{location}' TBLPROPERTIES ('format-version'='2')""")
        spark.sql(aggregate_sql(args.input_table)).createOrReplaceTempView("ecomm_course_daily")
        spark.sql(merge_sql(target))
        summary = spark.sql(f"SELECT count(*) groups, CAST(sum(revenue) AS STRING) revenue FROM {target}").first()
        print("SPARK_ECOMM_PASS", {"groups": summary["groups"], "revenue": summary["revenue"]})
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

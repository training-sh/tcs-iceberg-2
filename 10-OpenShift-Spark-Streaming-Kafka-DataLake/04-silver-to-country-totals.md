# 04 — Iceberg Silver stream to country totals
Finish notebook 03 and release its Spark session first. Run this notebook in a fresh kernel. It streams append snapshots from the same Polaris Silver table and stores Gold in SeaweedFS. It uses no Kafka Python client and starts only one Spark application.

```python
# Fixed names: keep this cell consistent across all four notebooks.
BOOTSTRAP = "kafka:9092"
TOPIC = "invoices-lake"
CONSUMER_GROUP = "invoice-observer"
DATALAKE = "polaris.invoice_lake"
LOCATION_ROOT = "s3://warehouse/iceberg/invoice_lake"
INGEST_CHECKPOINT = "s3a://warehouse/invoice-lake/checkpoints/kafka_to_lake"
GOLD_CHECKPOINT = "s3a://warehouse/invoice-lake/checkpoints/silver_to_country"
BRONZE = DATALAKE + ".bronze"
SILVER = DATALAKE + ".silver"
REJECTS = DATALAKE + ".rejects"
GOLD = DATALAKE + ".country_totals"
```

```python
print({"topic": TOPIC, "datalake": DATALAKE})
```

## Define Spark setup and country totals
All functions required by this notebook are defined here.

```python
import os

import socket

REQUIRED_ENV = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "POLARIS_CLIENT_ID", "POLARIS_CLIENT_SECRET"]

def preflight():
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing existing credential environment names: " + ", ".join(missing))
    import importlib.util
    from pathlib import Path
    if importlib.util.find_spec("pyspark") is None:
        raise RuntimeError("Choose the existing Spark-enabled Python kernel; do not pip install PySpark")
    jars = Path(os.environ.get("SPARK_HOME", "/opt/spark")) / "jars"
    patterns = ["spark-sql-kafka-0-10_*.jar", "spark-token-provider-kafka-0-10_*.jar",
                "kafka-clients-*.jar", "iceberg-spark-runtime-*.jar", "iceberg-aws-bundle-*.jar",
                "hadoop-aws-*.jar", "aws-java-sdk-bundle-*.jar", "commons-pool2-*.jar"]
    absent = [pattern for pattern in patterns if not list(jars.glob(pattern))]
    if absent:
        raise RuntimeError("Missing image JARs; stop without rebuilding/installing: " + ", ".join(absent))
    print("PREFLIGHT_PASS: required environment names, PySpark and image JARs present")

def start_spark(app_name):
    preflight()
    from pyspark.sql import SparkSession
    if SparkSession.getActiveSession() is not None:
        raise RuntimeError("Stop the existing Spark session and restart this kernel before setup")
    builder = (SparkSession.builder.appName(app_name).master("spark://spark-master:7077")
        .config("spark.driver.host", os.environ.get("POD_IP") or socket.gethostbyname(socket.gethostname()))
        .config("spark.driver.bindAddress", "0.0.0.0")
        .config("spark.cores.max", "1").config("spark.executor.cores", "1")
        .config("spark.executor.memory", "512m").config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.polaris", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.polaris.type", "rest")
        .config("spark.sql.catalog.polaris.uri", os.environ.get("POLARIS_URI", "http://polaris:8181/api/catalog"))
        .config("spark.sql.catalog.polaris.warehouse", "training")
        .config("spark.sql.catalog.polaris.rest.auth.type", "oauth2")
        .config("spark.sql.catalog.polaris.scope", "PRINCIPAL_ROLE:ALL")
        .config("spark.sql.catalog.polaris.oauth2-server-uri", os.environ.get("POLARIS_URI", "http://polaris:8181/api/catalog").rstrip("/") + "/v1/oauth/tokens")
        .config("spark.sql.catalog.polaris.header.Polaris-Realm", "POLARIS")
        .config("spark.sql.catalog.polaris.rest-metrics-reporting-enabled", "false")
        .config("spark.sql.catalog.polaris.credential", os.environ["POLARIS_CLIENT_ID"] + ":" + os.environ["POLARIS_CLIENT_SECRET"])
        .config("spark.sql.catalog.polaris.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.polaris.s3.endpoint", os.environ.get("S3_ENDPOINT", "http://seaweedfs:8333"))
        .config("spark.sql.catalog.polaris.s3.path-style-access", "true")
        .config("spark.sql.catalog.polaris.s3.access-key-id", os.environ["AWS_ACCESS_KEY_ID"])
        .config("spark.sql.catalog.polaris.s3.secret-access-key", os.environ["AWS_SECRET_ACCESS_KEY"])
        .config("spark.sql.catalog.polaris.client.region", "us-east-1")
        .config("spark.hadoop.fs.s3a.endpoint", os.environ.get("S3_ENDPOINT", "http://seaweedfs:8333"))
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .config("spark.hadoop.fs.s3a.access.key", os.environ["AWS_ACCESS_KEY_ID"])
        .config("spark.hadoop.fs.s3a.secret.key", os.environ["AWS_SECRET_ACCESS_KEY"])
        .config("spark.redaction.regex", "(?i)secret|password|token|access.?key|credential"))
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    print("SPARK_STARTED", spark.version, spark.sparkContext.applicationId)
    return spark
```

```python
BRONZE_COLUMNS = """TransportID STRING, SourceTopic STRING, SourcePartition INT,
SourceOffset BIGINT, KafkaTimestamp TIMESTAMP, RawKey STRING, RawValue STRING"""

SILVER_COLUMNS = """LineID STRING, InvoiceNo STRING, StockCode STRING, Description STRING,
Quantity INT, InvoiceDate TIMESTAMP, UnitPrice DECIMAL(18,2), CustomerID STRING,
Country STRING, Amount DECIMAL(28,2), PayloadHash STRING,
SourceTopic STRING, SourcePartition INT, SourceOffset BIGINT"""

def gold_merge_sql(target=GOLD):
    return f"""MERGE INTO {target} t USING current_country_totals s ON t.Country = s.Country
    WHEN MATCHED AND (t.TotalOrders <> s.TotalOrders OR t.TotalAmount <> s.TotalAmount)
      THEN UPDATE SET TotalOrders = s.TotalOrders, TotalAmount = s.TotalAmount
    WHEN NOT MATCHED THEN INSERT *"""

def create_gold(spark, gold=GOLD, location_root=LOCATION_ROOT):
    spark.sql(f"""CREATE TABLE IF NOT EXISTS {gold} (
        Country STRING, TotalOrders BIGINT, TotalAmount DECIMAL(38,2)
    ) USING iceberg LOCATION '{location_root}/country_totals'
    TBLPROPERTIES ('format-version'='2')""")

def merge_country_totals(batch, batch_id, silver=SILVER, gold=GOLD):
    from pyspark.sql import functions as F
    if batch.isEmpty():
        return
    spark = batch.sparkSession
    spark.catalog.refreshTable(silver)
    totals = (spark.table(silver).groupBy("Country")
              .agg(F.countDistinct("InvoiceNo").alias("TotalOrders"),
                   F.sum("Amount").alias("TotalAmount")))
    totals.createOrReplaceTempView("current_country_totals")
    spark.sql(gold_merge_sql(gold)).collect()
    spark.catalog.refreshTable(gold)
    print("GOLD_BATCH_PASS", {"batch_id": batch_id})

def await_finite(query, seconds=180):
    try:
        if not query.awaitTermination(seconds):
            raise TimeoutError("Finite query exceeded the exercise timeout")
    finally:
        if query.isActive:
            query.stop()
```

```python
spark = start_spark("invoice-country-totals")
create_gold(spark, gold=GOLD, location_root=LOCATION_ROOT)
snapshots = spark.sql(f"SELECT operation FROM {SILVER}.snapshots")
if snapshots.filter("operation <> 'append'").take(1):
    spark.stop()
    raise RuntimeError("Silver has non-append snapshots; do not skip them silently")
```

## Use Silver commits as notifications
Each callback reads the currently committed Silver table and computes lifetime distinct InvoiceNo and decimal Amount per Country. It MERGEs absolute totals, so replay does not add the same amount twice. This scans all Silver for a tiny dataset; it is not an incremental large-scale aggregation. No hourly/event-time window or watermark is used. Gold updates are safe because Gold is read in batch, not streamed here.

```python
silver_changes = spark.readStream.format("iceberg").load(SILVER)
writer = (silver_changes.writeStream.foreachBatch(lambda batch, batch_id: merge_country_totals(batch, batch_id, silver=SILVER, gold=GOLD)).outputMode("append")
          .option("checkpointLocation", GOLD_CHECKPOINT))
query = writer.trigger(once=True).start()
await_finite(query, seconds=180)
spark.catalog.refreshTable(GOLD)  # Refresh metadata committed by the callback session.
spark.table(GOLD).orderBy("Country").show(truncate=False)
```

After batch A: IN / 2 / 110.00, UK / 1 / 30.00, US / 1 / 35.00. After batch B is ingested: IN / 2 / 110.00, UK / 2 / 80.00, US / 1 / 35.00. The total rises from 175.00 to 225.00.

The once trigger finishes one micro-batch for this small Silver stream. It is separate from Kafka's AvailableNow run. Stop this session before returning to notebook 03 to ingest another producer batch, then reopen 04 with its unchanged checkpoint.

```python
START_LIVE = False
if START_LIVE:
    query = writer.trigger(processingTime="30 seconds").start()
else:
    print("Recurring Gold query not requested")
```

```python
DRAIN_LIVE = False  # Only with no ongoing upstream writes.
if DRAIN_LIVE and "query" in globals() and query.isActive:
    query.processAllAvailable()
```

```python
try:
    if "query" in globals() and query.isActive:
        query.stop()
finally:
    if "spark" in globals():
        spark.stop()
print("Spark executor released")
```

Keep Silver append-only and retain snapshots needed by the reader. Do not update/delete Silver, expire snapshots, remove checkpoints, or recreate topics under an existing checkpoint. The Gold MERGE does not delete countries that disappear from input; corrections, refunds and removals require a different contract. Use one writer per table.

# 03 — Kafka to Iceberg Bronze, Silver and rejects
Publish batch A first. Stop other Spark notebooks/applications before starting this one. Use one worker core and one 512 MiB executor; no broker/worker scaling is required. Run the finite path first. Do not use Run All across alternative trigger cells.

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

## Define Spark setup
Use the existing image libraries and credential environment variables. No separate Python source files are needed.

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

## Define tables, validation and the streaming callback
Run these definitions before creating the Spark session and starting the stream.

```python
BRONZE_COLUMNS = """TransportID STRING, SourceTopic STRING, SourcePartition INT,
SourceOffset BIGINT, KafkaTimestamp TIMESTAMP, RawKey STRING, RawValue STRING"""

SILVER_COLUMNS = """LineID STRING, InvoiceNo STRING, StockCode STRING, Description STRING,
Quantity INT, InvoiceDate TIMESTAMP, UnitPrice DECIMAL(18,2), CustomerID STRING,
Country STRING, Amount DECIMAL(28,2), PayloadHash STRING,
SourceTopic STRING, SourcePartition INT, SourceOffset BIGINT"""

def insert_merge_sql(target, view, key):
    return f"""MERGE INTO {target} t USING {view} s ON t.{key} = s.{key}
    WHEN NOT MATCHED THEN INSERT *"""

def payload_conflicts_sql(target=SILVER):
    return f"""SELECT s.LineID FROM incoming_silver s JOIN {target} t
    ON s.LineID = t.LineID WHERE s.PayloadHash <> t.PayloadHash LIMIT 1"""

def create_lake_tables(spark, datalake=DATALAKE, location_root=LOCATION_ROOT):
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {datalake}")
    for table, columns, name in [(f"{datalake}.bronze", BRONZE_COLUMNS, "bronze"),
                                 (f"{datalake}.silver", SILVER_COLUMNS, "silver"),
                                 (f"{datalake}.rejects", BRONZE_COLUMNS + ", Reason STRING", "rejects")]:
        spark.sql(f"""CREATE TABLE IF NOT EXISTS {table} ({columns})
        USING iceberg LOCATION '{location_root}/{name}'
        TBLPROPERTIES ('format-version'='2')""")

def decode_invoices(raw):
    from pyspark.sql import functions as F, types as T
    fields = ["LineID", "InvoiceNo", "StockCode", "Description", "InvoiceDate",
              "UnitPrice", "CustomerID", "Country"]
    schema = T.StructType([T.StructField(name, T.StringType(), True) for name in fields]
                          + [T.StructField("Quantity", T.IntegerType(), True),
                             T.StructField("_corrupt_record", T.StringType(), True)])
    parsed = raw.withColumn("invoice", F.from_json("RawValue", schema, {"mode": "PERMISSIVE"}))
    parsed = (parsed.select("*", "invoice.*")
              .withColumn("BadJSON", F.col("invoice").isNull() | F.col("_corrupt_record").isNotNull())
              .drop("invoice", "_corrupt_record"))
    for name in fields:
        parsed = parsed.withColumn(name, F.trim(F.col(name)))
    parsed = (parsed.withColumn("Description", F.coalesce("Description", F.lit("")))
        .withColumn("UnitPrice", F.expr("try_cast(UnitPrice AS DECIMAL(18,2))"))
        .withColumn("InvoiceDate", F.try_to_timestamp("InvoiceDate", F.lit("yyyy-MM-dd HH:mm:ss"))))
    missing = F.lit(False)
    for name in ["LineID", "InvoiceNo", "StockCode", "CustomerID", "Country"]:
        missing = missing | F.col(name).isNull() | (F.col(name) == "")
    parsed = parsed.withColumn("Reason",
        F.when(F.col("BadJSON"), "invalid_json_or_tombstone")
         .when(missing, "missing_business_field")
         .when(F.col("Quantity").isNull() | (F.col("Quantity") <= 0), "invalid_quantity")
         .when(F.col("UnitPrice").isNull() | (F.col("UnitPrice") < 0), "invalid_price")
         .when(F.col("InvoiceDate").isNull(), "invalid_invoice_date")
         .when(F.upper(F.col("InvoiceNo")).startswith("C"), "cancelled_invoice"))
    rejects = parsed.filter("Reason IS NOT NULL").select(*raw.columns, "Reason")
    business = ["LineID", "InvoiceNo", "StockCode", "Description", "Quantity",
                "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
    valid = (parsed.filter("Reason IS NULL")
        .withColumn("Amount", (F.col("Quantity") * F.col("UnitPrice")).cast("decimal(28,2)")))
    valid = valid.withColumn("PayloadHash", F.sha2(F.to_json(F.struct(*business)), 256))
    valid = valid.select(*business, "Amount", "PayloadHash", "SourceTopic", "SourcePartition", "SourceOffset")
    return valid, rejects

def merge_microbatch(batch, batch_id, bronze=BRONZE, silver=SILVER, rejects_table=REJECTS):
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window
    if batch.isEmpty():
        return
    batch.persist()
    spark = batch.sparkSession
    try:
        # Each transport occurrence is preserved, including replayed business events.
        batch.dropDuplicates(["TransportID"]).createOrReplaceTempView("incoming_bronze")
        spark.sql(insert_merge_sql(bronze, "incoming_bronze", "TransportID")).collect()
        valid, rejects = decode_invoices(batch)
        rejects.createOrReplaceTempView("incoming_rejects")
        spark.sql(insert_merge_sql(rejects_table, "incoming_rejects", "TransportID")).collect()

        if valid.groupBy("LineID").agg(F.countDistinct("PayloadHash").alias("versions")).filter("versions > 1").take(1):
            raise ValueError("Conflicting payloads for one LineID; immutable-line contract violated")
        order = Window.partitionBy("LineID").orderBy("SourceTopic", "SourcePartition", "SourceOffset")
        valid = valid.withColumn("choice", F.row_number().over(order)).filter("choice = 1").drop("choice")
        valid.createOrReplaceTempView("incoming_silver")
        if spark.sql(payload_conflicts_sql(silver)).take(1):
            raise ValueError("Existing LineID has different content; stop and review the source event")
        spark.sql(insert_merge_sql(silver, "incoming_silver", "LineID")).collect()
        print("LAKE_BATCH_PASS", {"batch_id": batch_id})
    finally:
        batch.unpersist()

def await_finite(query, seconds=180):
    try:
        if not query.awaitTermination(seconds):
            raise TimeoutError("Finite query exceeded the exercise timeout")
    finally:
        if query.isActive:
            query.stop()
```

```python
from pyspark.sql import functions as F
spark = start_spark("kafka-invoices-to-iceberg")
create_lake_tables(spark, datalake=DATALAKE, location_root=LOCATION_ROOT)
```

## Read the real Kafka stream
Retain transport metadata. The topic/partition/offset identity differs from the business LineID. `startingOffsets=earliest` affects a new query only; an existing checkpoint wins on resume. `failOnDataLoss=true` surfaces missing retained offsets instead of silently skipping data.

```python
kafka_rows = (spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", BOOTSTRAP)
    .option("subscribe", TOPIC)
    .option("startingOffsets", "earliest")
    .option("failOnDataLoss", "true")
    .option("maxOffsetsPerTrigger", 20)
    .load())
raw = kafka_rows.selectExpr(
    "topic AS SourceTopic", "partition AS SourcePartition", "offset AS SourceOffset",
    "timestamp AS KafkaTimestamp", "CAST(key AS STRING) AS RawKey", "CAST(value AS STRING) AS RawValue")
raw = raw.withColumn("TransportID", F.sha2(F.to_json(F.struct("SourceTopic", "SourcePartition", "SourceOffset")), 256))
writer = (raw.writeStream.foreachBatch(lambda batch, batch_id: merge_microbatch(batch, batch_id, bronze=BRONZE, silver=SILVER, rejects_table=REJECTS)).outputMode("append")
          .option("checkpointLocation", INGEST_CHECKPOINT))
raw.printSchema()
```

The callback defined above MERGEs raw occurrences by TransportID, quarantines invalid payloads, and MERGEs accepted rows by LineID. Identical lines at new offsets do not duplicate Silver. Different valid content for the same LineID fails visibly. It is an immutable-line contract, not correction/CDC handling. Each table write commits independently; retries safely revisit earlier stages using stable keys. A conflict may leave Bronze/reject commits while Silver/checkpoint processing remains incomplete.

## A. Process currently available Kafka input and finish
AvailableNow captures the available input and can use multiple bounded micro-batches. It does not wait for future producer batches. Reuse the same checkpoint for batch B and for resume.

```python
query = writer.trigger(availableNow=True).start()
await_finite(query, seconds=180)
print("FINITE_INGEST_COMPLETE")
```

## Inspect the committed tables
After A only: Bronze 10, Silver 7, rejects 2; accepted amount 175.00 across four invoices. After B too: Bronze 12, Silver 8, rejects 2; accepted amount 225.00 across five invoices. These counts assume one publication of each batch and a fresh topic. Kafka re-publication grows Bronze/rejects; checkpoint-only resume does not.

```python
for table in [BRONZE, SILVER, REJECTS]:
    spark.catalog.refreshTable(table)
    print(table, spark.table(table).count())
spark.sql(f"SELECT count(*) lines, count(DISTINCT InvoiceNo) invoices, sum(Amount) amount FROM {SILVER}").show()
spark.table(REJECTS).select("SourcePartition", "SourceOffset", "Reason").show(truncate=False)
spark.sql(f"SELECT LineID,count(*) copies FROM {SILVER} GROUP BY LineID HAVING count(*) > 1").show()
spark.sql(f"SELECT operation,snapshot_id FROM {SILVER}.snapshots").show(truncate=False)
```

## B. Optional recurring mode, instead of A
Use this only while demonstrating arrivals. It occupies the existing executor. Stop publishing before draining; processAllAvailable can keep waiting while input keeps arriving. Stop the query before opening the country-totals Spark notebook.

```python
START_LIVE = False
if START_LIVE:
    if query.isActive:
        raise RuntimeError("A query is already active")
    query = writer.trigger(processingTime="30 seconds").start()
else:
    print("Recurring query not requested")
```

```python
DRAIN_LIVE = False  # Only after the producer has stopped.
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
print("Spark executor released; use a fresh kernel for the next Spark notebook")
```

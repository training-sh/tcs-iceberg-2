# Hive external tables and Spark SQL

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Run UI forwarding commands in separate VM terminals and keep them running while using their URLs.

Run commands one at a time and check each result before continuing. Enter heredocs and commands continued with `\` as complete units. If a command fails, resolve the error before running the next command.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Run the commands in the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a Bash terminal in the Linux VM after completing [Bash configuration](../00-bashrc.md). Run this once per terminal to load the cluster credentials and select `bigdata`. Continue only when it succeeds. If the cluster is stopped, run `okd-start`. If `okd-env` is not found, run `source ~/.bashrc` and retry.

```bash
okd-env
```

## 1. Start HDFS, Hive Metastore, HiveServer2 and Spark

HiveServer2 is disabled in the normal low-memory profile. Start it only for this lesson.

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale statefulset/namenode statefulset/datanode statefulset/spark-master statefulset/spark-worker --replicas=1
```

Wait for `statefulset/namenode` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/namenode --timeout=300s
```

Wait for `statefulset/datanode` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/datanode --timeout=300s
```

Wait for `statefulset/spark-master` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
```

Wait for `statefulset/spark-worker` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

Set these workloads to one replica. This starts stopped workloads or keeps an existing single replica running.

```bash
oc -n bigdata scale deployment/hive-metastore deployment/hiveserver2 --replicas=1
```

Wait for `deployment/hive-metastore` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/hive-metastore --timeout=300s
```

Wait for `deployment/hiveserver2` to become ready. Continue only after rollout succeeds.

```bash
oc -n bigdata rollout status deployment/hiveserver2 --timeout=300s
```

List the matching pods and check their `READY` and `STATUS` columns.

```bash
oc -n bigdata get pods -l 'app in (hive-metastore,hiveserver2)'
```

## 2. Place order data in HDFS

Create the sample orders CSV inside the NameNode container. Paste the complete command, including the closing `DATA` line and quote.

```bash
oc -n bigdata exec namenode-0 -- sh -c "cat > /tmp/orders.csv <<'DATA'
1,2026-01-01,alice,120.50
2,2026-01-01,bob,75.00
3,2026-01-02,alice,40.00
4,2026-01-02,carol,210.25
5,2026-01-03,bob,25.00
DATA"
```

Create the HDFS input directory. `-p` also creates missing parent directories.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/orders/input
```

Upload the container file into HDFS. `-f` replaces only the named sample input file.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/orders.csv /training/orders/input/orders.csv
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/orders/input/orders.csv
```

## 3. Create an external Hive table with Beeline

This lesson creates an external table over the HDFS source directory. The DROP example is disabled. `IF NOT EXISTS` preserves an existing table definition; inspect its schema and location before reusing it.

Write the SQL script inside the HiveServer2 container. Paste the complete command, including the closing `SQL` line and quote.

```bash
oc -n bigdata exec deployment/hiveserver2 -- bash -c "cat > /tmp/orders.sql <<'SQL'
CREATE DATABASE IF NOT EXISTS orderdb;
-- DO NOT DELETE: keep the DROP command commented out.
-- DROP TABLE IF EXISTS orderdb.orders;
CREATE EXTERNAL TABLE IF NOT EXISTS orderdb.orders (
  order_id INT,
  order_date DATE,
  customer STRING,
  amount DECIMAL(12,2)
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 'hdfs://namenode:9000/training/orders/input';
SELECT * FROM orderdb.orders ORDER BY order_id;
SELECT customer, COUNT(*) AS order_count, SUM(amount) AS total_amount
FROM orderdb.orders GROUP BY customer ORDER BY customer;
SQL"
```

Run the SQL through Beeline against HiveServer2 and inspect the returned table or metadata.

```bash
oc -n bigdata exec deployment/hiveserver2 -- beeline -u jdbc:hive2://hiveserver2:10000 -n team --silent=true --showHeader=true --outputformat=table -f /tmp/orders.sql
```

## 4. Read Hive and create an aggregate table with Spark

Spark connects to the same Hive Metastore. The aggregate is saved as a Hive table and can then be queried from Beeline. Creation stops if `orderdb.order_aggregate` already exists; use a fresh table name in both the script and subsequent queries for a repeat run. Existing results are preserved.

Create a local working directory on the VM for lesson files.

```bash
mkdir -p .state
```

Create the PySpark application on the VM. Paste this complete heredoc, including the final `PY` line.

```bash
cat > .state/spark_hive_orders.py <<'PY'
from pyspark.sql import SparkSession

spark = (SparkSession.builder
    .appName('hive-order-aggregate')
    .config('spark.sql.catalogImplementation', 'hive')
    .config('hive.metastore.uris', 'thrift://hive-metastore:9083')
    .enableHiveSupport()
    .getOrCreate())

orders = spark.table('orderdb.orders')
orders.show(truncate=False)
aggregate = orders.groupBy('customer').sum('amount').withColumnRenamed('sum(amount)', 'total_amount')
aggregate.write.format('hive').mode('errorifexists').saveAsTable('orderdb.order_aggregate')
spark.table('orderdb.order_aggregate').orderBy('customer').show(truncate=False)
spark.stop()
PY
```

Copy the local lesson file or directory from the VM into the selected container.

```bash
oc -n bigdata cp .state/spark_hive_orders.py spark-master-0:/tmp/spark_hive_orders.py -c jupyter
```

Save the master pod IP in `DRIVER_IP`. Spark executors use this address to connect back to the driver. Run the next submission in this same terminal.

```bash
DRIVER_IP=$(oc -n bigdata get pod spark-master-0 -o jsonpath='{.status.podIP}')
```

Submit the application to the standalone Spark master. Paste this entire multiline command and wait for it to finish before inspecting results.

```bash
oc -n bigdata exec spark-master-0 -c jupyter -- spark-submit \
  --master spark://spark-master:7077 \
  --total-executor-cores 1 --executor-cores 1 \
  --executor-memory 512m --driver-memory 512m \
  --conf "spark.driver.host=$DRIVER_IP" \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --conf spark.driver.port=7078 \
  --conf spark.blockManager.port=7079 \
  /tmp/spark_hive_orders.py
```

## 5. Query the Spark-created table through Beeline

Run the SQL through Beeline against HiveServer2 and inspect the returned table or metadata.

```bash
oc -n bigdata exec deployment/hiveserver2 -- beeline \
  -u jdbc:hive2://hiveserver2:10000 -n team \
  --silent=true --showHeader=true --outputformat=table \
  -e "SHOW TABLES IN orderdb; SELECT * FROM orderdb.order_aggregate ORDER BY customer;"
```

## 6. Inspect metadata, HDFS locations and UIs

Run the SQL through Beeline against HiveServer2 and inspect the returned table or metadata.

```bash
oc -n bigdata exec deployment/hiveserver2 -- beeline -u jdbc:hive2://hiveserver2:10000 -n team --silent=true -e "DESCRIBE FORMATTED orderdb.orders; DESCRIBE FORMATTED orderdb.order_aggregate;"
```

List HDFS files and directories to check their paths and output files.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls -R /training/orders
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:10002 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/hiveserver2 10002:10002
```

## 7. Return to the low-memory profile

Keep the Hive Metastore running for Spark and Trino catalog access. Stop only HiveServer2 after the lesson.

Stop these workloads without deleting their storage.

```bash
oc -n bigdata scale deployment/hiveserver2 --replicas=0
```

Inspect the workload definitions and Services for these components.

```bash
oc -n bigdata get deployment hive-metastore hiveserver2
```

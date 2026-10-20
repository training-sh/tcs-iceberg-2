# Hive external tables and Spark SQL

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Examples that print forwarding commands show what to run in a separate terminal; keep each forward running while using its URL.

Strict-mode command blocks use `( ... )` subshells so their `set -euo pipefail` settings do not change or close your interactive terminal. Variables inside one such block do not carry into the next.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Copy each block into the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a terminal in the Linux VM. The one-time functions are installed by [00 - Installation](../00-Introduction/00-Installation.md). Load them, connect `oc` to the running CRC cluster, and select the `bigdata` project before continuing.

```bash
# Load the helpers into this terminal, then validate access.
source "$HOME/.bashrc"
if declare -F okd-env >/dev/null; then
  okd-env && oc whoami && oc project && oc get nodes
else
  echo 'Complete 00-Introduction/00-Installation.md first.' >&2
fi
```

## 1. Start HDFS, Hive Metastore, HiveServer2 and Spark

HiveServer2 is disabled in the normal low-memory profile. Start it only for this lesson.

```bash
(
# 1. Start HDFS, Hive Metastore, HiveServer2 and Spark
set -euo pipefail
oc -n bigdata scale statefulset/namenode statefulset/datanode statefulset/spark-master statefulset/spark-worker --replicas=1
for s in namenode datanode spark-master spark-worker; do oc -n bigdata rollout status statefulset/$s --timeout=300s; done
oc -n bigdata scale deployment/hive-metastore deployment/hiveserver2 --replicas=1
oc -n bigdata rollout status deployment/hive-metastore --timeout=300s
oc -n bigdata rollout status deployment/hiveserver2 --timeout=300s
oc -n bigdata get pods -l 'app in (hive-metastore,hiveserver2)'
)
```

## 2. Place order data in HDFS

```bash
(
# 2. Place order data in HDFS
set -euo pipefail
oc -n bigdata exec namenode-0 -- sh -c "cat > /tmp/orders.csv <<'DATA'
1,2026-01-01,alice,120.50
2,2026-01-01,bob,75.00
3,2026-01-02,alice,40.00
4,2026-01-02,carol,210.25
5,2026-01-03,bob,25.00
DATA"
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/orders/input
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/orders.csv /training/orders/input/orders.csv
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/orders/input/orders.csv
)
```

## 3. Create an external Hive table with Beeline

This lesson creates an external table over the HDFS source directory. The DROP example is disabled. `IF NOT EXISTS` preserves an existing table definition; inspect its schema and location before reusing it.

```bash
(
# 3. Create an external Hive table with Beeline
set -euo pipefail
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
SQL
beeline -u jdbc:hive2://hiveserver2:10000 -n team --silent=true --showHeader=true --outputformat=table -f /tmp/orders.sql"
)
```

## 4. Read Hive and create an aggregate table with Spark

Spark connects to the same Hive Metastore. The aggregate is saved as a Hive table and can then be queried from Beeline. Creation stops if `orderdb.order_aggregate` already exists; use a fresh table name in both the script and subsequent queries for a repeat run. Existing results are preserved.

```bash
(
# 4. Read Hive and create an aggregate table with Spark
set -euo pipefail
mkdir -p .state
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
oc -n bigdata cp .state/spark_hive_orders.py spark-master-0:/tmp/spark_hive_orders.py -c jupyter
DRIVER_IP=$(oc -n bigdata get pod spark-master-0 -o jsonpath='{.status.podIP}')
oc -n bigdata exec spark-master-0 -c jupyter -- spark-submit \
  --master spark://spark-master:7077 \
  --total-executor-cores 1 --executor-cores 1 \
  --executor-memory 512m --driver-memory 512m \
  --conf "spark.driver.host=$DRIVER_IP" \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --conf spark.driver.port=7078 \
  --conf spark.blockManager.port=7079 \
  /tmp/spark_hive_orders.py
)
```

## 5. Query the Spark-created table through Beeline

```bash
(
# 5. Query the Spark-created table through Beeline
set -euo pipefail
oc -n bigdata exec deployment/hiveserver2 -- beeline \
  -u jdbc:hive2://hiveserver2:10000 -n team \
  --silent=true --showHeader=true --outputformat=table \
  -e "SHOW TABLES IN orderdb; SELECT * FROM orderdb.order_aggregate ORDER BY customer;"
)
```

## 6. Inspect metadata, HDFS locations and UIs

```bash
(
# 6. Inspect metadata, HDFS locations and UIs
set -euo pipefail
oc -n bigdata exec deployment/hiveserver2 -- beeline -u jdbc:hive2://hiveserver2:10000 -n team --silent=true -e "DESCRIBE FORMATTED orderdb.orders; DESCRIBE FORMATTED orderdb.order_aggregate;"
oc -n bigdata exec namenode-0 -- hdfs dfs -ls -R /training/orders
echo
echo 'HiveServer2 status: oc -n bigdata port-forward --address=127.0.0.1 service/hiveserver2 10002:10002'
echo 'Open: http://127.0.0.1:10002'
)
```

## 7. Return to the low-memory profile

Keep the Hive Metastore running for Spark and Trino catalog access. Stop only HiveServer2 after the lesson.

```bash
(
# 7. Return to the low-memory profile
set -euo pipefail
oc -n bigdata scale deployment/hiveserver2 --replicas=0
oc -n bigdata get deployment hive-metastore hiveserver2
)
```

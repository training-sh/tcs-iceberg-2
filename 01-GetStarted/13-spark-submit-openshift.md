# Submit a Spark word-count job to HDFS

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

## 1. Start HDFS and Spark

```bash
(
# 1. Start HDFS and Spark
set -euo pipefail
oc -n bigdata scale statefulset/namenode statefulset/datanode statefulset/spark-master statefulset/spark-worker --replicas=1
for s in namenode datanode spark-master spark-worker; do oc -n bigdata rollout status statefulset/$s --timeout=300s; done
)
```

## 2. Prepare the shared HDFS input

```bash
(
# 2. Prepare the shared HDFS input
set -euo pipefail
oc -n bigdata exec namenode-0 -- sh -c "printf 'spark hadoop spark\nopenshift spark hdfs\nhadoop data\n' > /tmp/spark-words.txt"
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/spark/input
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/spark-words.txt /training/spark/input/words.txt
# DO NOT DELETE: reference only; keep this command commented out.
# oc -n bigdata exec namenode-0 -- hdfs dfs -rm -r -f /training/spark/spark-word-count
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/spark/input/words.txt
)
```

## 3. Create the PySpark application in the Jupyter container

```bash
(
# 3. Create the PySpark application in the Jupyter container
set -euo pipefail
mkdir -p .state
cat > .state/spark_hdfs_wordcount.py <<'PY'
from pyspark.sql import SparkSession
from operator import add

spark = SparkSession.builder.appName('hdfs-word-count').getOrCreate()
sc = spark.sparkContext
input_path = 'hdfs://namenode:9000/training/spark/input'
output_path = 'hdfs://namenode:9000/training/spark/spark-word-count'
words = sc.textFile(input_path).flatMap(lambda line: line.split()).map(lambda word: (word.lower(), 1)).reduceByKey(add)
words.sortByKey().map(lambda item: f'{item[0]}\t{item[1]}').saveAsTextFile(output_path)
print('RESULT:', words.sortByKey().collect())
spark.stop()
PY
oc -n bigdata cp .state/spark_hdfs_wordcount.py spark-master-0:/tmp/spark_hdfs_wordcount.py -c jupyter
oc -n bigdata exec spark-master-0 -c jupyter -- sed -n '1,120p' /tmp/spark_hdfs_wordcount.py
)
```

## 4. Submit to the standalone Spark master

`--total-executor-cores` limits the total cores used by this application. `--executor-cores` controls cores per executor. The single-worker lab uses one of each.

```bash
(
# 4. Submit to the standalone Spark master
set -euo pipefail
DRIVER_IP=$(oc -n bigdata get pod spark-master-0 -o jsonpath='{.status.podIP}')
oc -n bigdata exec spark-master-0 -c jupyter -- spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --name hdfs-word-count \
  --total-executor-cores 1 \
  --executor-cores 1 \
  --executor-memory 512m \
  --driver-memory 512m \
  --conf "spark.driver.host=$DRIVER_IP" \
  --conf spark.driver.bindAddress=0.0.0.0 \
  --conf spark.driver.port=7078 \
  --conf spark.blockManager.port=7079 \
  /tmp/spark_hdfs_wordcount.py
)
```

## 5. Inspect the HDFS result

```bash
(
# 5. Inspect the HDFS result
set -euo pipefail
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /training/spark/spark-word-count
oc -n bigdata exec namenode-0 -- sh -c "hdfs dfs -cat '/training/spark/spark-word-count/part-*' | sort"
)
```

## 6. Inspect Spark application state and logs

```bash
(
# 6. Inspect Spark application state and logs
set -euo pipefail
oc -n bigdata logs spark-master-0 -c spark-master --tail=50
oc -n bigdata logs spark-worker-0 -c spark-worker --tail=50
echo 'Open the master UI with:'
echo 'oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18080:8080'
)
```

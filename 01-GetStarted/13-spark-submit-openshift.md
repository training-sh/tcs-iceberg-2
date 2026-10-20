# Submit a Spark word-count job to HDFS

Run the lesson sections in order after the course workloads have been deployed. Startup, restart, scale, and data-writing blocks change the lab. The initialization block must succeed before you continue. Run UI forwarding commands in separate VM terminals and keep them running while using their URLs.

Run commands one at a time and check each result before continuing. Enter heredocs and commands continued with `\` as complete units. If a command fails, resolve the error before running the next command.

**DO NOT DELETE lab resources or data.** Bash deletion examples are commented with `#`; SQL deletion examples use `--`. Keep those comments in place. Sample input commands using `-put -f` overwrite only the named lesson input files. MapReduce/Spark output directories must not already exist; for a repeat run, choose a fresh output path and update every occurrence in that lesson instead of deleting previous results.

These are Bash commands for the Linux VM terminal, not Jupyter cells. Run the commands in the VM terminal; the in-cluster Jupyter container does not provide the `oc` administration client. Commands use the current OpenShift context and namespace `bigdata`.

## Initialize the VM terminal

Open a Bash terminal in the Linux VM after completing [Bash configuration](../00-bashrc.md). Run this once per terminal to load the cluster credentials and select `bigdata`. Continue only when it succeeds. If the cluster is stopped, run `okd-start`. If `okd-env` is not found, run `source ~/.bashrc` and retry.

```bash
okd-env
```

## 1. Start HDFS and Spark

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

## 2. Prepare the shared HDFS input

Create the sample text file inside the NameNode container.

```bash
oc -n bigdata exec namenode-0 -- sh -c "printf 'spark hadoop spark\nopenshift spark hdfs\nhadoop data\n' > /tmp/spark-words.txt"
```

Create the HDFS input directory. `-p` also creates missing parent directories.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/spark/input
```

Upload the container file into HDFS. `-f` replaces only the named sample input file.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -put -f /tmp/spark-words.txt /training/spark/input/words.txt
```

Reference only: keep this deletion command commented out.

```bash
# oc -n bigdata exec namenode-0 -- hdfs dfs -rm -r -f /training/spark/output/spark-word-count
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -cat /training/spark/input/words.txt
```

Prepare a separate output parent. Spark runs as `spark`, while the sample input was uploaded by the HDFS lab account.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/spark/output
```

Give Spark ownership of only this output parent. Do not change the input directory or use a recursive ownership change.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -chown spark /training/spark/output
```

## 3. Create the PySpark application in the Jupyter container

Create a local working directory on the VM for lesson files.

```bash
mkdir -p .state
```

Create the PySpark application on the VM. Paste this complete heredoc, including the final `PY` line.

```bash
cat > .state/spark_hdfs_wordcount.py <<'PY'
from pyspark.sql import SparkSession
from operator import add

spark = SparkSession.builder.appName('hdfs-word-count').getOrCreate()
sc = spark.sparkContext
input_path = 'hdfs://namenode:9000/training/spark/input'
output_path = 'hdfs://namenode:9000/training/spark/output/spark-word-count'
words = sc.textFile(input_path).flatMap(lambda line: line.split()).map(lambda word: (word.lower(), 1)).reduceByKey(add)
words.sortByKey().map(lambda item: f'{item[0]}\t{item[1]}').saveAsTextFile(output_path)
print('RESULT:', words.sortByKey().collect())
spark.stop()
PY
```

Copy the local lesson file or directory from the VM into the selected container.

```bash
oc -n bigdata cp .state/spark_hdfs_wordcount.py spark-master-0:/tmp/spark_hdfs_wordcount.py -c jupyter
```

Read the file inside the container to verify its contents.

```bash
oc -n bigdata exec spark-master-0 -c jupyter -- sed -n '1,120p' /tmp/spark_hdfs_wordcount.py
```

## 4. Submit to the standalone Spark master

`--total-executor-cores` limits the total cores used by this application. `--executor-cores` controls cores per executor. The single-worker lab uses one of each.

Save the master pod IP in `DRIVER_IP`. Spark executors use this address to connect back to the driver. Run the next submission in this same terminal.

```bash
DRIVER_IP=$(oc -n bigdata get pod spark-master-0 -o jsonpath='{.status.podIP}')
```

Submit the application to the standalone Spark master. Paste this entire multiline command and wait for it to finish before inspecting results.

```bash
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
```

## 5. Inspect the HDFS result

List HDFS files and directories to check their paths and output files.

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -ls /training/spark/output/spark-word-count
```

Read the HDFS file contents to verify the data.

```bash
oc -n bigdata exec namenode-0 -- sh -c "hdfs dfs -cat '/training/spark/output/spark-word-count/part-*' | sort"
```

## 6. Inspect Spark application state and logs

Read recent logs from `spark-master-0`. Check for startup or connection errors.

```bash
oc -n bigdata logs spark-master-0 -c spark-master --tail=50
```

Read recent logs from `spark-worker-0`. Check for startup or connection errors.

```bash
oc -n bigdata logs spark-worker-0 -c spark-worker --tail=50
```

In a separate VM terminal, run `okd-env`, then start this forward. Keep it running and open http://127.0.0.1:18080 in the VM browser. Press Ctrl+C when finished.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18080:8080
```

## Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Run follow commands in a separate VM terminal after `okd-env`. Press Ctrl+C to stop following; this does not stop the workload. A scaled-to-zero workload has no current pod logs.

Follow Spark master logs during submission.

```bash
oc -n bigdata logs -f spark-master-0 -c spark-master --tail=50 --timestamps
```

Read Spark worker logs for executor scheduling errors.

```bash
oc -n bigdata logs spark-worker-0 -c spark-worker --since=10m --timestamps
```

Read the Jupyter server logs. The driver launched by oc exec prints to the submitting terminal, rather than necessarily appearing in these container logs.

```bash
oc -n bigdata logs spark-master-0 -c jupyter --tail=50 --timestamps
```

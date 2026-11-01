# Part 3: Workers and recovery ? 45 minutes

Allocate 10 minutes to capacity and scale-out, 15 to failure/recovery, 10 to service control and 10 to restoration. These steps intentionally change workload state in a dedicated exercise environment. They were not executed during reference verification.

## 1. Record the baseline

Use the same terminal throughout so the saved counts remain available. Finish other Spark applications first.

```bash
export NS=bigdata
BASE_WORKERS=$(oc -n "$NS" get sts spark-worker -o jsonpath='{.spec.replicas}')
BASE_MASTER=$(oc -n "$NS" get sts spark-master -o jsonpath='{.spec.replicas}')
BASE_RM=$(oc -n "$NS" get deploy resourcemanager -o jsonpath='{.spec.replicas}')
BASE_NM=$(oc -n "$NS" get deploy nodemanager -o jsonpath='{.spec.replicas}')
BASE_MR_HISTORY=$(oc -n "$NS" get deploy historyserver -o jsonpath='{.spec.replicas}')
BASE_GRAFANA=$(oc -n "$NS" get sts grafana -o jsonpath='{.spec.replicas}')
BASE_LOKI=$(oc -n "$NS" get sts loki -o jsonpath='{.spec.replicas}')
BASE_ALLOY=$(oc -n "$NS" get sts alloy -o jsonpath='{.spec.replicas}')
printf 'workers=%s master=%s rm=%s nm=%s mr_history=%s grafana=%s loki=%s alloy=%s\n' "$BASE_WORKERS" "$BASE_MASTER" "$BASE_RM" "$BASE_NM" "$BASE_MR_HISTORY" "$BASE_GRAFANA" "$BASE_LOKI" "$BASE_ALLOY"
oc adm top nodes
oc -n "$NS" get sts spark-worker -o yaml
oc -n "$NS" get resourcequota,limitrange
```

Record the printed values outside the shell too. Confirm capacity for another worker; its configured resource requests, memory/CPU limits and Spark worker memory all matter. If baseline workers is not one, adapt the target and restoration deliberately. Do not scale down other active workloads to force this exercise through.

## 2. Scale Spark workers from one to two

```bash
oc -n "$NS" scale sts/spark-worker --replicas=2
oc -n "$NS" rollout status sts/spark-worker --timeout=180s
oc -n "$NS" get pods -l app=spark-worker -o wide
```

Expect two Ready worker pods and two registrations in the master UI. If a pod is Pending, inspect its description and events; return to the recorded count if capacity is insufficient. No additional OKD node has been created.

Open `03-workers-and-recovery.ipynb` in a fresh kernel. Run through workload submission and pause. The 24 partitions each sleep for eight seconds, leaving time for inspection. In the live driver UI, confirm active tasks and executor placement. The notebook allows two executor cores in total; an old session limited to one core will not demonstrate both workers.

## 3. Remove one worker pod during the job

In a second terminal, watch pods and events:

```bash
oc -n bigdata get pods -l app=spark-worker -w
```

While tasks are running, delete only the second worker pod. This simulates worker-pod loss; it is not an OKD node failure.

```bash
oc -n "$NS" get pod spark-worker-1 -o jsonpath='{.metadata.uid}{"\n"}'
oc -n "$NS" delete pod spark-worker-1 --wait=false
oc -n "$NS" get events --sort-by=.lastTimestamp
oc -n "$NS" rollout status sts/spark-worker --timeout=180s
oc -n "$NS" get pods -l app=spark-worker -o wide
```

Compare the replacement UID after readiness:

```bash
oc -n "$NS" get pod spark-worker-1 -o jsonpath='{.metadata.uid}{"\n"}'
```

Expect the StatefulSet to recreate the pod with a new UID. Observe executor loss and any task retries in the driver UI. Task loss is timing-dependent: if that worker had no running tasks, rerun the workload and observe placement before repeating. A successful final result alone does not prove a retry occurred. Record executor loss/task attempt evidence and the recreated pod UID.

Run the next notebook cell. Expected total: `71994000`, with the same result read back from SeaweedFS. The reference verification confirms this normal result without fault injection. If the job fails, retain the driver error, events and executor evidence before rerunning; external side effects are not automatically exactly-once under Spark retries.

## 4. Restart and restore workers

Stop the notebook session first. A rolling restart replaces the worker pods and discards local executor logs/scratch; persistent SeaweedFS data and event logs remain.

```bash
oc -n "$NS" rollout restart sts/spark-worker
oc -n "$NS" rollout status sts/spark-worker --timeout=180s
oc -n "$NS" scale sts/spark-worker --replicas="$BASE_WORKERS"
oc -n "$NS" rollout status sts/spark-worker --timeout=180s
```

## 5. Explicit service stop/start commands

Review dependencies before executing. The reference has YARN stopped already. `historyserver` below is MapReduce history, not Spark History Server. Retain PVCs and avoid interrupting active applications.

```bash
# Stop YARN processes; HDFS remains available.
oc -n "$NS" scale deploy/resourcemanager deploy/nodemanager deploy/historyserver --replicas=0
# Start the existing YARN processes only when needed.
oc -n "$NS" scale deploy/resourcemanager deploy/nodemanager deploy/historyserver --replicas=1
oc -n "$NS" rollout status deploy/resourcemanager --timeout=180s
oc -n "$NS" rollout status deploy/nodemanager --timeout=180s
oc -n "$NS" rollout status deploy/historyserver --timeout=180s
# Restore their individual starting counts.
oc -n "$NS" scale deploy/resourcemanager --replicas="$BASE_RM"
oc -n "$NS" scale deploy/nodemanager --replicas="$BASE_NM"
oc -n "$NS" scale deploy/historyserver --replicas="$BASE_MR_HISTORY"
```

Optional existing Grafana/Loki/Alloy services can be started for Part 2's view. They consume additional memory; the core exercise does not require them.

```bash
oc -n "$NS" scale sts/loki sts/alloy sts/grafana --replicas=1
oc -n "$NS" rollout status sts/loki --timeout=180s
oc -n "$NS" rollout status sts/alloy --timeout=180s
oc -n "$NS" rollout status sts/grafana --timeout=180s
# Restore after viewing. Pausing Alloy stops new collection.
oc -n "$NS" scale sts/alloy --replicas="$BASE_ALLOY"
oc -n "$NS" scale sts/grafana --replicas="$BASE_GRAFANA"
oc -n "$NS" scale sts/loki --replicas="$BASE_LOKI"
```

Spark/Jupyter stop/start is a separate optional exercise after saving notebook work. Scaling the master stops Jupyter, Spark master and Spark History Server together. Existing manual forwards then terminate.

```bash
oc -n "$NS" scale sts/spark-worker --replicas=0
oc -n "$NS" scale sts/spark-master --replicas=0
# Start the existing workloads again.
oc -n "$NS" scale sts/spark-master --replicas="$BASE_MASTER"
oc -n "$NS" rollout status sts/spark-master --timeout=180s
oc -n "$NS" scale sts/spark-worker --replicas="$BASE_WORKERS"
oc -n "$NS" rollout status sts/spark-worker --timeout=180s
oc -n "$NS" get deploy,sts,pods
```

Keep SeaweedFS and PostgreSQL running while using Polaris. Restart forwarding manually after master recreation. If baseline replicas were zero, skip readiness waits for that stopped workload.

## 6. Optional cleanup of temporary plain Parquet

Each notebook writes its exact root into its `ops_...json` record. In a new notebook cell with an active Spark session, substitute one reviewed run root below. This deletes only that run's plain data; do not delete the warehouse bucket, shared event prefix or a catalog-managed table location.

```python
from pathlib import Path
import json
record = json.loads(Path('ops_REPLACE_WITH_RUN_ID.json').read_text())
expected = f"s3a://{config['bucket']}/{config['temporary_prefix']}/{record['run_id']}"
assert record['run_id'].startswith('ops_') and record['root'] == expected
path = spark._jvm.org.apache.hadoop.fs.Path(expected)
fs = path.getFileSystem(spark._jsc.hadoopConfiguration())
assert fs.delete(path, True), 'Prefix missing or deletion failed'
```

If Part 2 was interrupted before cleanup, use its recorded run ID to drop only `polaris.RUN_ID.orders PURGE`, then `polaris.RUN_ID`. Do this before deleting any storage manually. Stop the cleanup Spark session when finished. Preserve history for review and allow the existing retention policy to remove old event logs.

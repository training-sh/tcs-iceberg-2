# Part 1: Run and inspect Spark ? 45 minutes

Allocate 10 minutes to forwarding, 15 to notebook execution, 15 to UI inspection and 5 to history handoff.

## 1. Check readiness

Complete the README preflight. Use the namespace in the current terminal:

```bash
export NS=bigdata
oc -n "$NS" get pods -l app=spark-worker
oc -n "$NS" wait --for=condition=Ready pod/spark-master-0 pod/spark-worker-0 --timeout=120s
oc -n "$NS" get svc spark-master -o yaml
```

The reference master pod has `spark-master`, `spark-history` and `jupyter` containers. Confirm those names on your environment.

## 2. Forward ports directly

Run each forwarding command in its own terminal and keep it open. These local ports avoid the existing managed forwarders' usual ports. All bindings remain localhost.

```bash
oc -n bigdata port-forward --address=127.0.0.1 pod/spark-master-0 28888:8888
```

```bash
oc -n bigdata port-forward --address=127.0.0.1 pod/spark-master-0 28080:8080
```

```bash
oc -n bigdata port-forward --address=127.0.0.1 pod/spark-master-0 24040:4040
```

```bash
oc -n bigdata port-forward --address=127.0.0.1 pod/spark-master-0 28082:18080
```

| Interface | VM browser URL |
|---|---|
| Jupyter | http://127.0.0.1:28888/lab |
| Spark master | http://127.0.0.1:28080/ |
| Live driver | http://127.0.0.1:24040/ |
| Spark history | http://127.0.0.1:28082/ |

Use the existing Jupyter authentication method; do not disable it. The driver forward may report a connection failure before a SparkContext exists. If the notebook reports 4041, stop only that forwarding terminal and forward `24040:4041` instead. Restart port forwarding after the target pod is recreated.

## 3. Execute the notebook

Open `01-run-and-inspect.ipynb` with a fresh Python kernel. Run through the data cell and pause before `spark.stop()`.

The driver logging cell records a handled Python error in an explicit application log, then asserts Spark remains healthy. The deliberate `ZeroDivisionError` is caught; the notebook must continue successfully.

Expected assertions: four identical rows after the SeaweedFS Parquet round trip; north total 200; south total 200. Record the `ops_...` run ID, application ID and S3 prefix. The notebook deliberately uses standalone Spark, not `local[*]`, YARN or native Kubernetes executor mode.

## 4. Inspect the live application

In the master UI, locate the printed application ID and registered worker. In the driver UI:

1. Open Jobs and select the write or aggregation job.
2. Follow its stages and identify shuffle boundaries.
3. Open SQL and inspect the aggregate plan.
4. Open Executors and compare driver and executor entries, task counts and memory.
5. Match the executor's host to the worker pod's IP from `oc get pods -o wide`.

Read the Python driver log using the exact filename printed by the notebook:

```bash
oc -n "$NS" exec spark-master-0 -c jupyter -- tail -n 40 /workspace/user_notebooks/spark-operations-workshop/ops_REPLACE_WITH_RUN_ID-driver.log
```

Expect `ERROR`, the controlled exception traceback and the later healthy message. This file is on the notebook PVC and survives worker replacement. JVM driver diagnostics remain in notebook kernel stderr unless an existing JVM logging destination is configured. Do not equate this Python application log with all JVM diagnostics.

Python notebook output is driver-side output. Spark master daemon logs do not contain the complete notebook driver's output. Part 2 distinguishes the log sources.

Run the final notebook cell. The live UI stops with SparkContext; the completed application should become visible in History Server. Refresh after the history scan interval. Confirm the same application ID and completed status.

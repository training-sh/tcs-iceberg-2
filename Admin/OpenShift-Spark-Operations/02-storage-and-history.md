# Part 2: Storage, history and logs ? 45 minutes

Allocate 15 minutes to the storage notebook, 10 to history, 15 to logs and 5 to optional monitoring.

## 1. Run the storage notebook

With the previous session stopped, open `02-storage-and-history.ipynb` in a fresh kernel. Run until the inspection checkpoint.

Expected results: four exact rows after S3 readback; a Polaris Iceberg table with the same rows; updating one amount produces a total of 420; at least two snapshots; physical Parquet and Iceberg metadata objects exist in SeaweedFS. Polaris stores catalog state while SeaweedFS stores table objects. The table location printed by the notebook can differ from the plain Parquet exercise prefix.

## 2. Inspect runtime event-log settings

```bash
export NS=bigdata
oc -n "$NS" exec spark-master-0 -c jupyter -- python3 -c 'import os; from pathlib import Path; p=Path(os.environ["SPARK_CONF_DIR"])/"spark-defaults.conf"; print("Configuration:",p); print("\n".join(x for x in p.read_text().splitlines() if x.startswith(("spark.eventLog.","spark.history."))))'
oc -n "$NS" logs spark-master-0 -c spark-history --tail=60
```

The reference configuration points event logs and history at `s3a://warehouse/spark-events`. These logs reconstruct Jobs, Stages, SQL and Executors; they are not a replacement for stdout/stderr. Stop the notebook session after inspection and match its completed application ID in History Server.

## 3. Read container and platform evidence

```bash
oc -n "$NS" logs spark-master-0 -c spark-master --tail=80
oc -n "$NS" logs spark-master-0 -c jupyter --tail=80
oc -n "$NS" logs spark-worker-0 -c spark-worker --tail=80
oc -n "$NS" logs deployment/polaris --tail=60
oc -n "$NS" logs seaweedfs-0 --tail=60
oc -n "$NS" get events --sort-by=.lastTimestamp
oc -n "$NS" describe pod spark-worker-0
oc -n "$NS" get pod spark-worker-0 -o jsonpath='{range .status.containerStatuses[*]}{.name}{" restarts="}{.restartCount}{" previous="}{.lastState}{"\n"}{end}'
# Only when this container has actually restarted:
oc -n "$NS" logs spark-worker-0 -c spark-worker --previous --tail=60
```

| Evidence | Source | Limitation |
|---|---|---|
| Notebook Python output and errors | Notebook cell outputs | Not all kernel output appears in Jupyter server logs |
| Driver JVM messages | Kernel stderr and configured driver log destination | Jupyter server stdout is not a complete driver log |
| Worker registration and executor launches | Worker container log | Does not necessarily contain executor stdout/stderr |
| Executor messages | Worker UI and per-application executor files | Worker replacement may remove local files |
| Job/stage/task history | Spark event logs and History Server | Not full application text logs |
| Scheduling, image pulls, restarts | OpenShift events and pod status | Retention is finite |

## 4. Read actual executor stdout/stderr

Forward the worker UI in another terminal:

```bash
oc -n bigdata port-forward --address=127.0.0.1 pod/spark-worker-0 28081:8081
```

Open http://127.0.0.1:28081/ and find the application/executor matching your application ID. Follow stdout and stderr links. For command-line inspection, discover the worker work directory rather than guessing it:

```bash
oc -n "$NS" exec spark-worker-0 -c spark-worker -- sh -c 'printf "SPARK_WORKER_DIR=%s\nSPARK_HOME=%s\n" "$SPARK_WORKER_DIR" "$SPARK_HOME"; ps -ef | head -20; find /data /opt/spark/work /opt/spark/work-dir /tmp -maxdepth 5 -type f \( -name stdout -o -name stderr \) 2>/dev/null | head -30'
# Replace this example path with a path returned above for YOUR application.
oc -n "$NS" exec spark-worker-0 -c spark-worker -- tail -n 60 /ACTUAL/WORK/DIRECTORY/APPLICATION_ID/EXECUTOR_ID/stderr
```

The verified worker writes executor files under `/opt/spark/work/APPLICATION_ID/EXECUTOR_ID/`. Use the matching ID from your run rather than copying an old path.

An empty stdout file is valid when the workload prints nothing on executors. Inspect stderr for executor startup/task messages. Do not use a different application's files as evidence for this run.

## 5. Native monitoring and Grafana

Follow [Grafana and Loki](04-grafana-loki.md) for the verified log-collection exercise. The existing Grafana, Loki and Alloy services have now been started and log queries verified; the Prometheus datasource remains unavailable.

```bash
oc adm top nodes
oc adm top pods -n "$NS"
oc -n "$NS" get sts grafana loki alloy
oc -n "$NS" get svc grafana
```

Use the existing OpenShift console's Observe pages when accessible. Platform/control-plane logs require separate permissions and are outside this project's centralized log scope. For an authorized cluster administrator, these direct read-only commands expose native Kubernetes diagnostics:

```bash
oc get clusteroperators
oc -n openshift-kube-apiserver get pods
oc -n openshift-kube-apiserver get pod kube-apiserver-crc -o jsonpath='{.spec.containers[*].name}{"\n"}'
# Substitute the actual pod and node discovered on your installation.
oc -n openshift-kube-apiserver logs kube-apiserver-crc -c kube-apiserver --tail=40
oc adm node-logs crc -u kubelet --tail=40
```

The reference API-server and kubelet log reads succeeded. If access is denied, retain project-level logs and request the relevant evidence from the environment owner; no RBAC change is part of this workshop. `oc logs` and events work independently of centralized logging.

If Grafana is already running, forward it without changing workloads:

```bash
oc -n bigdata port-forward --address=127.0.0.1 svc/grafana 23000:3000
```

Open http://127.0.0.1:23000/ using its configured account. Existing Loki/Alloy collection covers container stdout/stderr, not arbitrary executor files. If these services are stopped, skip the optional view or use Part 3's explicit start/restore commands during the exercise. No installation is required for the core path.

Run the notebook's cleanup cell to purge only its temporary Polaris table and namespace, then its final stop cell. Plain Parquet remains for optional cleanup.

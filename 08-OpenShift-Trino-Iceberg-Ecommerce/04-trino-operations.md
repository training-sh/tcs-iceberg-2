# 04 — Trino operations: lifecycle, workers and cleanup

Use a host terminal on the Linux desktop. The data exercises assume services are already running. The commands here intentionally change workload state or remove exercise data. Run only the operation needed; do not execute the whole page as a script.

## 1. Inspect before changing state

```bash
cd ~/openshift/08-OpenShift-Trino-Iceberg-Ecommerce
export PATH="$HOME/.crc/bin/oc:$PATH"
oc get statefulset -n bigdata trino
oc get pods -n bigdata -l app=trino
oc get svc -n bigdata trino
oc get pvc -n bigdata
oc get statefulset -n bigdata trino -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

To inspect active query work, use the CLI before stopping or reducing capacity:

```bash
oc exec -n bigdata trino-0 -- trino --server http://localhost:8080 --user team --execute "SELECT query_id, state FROM system.runtime.queries WHERE state IN ('QUEUED', 'RUNNING')"
```

The monitoring statement itself can appear while it executes. Check the UI for other active queries and finish Airflow/Spark exercises first. If optional password authentication is enabled, use the HTTPS CLI connection from [web access](05-trino-web-ui-and-access.md) instead of these unauthenticated HTTP commands.

## 2. Stop and start the current single-node Trino

Stop only Trino after active queries finish:

```bash
oc scale statefulset/trino -n bigdata --replicas=0
oc get pods -n bigdata -l app=trino
```

The pod terminates. Existing Trino PVCs and the source/object-store data remain. In-flight queries are not preserved. This command does not stop MySQL, Polaris, PostgreSQL or SeaweedFS.

Start it again:

```bash
oc scale statefulset/trino -n bigdata --replicas=1
oc rollout status statefulset/trino -n bigdata --timeout=600s
oc exec -n bigdata trino-0 -- trino --server http://localhost:8080 --user team --execute 'SELECT version(); SELECT count(*) FROM tpch.tiny.nation;'
```

Expected: one ready pod, Trino 476 and 25 nations. Required data services must already be available. Do not reapply a deployment manifest to start the installed service: the manifest may contain zero replicas or older resource settings.

The root component helper can start additional dependencies for the full stack, including Hive/HDFS. Use these direct Trino commands when only the existing Trino instance needs to change state. Do not restart the stack for a SQL table error.

## 3. Understand the optional worker definition

Read [trino-workers.yaml](trino-workers.yaml) before applying it. It defines:

- A worker ConfigMap with `coordinator=false` and coordinator discovery at `http://trino:8080`.
- A headless worker Service and `statefulset/trino-worker` at **zero replicas**.
- A separate `app=trino-worker` label; the coordinator's Service must not select it.
- The same Trino 476 image family and catalog environment as the existing deployment.
- A 768 MB heap, 256 MB per-node query memory limit and 1536 MiB container memory limit.
- Disposable local data through emptyDir. Iceberg table objects remain in SeaweedFS.

The upstream image's launcher derives a unique node ID from the pod hostname when `node.id` is absent. All nodes use the same `node.environment=training`; this is a Trino cluster environment name, not a database.

Compare the prepared worker image with the current coordinator image. If they differ, edit the worker manifest to use the coordinator's exact image and verify that its catalogs match. A newer image tag is not a substitute for version compatibility. If the coordinator's catalog definitions come from mounted configuration rather than the image, supply those same definitions to the worker before starting it.

Review the existing `service/trino` selector. It should select the coordinator's `app=trino` pods only:

```bash
oc get svc -n bigdata trino -o jsonpath='{.spec.selector}{"\n"}'
```

## 4. Start one separate worker — optional

This creates configuration/workload definitions and starts extra compute. Keep it optional on CRC. Check host/CRC capacity and keep other Spark drivers and streaming queries stopped. The worker's low request is a scheduling floor, not its actual memory usage.

First validate and create the zero-replica definitions:

```bash
oc apply --dry-run=server -f trino-workers.yaml
oc apply -f trino-workers.yaml
oc get statefulset -n bigdata trino-worker
```

Expected: zero desired worker pods. If the coordinator already uses the optional shared-secret/password profile, apply the [worker authentication patch](trino-worker-auth-patch.yaml) **before** scaling it up, as described in lesson 05.

Then start one worker:

```bash
oc scale statefulset/trino-worker -n bigdata --replicas=1
oc rollout status statefulset/trino-worker -n bigdata --timeout=600s
oc get pods -n bigdata -l app=trino-worker
```

Use the Trino SQL prompt to verify discovery:

```sql
SELECT node_id, coordinator, state
FROM system.runtime.nodes
ORDER BY coordinator DESC, node_id;

SELECT count(*) FROM tpch.tiny.nation;
```

Expected: one coordinator plus one non-coordinator node, both active, and a nation count of 25. Node registration does not guarantee that both nodes process every query. A tiny query can need very little parallelism. Verify a small Iceberg read too: workers must reach Polaris and SeaweedFS with valid permissions.

The current coordinator still executes tasks. In a larger dedicated-coordinator layout, set `node-scheduler.include-coordinator=false` only after worker capacity and rollout plans are ready. That is a separate coordinator configuration change and restart; it is unnecessary for this one-worker demonstration.

## 5. Reduce worker count and stop the cluster

After query work finishes, remove the optional worker capacity:

```bash
oc scale statefulset/trino-worker -n bigdata --replicas=0
oc get pods -n bigdata -l app=trino-worker
```

Scaling down during a running query can fail its tasks; do not assume draining or fault-tolerant retries are enabled. Keep the coordinator at one replica while using it. To stop all Trino compute, stop workers first and then the coordinator. For restart, bring up the coordinator, wait for readiness, and then bring back only the worker count required.

Do not increase `statefulset/trino` above one replica. Do not add multiple workers on a constrained single-node CRC deployment just to demonstrate a bigger count. More replicas share the same CPU, memory and failure domain.

## 6. Diagnose failures with targeted checks

| Symptom | Check |
|---|---|
| Pod Pending | Events, quotas, free memory and CPU requests |
| CrashLoopBackOff | Pod termination reason and private logs; configuration and JVM/container memory relationship |
| Worker absent from node list | Same release/environment, unique node ID and discovery URI |
| Worker cannot join after authentication changes | Matching internal shared secret on coordinator and workers |
| Metadata works but Iceberg scan fails | Worker storage endpoint, S3 credentials and allowed object locations |
| Query exceeds memory | Input size, join shape, query limits and heap headroom; do not blindly raise limits |
| MySQL works on coordinator but not worker | Matching catalog properties, Secret wiring and source network access |

```bash
oc describe pod -n bigdata trino-worker-0
oc logs -n bigdata trino-worker-0 --tail=100
```

Review logs privately before sharing. Do not print catalog files, Secret values or whole environments. `/data` on the optional worker is disposable; persistent table data must remain in its external store.

## 7. Maintenance and cleanup

Compaction rewrites data files. Snapshot expiration removes old table references. Orphan cleanup can delete unreferenced objects. These operations have different purposes and can affect time travel. Ten order lines do not justify recurring maintenance jobs. Do not reduce retention or run deletion loops for these exercises.

When the exercise tables are no longer needed, check exact names and run this **optional destructive SQL** at the Trino prompt:

```sql
DROP TABLE iceberg_polaris.trino_ecomm_s01.gold_daily_sales;
DROP TABLE iceberg_polaris.trino_ecomm_s01.silver_order_lines;
DROP TABLE iceberg_polaris.trino_ecomm_s01.bronze_order_lines;
DROP SCHEMA iceberg_polaris.trino_ecomm_s01;

DROP TABLE mysql.trino_ecomm.trino_s01_order_items;
DROP TABLE mysql.trino_ecomm.trino_s01_orders;
DROP TABLE mysql.trino_ecomm.trino_s01_products;
DROP TABLE mysql.trino_ecomm.trino_s01_customers;
```

Skip MySQL cleanup if exercise 02 was not run. Iceberg DROP TABLE can delete referenced objects. Keep the `trino_ecomm` database if other exercise runs still use it. Do not delete Hive metadata, shared buckets or PVCs. No CASCADE is used; stop on unexpected remaining objects. Stop loopback forwards with Ctrl+C when finished.

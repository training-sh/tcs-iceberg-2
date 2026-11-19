# Reference commands

Run from the extracted capstone directory in the VM terminal. These commands use the existing cluster and images. They do not build images, install a cluster, change registry permissions or reconfigure platform monitoring. The section numbers match `README.md`.

Use Bash on the VM. The README gives selected command examples and adaptable patterns; this file supplies the corresponding full command reference. Its examples omit `-n` where the active project is already selected. `REPLACE_...` tokens in either file must be replaced before execution. Commands that save to `evidence/` below use the flat layout allowed by the README; step-prefixed filenames or per-step folders should be used for the final submission.

## 1. Access and project

```bash
export PATH="$HOME/.crc/bin:$HOME/.crc/bin/oc:$HOME/.local/bin:$PATH"
crc status
oc whoami
oc version
oc get nodes
oc get co
oc get storageclass
oc new-project olist-seller-ops
oc apply -f manifests/00-project.yaml
oc project olist-seller-ops
```

If CRC is stopped, start the existing instance with `crc start` before checking access. If authentication has expired, use the login details supplied for that VM. Do not create another cluster.
## 2. Configuration and inputs

```bash
sha256sum data/olist_sellers_dataset.csv data/olist_order_items_dataset.csv data/olist_orders_dataset.csv
mkdir -p working evidence
cp manifests/02-secret-template.yaml working/02-secrets.yaml
```

The working copy supplies training credentials: username/client/access key `team` and password/secret `team1234`. Preserve these relationships:

| Setting | Required relationship |
|---|---|
| Database username | `team` in both database Secrets |
| Database password | Same value in `lab-credentials/database-password` and `mysql-credentials/password` |
| MySQL root password | `team1234` (root username remains `root`) |
| S3 credentials | Same access/secret values in `lab-credentials` and the `s3.json` identity |
| Polaris credentials | Client `team`; bootstrap value `POLARIS,team,` followed by the same client secret |
| Grafana login | `password=team1234` in `grafana-login`; username `team` |

```bash
oc apply -f working/02-secrets.yaml
oc -n olist-seller-ops create secret generic grafana-login --from-literal=password='team1234'
oc apply -f manifests/03-application.yaml
oc -n olist-seller-ops create configmap seller-input-main --from-file=data/olist_sellers_dataset.csv --from-file=data/olist_order_items_dataset.csv
oc -n olist-seller-ops create configmap seller-input-orders --from-file=data/olist_orders_dataset.csv
oc -n olist-seller-ops get configmap,secret
```

Do not use raw Secret exports as evidence. Input ConfigMaps are created directly because adding their content to a client-side apply annotation exceeds the annotation size limit.
## 3. S3 and databases

```bash
oc apply -f manifests/10-seaweedfs.yaml
oc apply -f manifests/11-postgresql.yaml
oc apply -f manifests/12-mysql.yaml
oc -n olist-seller-ops rollout status statefulset/seaweedfs --timeout=300s
oc -n olist-seller-ops rollout status statefulset/postgres --timeout=300s
oc -n olist-seller-ops rollout status statefulset/mysql --timeout=300s
oc -n olist-seller-ops get pods,pvc
```

Expected: all three server pods Ready, all three PVCs Bound. On a fresh MySQL PVC, `MYSQL_DATABASE=hive_metastore` creates the required metadata database and grants the application user access.
## 4. Polaris

```bash
oc apply -f manifests/20-polaris-bootstrap.yaml
oc -n olist-seller-ops wait --for=condition=Complete job/polaris-bootstrap --timeout=300s
oc -n olist-seller-ops logs job/polaris-bootstrap
oc apply -f manifests/21-polaris.yaml
oc -n olist-seller-ops rollout status deployment/polaris --timeout=300s
oc apply -f manifests/22-polaris-catalog.yaml
oc -n olist-seller-ops wait --for=condition=Complete job/polaris-catalog --timeout=300s
oc -n olist-seller-ops logs job/polaris-catalog
```

Expected: successful realm bootstrap, Ready server and `POLARIS_CATALOG_READY training s3://warehouse/iceberg`. The bootstrap manifest calls the existing Java application directly so the image launcher does not echo credential-bearing arguments.
## 5. Hadoop and Hive

```bash
oc apply -f manifests/30-hdfs.yaml
oc -n olist-seller-ops rollout status statefulset/namenode --timeout=300s
oc -n olist-seller-ops rollout status statefulset/datanode --timeout=300s
oc -n olist-seller-ops exec namenode-0 -- hdfs dfsadmin -report
oc -n olist-seller-ops exec namenode-0 -- hdfs dfs -mkdir -p /user/hive/warehouse /olist /tmp/hive
oc -n olist-seller-ops exec namenode-0 -- hdfs dfs -chmod 1777 /tmp/hive
oc -n olist-seller-ops exec namenode-0 -- hdfs dfs -ls -d /tmp/hive /olist /user/hive/warehouse
oc apply -f manifests/31-hive-schema.yaml
oc -n olist-seller-ops wait --for=condition=Complete job/hive-schema --timeout=300s
oc -n olist-seller-ops logs job/hive-schema
oc apply -f manifests/32-hive.yaml
oc -n olist-seller-ops rollout status deployment/hive-metastore --timeout=300s
```

Expected: one live DataNode, scratch mode `drwxrwxrwt`, successful schema initialization and Ready Metastore. Keep HiveServer2 at zero until the metadata check.
## 6. Input, Spark and Trino

```bash
oc apply -f manifests/69-input-job.yaml
oc -n olist-seller-ops wait --for=condition=Complete job/seller-input-upload --timeout=300s
oc -n olist-seller-ops logs job/seller-input-upload
oc apply -f manifests/40-spark.yaml
oc -n olist-seller-ops rollout status statefulset/spark-master --timeout=300s
oc -n olist-seller-ops rollout status deployment/spark-worker --timeout=300s
```

Expected: three `INPUT_UPLOADED` messages and one registered Spark worker. Keep Trino stopped until Spark publishing completes.

For the registration checks in this section and section 9, start forwarding now in a separate VM terminal and leave it running:

```bash
oc -n olist-seller-ops port-forward service/spark-master 18080:8080
```

Open `http://localhost:18080` in the VM browser, or use `curl -fsS http://localhost:18080/json/` in another terminal. Restart forwarding if it exits; each additional forwarding command needs its own terminal.
## 7. Processing

```bash
oc apply -f manifests/60-metrics.yaml
oc apply -f manifests/61-logging.yaml
oc -n olist-seller-ops rollout status deployment/ops-metrics --timeout=300s
oc -n olist-seller-ops rollout status deployment/loki --timeout=300s
oc -n olist-seller-ops rollout status deployment/log-collector --timeout=300s
oc apply -f manifests/70-seller-job.yaml
oc -n olist-seller-ops wait --for=condition=Complete job/seller-process --timeout=900s
oc -n olist-seller-ops logs job/seller-process > evidence/processing.log
oc -n olist-seller-ops logs job/seller-process
```

Expected: `INPUT_COUNT`, `OUTPUT_VERIFIED` for both output tables and `SELLER_COMPUTE_PASS`. Copy that run ID, then start Trino and prepare verification:

```bash
oc apply -f manifests/50-trino.yaml
oc -n olist-seller-ops rollout status statefulset/trino --timeout=300s
oc -n olist-seller-ops exec trino-0 -- trino --server http://localhost:8080 --user team --execute 'SHOW CATALOGS'
cp manifests/71-verify-job.yaml working/71-verify-job.yaml
```

Replace `REPLACE_RUN_ID` in the working copy with the actual compute run ID, then run:

```bash
oc apply -f working/71-verify-job.yaml
oc -n olist-seller-ops wait --for=condition=Complete job/seller-verify --timeout=600s
oc -n olist-seller-ops logs job/seller-verify > evidence/verification.log
oc -n olist-seller-ops logs job/seller-verify
```

Expected: `TRINO_VERIFIED` for both tables and `SELLER_OPS_PASS`. The verification checks all rows against the input bytes and records a durable verification table in Polaris/S3. Processing seconds combine compute and verification work, excluding the wait while Trino starts. On a corrected compute retry, keep Trino stopped, delete only the failed `seller-process` Job and apply its manifest again; the program creates a fresh run ID.
## 8. Result validation

```bash
cp queries/validation.sql working/validation.sql
```

Replace `RUN_SCHEMA` in the working copy with the actual run ID, then execute it:

```bash
oc -n olist-seller-ops exec -i trino-0 -- trino --server http://localhost:8080 --user team --file /dev/stdin < working/validation.sql
oc -n olist-seller-ops exec namenode-0 -- hdfs dfs -ls -R /olist
```

Expected totals: 3,095 sellers, 3,379 item rows, merchandise value `390764.28`, 3,022 on-time items, 321 late items and 36 missing-handoff items. Geography has 23 rows. The differing-row count must be zero. Full expected rows, status counts and schemas are in `EXPECTED_RESULTS.md` and `expected-results.json`.
## 9. Worker scaling

```bash
oc -n olist-seller-ops scale statefulset/trino --replicas=0
oc -n olist-seller-ops get deployment spark-worker > evidence/workers-before.txt
oc -n olist-seller-ops scale deployment/spark-worker --replicas=2
oc -n olist-seller-ops rollout status deployment/spark-worker --timeout=300s
oc -n olist-seller-ops get deployment spark-worker > evidence/workers-after.txt
curl -fsS http://localhost:18080/json/ > evidence/worker-registration.json
```

Expected: two desired and Ready workers, and two alive workers in Spark. The application intentionally uses one execution core to control memory; registration demonstrates available capacity rather than guaranteed speedup.
## 10. Hive access and controlled shutdown

The metadata statement is also supplied in `queries/hive_metadata.sql`.

```bash
oc -n olist-seller-ops scale deployment/hiveserver2 --replicas=1
oc -n olist-seller-ops rollout status deployment/hiveserver2 --timeout=300s
oc -n olist-seller-ops exec deployment/hiveserver2 -- /opt/hive/bin/beeline -u jdbc:hive2://localhost:10000/default -n team -e 'SHOW DATABASES;'
oc -n olist-seller-ops scale deployment/hiveserver2 --replicas=0
```

Save the direct logs before stopping their pods. Retain all PVCs:

```bash
oc -n olist-seller-ops logs statefulset/spark-master > evidence/master.log
oc -n olist-seller-ops logs deployment/spark-worker --all-pods=true > evidence/workers.log
oc -n olist-seller-ops scale deployment/spark-worker deployment/hive-metastore --replicas=0
oc -n olist-seller-ops scale statefulset/namenode statefulset/datanode --replicas=0
oc -n olist-seller-ops get pods,pvc
oc apply -f manifests/50-trino.yaml
oc -n olist-seller-ops rollout status statefulset/trino --timeout=300s
```

HDFS/Hive queries are intentionally unavailable while these servers are stopped. Business validation precedes this step; data remains on PVCs. The Spark master remains available for the UI and connectivity fault. To resume a later batch, restore the NameNode, DataNode, Metastore and worker replicas before running another processing Job.

## 11. Access, logs, application metrics and recovery

```bash
oc apply -f manifests/62-prometheus.yaml
oc apply -f manifests/63-grafana.yaml
oc apply -f manifests/64-routes.yaml
oc -n olist-seller-ops rollout status deployment/prometheus --timeout=300s
oc -n olist-seller-ops rollout status deployment/grafana --timeout=300s
oc -n olist-seller-ops get services,routes,endpointslices
oc -n olist-seller-ops logs statefulset/spark-master > evidence/master.log
```

Open the Route hostnames shown by the resource listing. Grafana uses `team` / `team1234`. If forwarding is needed, run each of these in its own terminal:

```bash
oc -n olist-seller-ops port-forward service/spark-master 18080:8080
oc -n olist-seller-ops port-forward service/grafana 13000:3000
oc -n olist-seller-ops port-forward service/prometheus 19090:9090
oc -n olist-seller-ops port-forward service/loki 13100:3100
```

Then use:

```bash
curl -fsS http://localhost:18080/json/
curl -fsS http://localhost:19090/api/v1/targets
curl -fsSG http://localhost:19090/api/v1/query --data-urlencode 'query=olist_job_success'
curl -fsSG http://localhost:19090/api/v1/query --data-urlencode 'query=olist_job_duration_seconds'
curl -fsSG http://localhost:13100/loki/api/v1/query_range --data-urlencode 'query={namespace="olist-seller-ops"} |= "SELLER_OPS_PASS"'
```

Expected: exporter target up, success value `1`, nonzero duration and processing success in Loki. Grafana's supplied dashboard uses the same datasources. Its temporary storage is not the durable run history; reports persist under S3 `warehouse/olist/reports/`.
Introduce the fault only after the successful baseline, with no processing Job running:

```bash
oc -n olist-seller-ops patch service spark-master --type=merge -p '{"spec":{"selector":{"app":"spark-mastre"}}}'
oc -n olist-seller-ops get service spark-master -o yaml
oc -n olist-seller-ops get pods --show-labels
oc -n olist-seller-ops get endpointslice -l kubernetes.io/service-name=spark-master
```

The Service now has no selected backend although the master pod is healthy. Restore the selector and verify recovery:

```bash
oc -n olist-seller-ops patch service spark-master --type=merge -p '{"spec":{"selector":{"app":"spark-master"}}}'
oc -n olist-seller-ops get endpointslice -l kubernetes.io/service-name=spark-master
curl -fsS http://localhost:18080/json/
```

Keep the fault injection and its answer separate from the assignment. The five-part explanation must identify the selector mismatch rather than crediting a blanket restart.
## 12. Metrics API

```bash
oc get apiservice v1beta1.metrics.k8s.io
oc describe apiservice v1beta1.metrics.k8s.io
oc top nodes
oc -n olist-seller-ops top pods
```

If the API is absent or unavailable, retain that result and its condition. `MissingEndpoints` means its registered backing Service has no ready endpoints. Application metrics do not depend on this API. Do not scale platform monitoring components or change their permissions to complete this task.


## Cleanup reference

Save the required evidence before deleting the capstone project. Delete only its namespace; do not remove `bigdata`, platform namespaces, images or cluster configuration.

```bash
oc delete project olist-seller-ops --wait=false
oc get namespace olist-seller-ops
```

Normal completion is `NotFound` for the namespace. Its workloads and PVCs are removed with it.

### When deletion remains Terminating

Inspect the reason rather than changing platform monitoring:

```bash
oc get namespace olist-seller-ops -o yaml
oc -n olist-seller-ops get pods,pvc,deploy,sts,jobs,cm,secrets,roles,rolebindings,sa,services,routes,endpointslices -o name
```

The reference cluster has a registered but stopped Metrics API. This can block namespace discovery even after all stored objects are removed. Leave that API and its permissions unchanged.

Finalization is appropriate only when the namespace conditions confirm all of the following: `NamespaceContentRemaining=False`, `NamespaceDeletionContentFailure=False`, `NamespaceFinalizersRemaining=False` and `NamespaceDeletionGroupVersionParsingFailure=False`; the resource listing is empty; and the only discovery failure is `metrics.k8s.io/v1beta1`. Metrics observations are transient, not stored namespace objects.

For that exact condition, save the namespace JSON, change only `spec.finalizers` to an empty array, and submit it to the namespace finalization endpoint:

```bash
oc get namespace olist-seller-ops -o json > working/namespace-finalize.json
```

After the single field has been changed:

```bash
oc replace --raw /api/v1/namespaces/olist-seller-ops/finalize -f working/namespace-finalize.json
oc get namespace olist-seller-ops
```

Do not use this fallback if content remains, an application finalizer remains, or another API group cannot be discovered. It is a namespace cleanup procedure, not a platform repair task.

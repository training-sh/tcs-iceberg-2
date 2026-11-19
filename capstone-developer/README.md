# Developer Capstone for Olist on OKD/CRC

Allow approximately **10 hours** with a working training cluster and completed Assignment 2 work. Budget 3.5 hours for Part 1, 5.5 hours for Part 2 and 1 hour for submission.

# Ensure to stop bigdata pods/resources for your capstone

# If **olist-seller-ops** namespace already present, you can delete that

### instructions here only for guidelines, you have options to follow your own way

## Hadoop/Hive can be optional only if we have resource constraints

[Part 1 work steps](#work-to-complete) | [Part 2](#part-2-automate-your-product-and-customer-analytics) | [Assessment](#assessment) | [Submission](#submission)

## Part 1 — Deploy and verify the supplied platform

The project uses three CSV files supplied in `data/`: sellers, orders, and order items. You may copy the files to any location you need on the training VM. Keep the original filenames and contents, and point your upload commands to the copied files if you work outside the capstone directory.

> **Guidance note:** The directions and hints are provided for information, to clarify expectations and help save time. They are not intended to prescribe a single approach or influence your solution choices. Use your own judgment and explain your decisions while meeting the required outcomes.

Deploy a platform that helps Olist's seller operations team check seller activity, merchandise value, fulfillment status and shipping deadlines. Use Spark to process the supplied data, Hive/Hadoop and Polaris/S3 to store the results, Trino to check them, and Loki, Prometheus and Grafana to observe the platform.

Plan for approximately **3.5 hours** for Part 1 with the existing cluster and supplied images ready. The capstone provides the input data, standalone programs, SQL, and OpenShift manifests. In Part 1, you deploy the supplied workload, run the seller analytics pipeline, validate its results in both catalogs, and demonstrate how you monitor and troubleshoot it. Use your existing CRC/OpenShift cluster and its supplied images. Do not build images, write application code, change platform monitoring or alter registry permissions during Part 1.

[Work steps](#work-to-complete) | [Architecture](#architecture) | [Assessment](#assessment) | [Submission](#submission) | [Cleanup](#cleanup-after-review)

## Architecture

```mermaid
flowchart TD
    CSV["Supplied Olist CSV files"]
    subgraph Project["olist-seller-ops namespace"]
        Upload["Input upload Job"] --> S3["SeaweedFS S3: inputs and results"]
        S3 --> Spark["Spark processing Job: master and workers"]
        Spark -->|Parquet files| HDFS["Hadoop HDFS"]
        Spark -->|Iceberg files| S3
        Spark -. table metadata .-> Hive["Hive Metastore"]
        Spark -. table metadata .-> Polaris["Polaris catalog"]
        Hive --> MySQL["MySQL: Hive metadata"]
        Polaris --> PostgreSQL["PostgreSQL: catalog metadata"]
        Check["Verification Job"] -->|SQL checks| Trino["Trino"]
        Trino -->|reads files| HDFS
        Trino -->|reads files| S3
        Trino -. metadata lookup .-> Hive
        Trino -. metadata lookup .-> Polaris
        Check -->|verified run report| Exporter["Application metrics exporter"]
        Exporter --> Prometheus["Prometheus"]
        Trino -->|query-engine metrics| Prometheus
        Logs["Pod and Job logs"] --> Collector["Log collector"]
        Collector --> Loki["Loki"]
        Loki --> Grafana["Grafana dashboard"]
        Prometheus --> Grafana
    end
    CSV --> Upload
```

Dashed arrows show table-metadata lookups or registration. Trino reads the physical files from HDFS and S3. ConfigMaps and Secrets provide settings and credentials. Services and Routes expose Spark UI and Grafana; Service forwarding is an alternative.

The diagram shows the logical platform. Follow the work order below: Spark publishing finishes before Trino verification, and completed batch services stop before dashboard observation.

## Before beginning

Use the existing CRC/OpenShift installation on the supplied training VM. The manifests reuse the course images; no image builds or new cluster installation are part of the exercise.

Part 1 runs in `olist-seller-ops` using the supplied manifests. Part 2 requires the **existing course Airflow instance in `bigdata`**, along with the course Spark, Trino, Polaris and SeaweedFS services. Airflow is required for Part 2. The capstone manifests do not install it. Complete the [Part 2 preflight](#part-2-preflight) before starting Part 1 so missing shared services can be raised with the instructor early.

Before beginning, confirm cluster access, a Ready node, a working default StorageClass and availability of the image references listed in `IMAGES.json`. Ask the instructor to confirm the exact private image digests are available and the `olist-workloads` ServiceAccount in `olist-seller-ops` has pull access before the timed work. A matching tag or a running copy in `bigdata` does not establish either prerequisite. Do not add registry grants or change security policies to work around a different VM image.

The workflow limits memory use by finishing Spark publishing before starting Trino verification. It then checks scaling and Hive access, saves evidence, and stops completed batch services before bringing up the dashboard. PVCs are retained until cleanup. Follow that order even if the VM has spare capacity.

The Kubernetes Metrics API may be unavailable on a training cluster. Application metrics use the supplied exporter and Prometheus, so processing and dashboard checks do not depend on that API. The final task is to inspect and explain its availability, leaving platform configuration unchanged.

CRC may report `OKD: Starting` while the existing API is reachable and its node is Ready because pre-existing operator checks are incomplete. Record the operator conditions; do not change platform services to make the summary label disappear.

Browser access uses the Route hosts created by the cluster. Service forwarding is provided as an alternative. Use the VM's own terminal and browser; `localhost` in the reference commands refers to that VM.

## Supplied files

| Location | Contents |
|---|---|
| `data/` | CSV inputs, checksums, row counts and expected totals |
| `programs/` | Complete standalone processing, verification, upload and telemetry programs |
| `manifests/` | Deployments, Jobs, storage, networking, settings and training credential templates |
| `queries/` | Ready-to-run Trino validation and Hive metadata queries |
| `IMAGES.json` | Existing image references used by the manifests |

## Data and expected results

| Input file | Role in the project |
|---|---|
| `olist_sellers_dataset.csv` | Provides seller IDs and states, including sellers with no sampled orders. |
| `olist_orders_dataset.csv` | Provides order status and carrier handoff timestamps. |
| `olist_order_items_dataset.csv` | Links orders to sellers and provides item prices and shipping deadlines. |

The supplied sample contains 3,095 sellers, 3,000 orders and 3,379 order-item rows. Orders are selected by a reproducible hash of `order_id`; all associated items and all sellers are retained. File sizes, hashes and row counts are in `data/manifest.json`.

Use the original relationships:

- `sellers.seller_id = order_items.seller_id`
- `order_items.order_id = orders.order_id`

### Seller activity

`seller_activity` has one row for every seller, including sellers with no sampled orders. It contains seller ID/state, distinct orders handled, item rows, merchandise value excluding freight, delivered/canceled/other distinct order counts, and on-time/late/missing carrier-handoff item counts.

Shipping performance compares item-level `shipping_limit_date` with order-level `order_delivered_carrier_date`. Equality is on time. A missing carrier timestamp is counted separately. The order-level timestamp is an operational proxy; it does not prove an individual seller's exact dispatch time.

Orders involving several sellers count once for each seller. Fulfillment counts are distinct orders per seller; shipping counts are item rows.

### Geography

`seller_geography` contains seller state, seller count and order-item rows. There are 23 state rows in the supplied sample.

### Expected totals

| Measure | Value |
|---|---:|
| Sellers | 3,095 |
| Input orders | 3,000 |
| Item rows | 3,379 |
| Seller-order pairs | 3,007 |
| Merchandise value | 390,764.28 |
| Delivered seller-order pairs | 2,947 |
| Canceled seller-order pairs | 11 |
| Other seller-order pairs | 49 |
| On-time handoff items | 3,022 |
| Late handoff items | 321 |
| Missing handoff items | 36 |

Both business tables are published to Hive/HDFS and Polaris/Iceberg/S3. The verification Job compares every row from both catalogs with independently calculated results from the CSV bytes. A successful run records `SELLER_OPS_PASS`, a report in the exporter and a durable verification table in Polaris/S3.

The processing programs are standalone files. They use the Python and Spark libraries already present in the supplied image; they do not import other project files or require package installation.

Source: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Retain its CC BY-NC-SA 4.0 attribution and terms when distributing this subset.

## Assessment

### Part 1 assessment (50 marks)

| Area | Marks | Full credit | Partial credit |
|---|---:|---|---|
| Cluster access and configuration | 8 | Verify identity, Ready node, storage, project, input integrity and configuration and Secret references. | 4-7 for verified access and incomplete configuration checks |
| Deployment, storage and access | 10 | Show Ready workloads, Bound PVCs, completed initialization, DataNode registration, service access and controlled shutdown. | 5-9 for a working subset with a supported diagnosis |
| Seller processing and validation | 14 | Both supplied Jobs succeed. Show matching run IDs, correct results in both catalogs, zero differences and physical storage evidence. | 7-13 for execution with incomplete validation |
| Scaling and observability | 8 | Verify worker counts and registration, explain capacity, and interpret logs, scrape health, dashboard readings and Metrics API availability. | 4-7 for sound evidence covering some checks |
| Diagnosis and recovery | 10 | Document the symptom, investigation, root cause, safe manifest or configuration fix, and verified recovery. | 5-9 for supported diagnosis or correction with incomplete recovery evidence |

### Part 2 assessment (50 marks)

| Area | Marks | Full credit | Partial credit |
|---|---:|---|---|
| Student-authored manifests and deployment | 12 | Submitted YAML deploys workflow resources and configuration on OKD/CRC with documented dependencies and Secret references where needed. | 6-11 for largely deployable YAML with gaps in configuration or rollout evidence |
| Airflow orchestration and execution | 16 | One trigger runs all required stages in order, including Trino validation. Execution is unattended and failures surface in task status. | 8-15 for an executed workflow with incomplete automation, validation or failure handling |
| Data correctness and persistence | 14 | Four Silver and two Gold Iceberg tables meet the Assignment 2 definitions, grain and reconciliation checks. Trino reads persisted outputs. | 7-13 for persisted outputs with incomplete or incorrect checks |
| Repeatability and handover | 8 | A second run preserves counts, keys and business totals. The runbook and evidence let a reviewer reproduce the workflow and trace both runs. | 4-7 for rerun or handover evidence with gaps |

Award lower marks for limited evidence and zero when there is no relevant evidence. **Total: 100 marks.**

A documented unavailable Metrics API does not lose marks when the condition is identified correctly and application metrics are verified. A proven scheduling limit can earn scaling credit when the desired configuration and diagnosis are correct. Do not claim successful execution where only manifests or screenshots are available.

Common errors include using the wrong project, inconsistent Secret keys, starting consumers before initialization completes, treating Running as Ready, confusing item rows with distinct orders, checking only output counts, and assuming replica count proves Spark registration. Credential values must be removed from evidence and any exposed value replaced privately.

## Submission

Save text evidence as you work. Submit `ParticipantID_Olist_Capstone.zip` with `part1/` and `part2/` folders.

In `part1/`, include:

- Final non-secret manifests and training credential templates.
- Cluster/project, workload, storage and networking checks.
- Processing and verification logs, run ID and SQL results.
- Worker counts and registration before and after scaling.
- Loki results, dashboard readings and Metrics API availability.
- The fault's symptom, investigation, root cause, correction and recovery.
- A short report explaining the deployment and any unresolved limits.

In `part2/`, submit your manifests, DAG source and referenced executable assets such as notebooks, scripts and SQL. Include a short runbook with prerequisites, deployment and trigger steps, output table names and evidence paths. Include resource rollout evidence and the Airflow and Trino evidence for both runs.

Screenshots may supplement text evidence. Exclude credentials, source data and unchanged supplied Part 1 programs.

### Organize the proof

In `part1/`, create an `evidence/` folder with `step01/` through `step12/` subfolders. In each, save relevant command history as `stepNN_commands.txt`, outputs or logs as `.txt` or `.log`, and supporting screenshots as `.png`. Use descriptive names, such as `step09_workers_before.png` and `step09_workers_after.png`. A single folder with the same step prefixes is also acceptable.

| Step | Proof to retain | Example filename |
|---|---|---|
| 1 | Identity, project, node and storage checks | `step01_cluster_status.txt` |
| 2 | Input hashes and sanitized configuration checks | `step02_input_checks.txt` |
| 3 | Ready storage/database pods and Bound PVCs | `step03_storage_status.txt` |
| 4 | Bootstrap, server readiness and catalog success | `step04_catalog.log` |
| 5 | DataNode registration, paths and Hive initialization | `step05_hive_ready.txt` |
| 6 | Three upload markers and worker registration | `step06_upload.log` |
| 7 | Compute/verification success logs and matching run ID | `step07_verification.log` |
| 8 | SQL results, differences and physical output locations | `step08_sql_results.txt` |
| 9 | Before/after worker counts, registration and saved logs | `step09_workers_after.png` |
| 10 | Hive query output and controlled workload shutdown | `step10_batch_shutdown.txt` |
| 11 | Dashboard, Loki, scrape health and five-part fault account | `step11_fault_report.md` |
| 12 | Metrics API condition and readings or explained limit | `step12_metrics_api_status.txt` |

Keep screenshots readable and show enough context to identify the project, resource or run. Pair them with text output where available. Reference the step number and relative evidence paths in your report; explain failed attempts and their corrections without claiming an unverified outcome. Remove credentials from command history, logs and screenshots, including literal Secret arguments and encoded Secret values. Do not submit a raw terminal-history dump.

## Cleanup after review

Keep the capstone resources until both parts have been reviewed. If you used shared services in Part 2, clean up only the resources and outputs you created, following your runbook. After review, delete only `olist-seller-ops` and confirm that its namespace, workloads and PVCs have been removed. Do not delete `bigdata`, existing images or platform resources.

**Hint:** deletion destroys the project's stored data. If the namespace remains Terminating, inspect its conditions and remaining resources before taking further action. Leave platform monitoring and permissions unchanged.

Cleanup follows evidence review; it is not an additional troubleshooting fault. The final operational task in the work list is the Metrics API check.

## If you get stuck

Confirm the project, inspect the resource state and events, then read the relevant logs. Check the dependency named in the work step before changing configuration. Change one thing at a time and verify the result.

| Symptom | Start by inspecting |
|---|---|
| Pod Pending | Scheduling events and PVC binding |
| Configuration error | Referenced ConfigMap/Secret names and keys |
| Image pull error | Exact reference in `IMAGES.json` and existing image availability |
| Repeated container restart | Termination reason, previous container logs and dependency readiness |
| Job does not complete | Job conditions, its pod logs and the last success marker |

Do not rebuild an image, change platform permissions or edit business logic to bypass a deployment problem.

### Useful references

Use these for the relevant operation, not as another deployment sequence. Keep the supplied image versions and manifests.

- Pod state and events: [application troubleshooting](https://kubernetes.io/docs/tasks/debug/debug-application/).
- Configuration references: [ConfigMaps](https://kubernetes.io/docs/concepts/configuration/configmap/) and [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/).
- Completion and retries: [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/).
- Connectivity: [Service troubleshooting](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/).
- Worker and application status: [Spark monitoring](https://spark.apache.org/docs/3.5.9/monitoring.html).
- Log inspection: [Grafana Explore](https://grafana.com/docs/grafana/latest/visualizations/explore/).

## Work to complete

### Using the command examples

The commands below are **examples and syntax references**, not a complete execution script. Read the purpose, inspect the supplied manifest and adapt each example before use. Replace every `REPLACE_...` token; do not type it literally. Choose the correct resource type and name from the manifest. The examples support your approach rather than prescribe a single solution.

Use a **Bash terminal on the training VM**, starting in the capstone directory where `manifests/`, `data/` and `queries/` are visible. These examples use the active project; check `oc project` when opening another terminal. `-n olist-seller-ops` can make the target explicit. The `--` separator in `oc exec` marks the start of the command inside the container. A terminal running `port-forward` must stay open; run other commands in a second terminal.

Do not apply the entire manifests directory at once. The order below allows initialization to finish and keeps memory available. Complete each **Check** before continuing. Save proof in the matching step folder as described under Submission.

| Operation | Command pattern | How to use it |
|---|---|---|
| Deploy a supplied file | `oc apply -f manifests/REPLACE_FILE.yaml` | Read its resource names and dependencies first |
| Wait for a server | `oc rollout status REPLACE_KIND/REPLACE_NAME --timeout=300s` | Use `deployment` or `statefulset` as defined in the manifest |
| Wait for a batch Job | `oc wait --for=condition=Complete job/REPLACE_NAME --timeout=300s` | Use the Job's metadata name, not the YAML filename |
| Inspect a failure | `oc describe pod REPLACE_POD` | Read Events and container state; find the pod with `oc get pods` |
| Read Job output | `oc logs job/REPLACE_NAME` | Search for the expected marker and the first error |
| Inspect recent events | `oc get events --sort-by=.metadata.creationTimestamp` | Match warnings to the resource being checked |

A timeout means the expected condition was not reached; inspect status and logs before retrying. Reapplying a completed Job does not run it again. Keep its evidence before considering a retry.

### 1. Prepare the project

Confirm the existing cluster is running. If it is stopped, use `crc start` for that instance. Authenticate with the access details supplied for your VM if `oc whoami` fails. Check the node and default storage provisioner before creating workloads.

```bash
crc status
oc whoami
oc version
oc get nodes
oc get co
oc get storageclass
```

Use the dedicated `olist-seller-ops` project assigned to you. If it is absent and your account can create projects, run `oc new-project olist-seller-ops`. Select it with `oc project olist-seller-ops`. The supplied YAML hard-codes that namespace. Apply `oc apply -n olist-seller-ops -f manifests/00-project.yaml` if your account can apply the Namespace resource. Otherwise have the instructor provision that Namespace and its `olist-workloads` ServiceAccount before the lab. On a shared cluster use the instructor-assigned setup so two learners do not operate in the same seller project.

**Check:** correct identity and active project, node `Ready`, a default StorageClass, and `olist-workloads` listed by `oc get serviceaccount`. Record existing operator warnings; do not repair platform services.

### 2. Prepare configuration and data

Create private working and evidence folders. Check the three CSV hashes against `data/manifest.json`; for example, `sha256sum data/olist_sellers_dataset.csv`. Repeat for the orders and items files.

```bash
mkdir -p working evidence/step02
cp manifests/02-secret-template.yaml working/02-secrets.yaml
```

The working copy supplies training credentials: username/client/access key `team` and password/secret `team1234`. Preserve these relationships:

| Configuration | Match to preserve |
|---|---|
| Database accounts | Both usernames remain `team`; `lab-credentials/database-password` equals `mysql-credentials/password` |
| MySQL root | `team1234` (root username remains `root`) |
| S3 | Access and secret keys match in `lab-credentials` and the `s3.json` identity |
| Polaris | Client stays `team`; bootstrap value is `POLARIS,team,` followed by that same client secret |
| Grafana | A separate `grafana-login` Secret with `password=team1234`; login user is `team` |

Apply the working Secret file and `03-application.yaml`. That application manifest already contains the programs as ConfigMap data; no code packaging or development is needed. Create Grafana credentials with `oc -n olist-seller-ops create secret generic grafana-login --from-literal=password=team1234`. Keep credentials out of submitted history.

Create `seller-input-main` from the sellers **and items** CSVs. Create `seller-input-orders` from the orders CSV. Example for the latter:

```bash
oc create configmap seller-input-orders --from-file=data/olist_orders_dataset.csv
```

For the first ConfigMap, use the same command pattern with two `--from-file` arguments. Create these input ConfigMaps directly; do not generate YAML and then use client-side apply, whose saved annotation can exceed the size limit.

**Check:** `oc get configmap,secret` lists the expected names. Filenames remain the ConfigMap keys. Compare Secret key names with the consuming manifest privately; do not export Secret values as proof.

### 3. Deploy storage and databases

Apply `10-seaweedfs.yaml`, `11-postgresql.yaml` and `12-mysql.yaml`. These create S3-compatible storage and the two metadata databases. Example for the first server:

```bash
oc apply -f manifests/10-seaweedfs.yaml
oc rollout status statefulset/seaweedfs --timeout=300s
oc get pods,pvc
```

Use the same apply/wait pattern for StatefulSets `postgres` and `mysql`. Wait for all three before continuing.

**Check:** three server pods are Ready and their PVCs are `Bound`. If a claim is Pending, inspect its events and StorageClass. If a pod restarts, inspect its logs and previous container logs (`oc logs REPLACE_POD --previous`). A Running pod alone is insufficient.

### 4. Prepare Polaris

Work in this order: bootstrap Job, Polaris server, then catalog Job. Start with:

```bash
oc apply -f manifests/20-polaris-bootstrap.yaml
oc wait --for=condition=Complete job/polaris-bootstrap --timeout=300s
oc logs job/polaris-bootstrap
```

Next apply `21-polaris.yaml` and wait for Deployment `polaris`. Then apply `22-polaris-catalog.yaml`, wait for Job `polaris-catalog` and read its logs using the same patterns.

**Check:** both Jobs Complete, server Ready, and catalog log contains `POLARIS_CATALOG_READY training s3://warehouse/iceberg`. If authentication fails, compare the related Secret fields privately. Do not edit the supplied program or repeat initialization without reading the failure.

### 5. Prepare Hadoop and Hive

Apply `30-hdfs.yaml`; wait for StatefulSets `namenode` and `datanode`. Confirm HDFS registration from inside the NameNode:

```bash
oc exec namenode-0 -- hdfs dfsadmin -report
```

Prepare `/user/hive/warehouse`, `/olist` and `/tmp/hive`. HDFS command reference: `hdfs dfs -mkdir -p REPLACE_PATH`; run it through `oc exec namenode-0 --`. Use HDFS `-chmod 1777 /tmp/hive` for the shared scratch directory, and `-ls -d` to inspect the three paths. These commands act on HDFS, not the VM filesystem.

Apply `31-hive-schema.yaml`, wait for Job `hive-schema` and read its logs. Only after it succeeds, apply `32-hive.yaml` and wait for Deployment `hive-metastore`. Leave `hiveserver2` at zero replicas until step 10.

**Check:** one live DataNode, all required paths, `/tmp/hive` mode `drwxrwxrwt`, successful Hive schema initialization and Ready Metastore. MySQL must remain Ready.

### 6. Upload the inputs and start Spark

Apply `69-input-job.yaml`; wait for Job `seller-input-upload` and read its logs. Continue only after finding three `INPUT_UPLOADED` messages, one per source file. Then apply `40-spark.yaml` and wait for StatefulSet `spark-master` and Deployment `spark-worker`.

To inspect registration, open a separate VM terminal and keep this example running:

```bash
oc -n olist-seller-ops port-forward service/spark-master 18080:8080
```

Open `http://localhost:18080` in the VM browser, or inspect `curl -fsS http://localhost:18080/json/` from another terminal. Keep this forwarding session for the scaling check; restart it if it exits.

**Check:** upload Job Complete, correct filenames, and one alive worker registered with the Spark master. Pod readiness and registered workers are different checks. Keep Trino stopped until publishing finishes.

### 7. Run and verify the supplied workload

Apply `60-metrics.yaml` and `61-logging.yaml`. Wait for Deployments `ops-metrics`, `loki` and `log-collector`. Apply `70-seller-job.yaml` to run the supplied processing program; no Python command needs to be assembled manually.

```bash
oc wait --for=condition=Complete job/seller-process --timeout=900s
oc logs job/seller-process
```

Find `INPUT_COUNT`, `OUTPUT_VERIFIED` for both tables and `SELLER_COMPUTE_PASS`. Save the log and copy the run ID exactly. For example, after creating its folder, `oc logs job/seller-process > evidence/step07/step07_compute.log` saves the output.

Only now apply `50-trino.yaml` and wait for StatefulSet `trino`. A useful connection check is:

```bash
oc exec trino-0 -- trino --server http://localhost:8080 --user team --execute 'SHOW CATALOGS'
cp manifests/71-verify-job.yaml working/71-verify-job.yaml
```

Replace `REPLACE_RUN_ID` in the working copy with the actual compute run ID. Apply that copy, wait for Job `seller-verify` with a `600s` timeout, and save its logs.

**Check:** both Jobs Complete; verification logs contain `TRINO_VERIFIED` for both tables and `SELLER_OPS_PASS` for the same run. If compute fails, read its first error and dependency state. Keep Trino stopped during a compute retry; do not rerun successful Jobs without a reason.

### 8. Check the business results

Copy `queries/validation.sql` to `working/validation.sql`. Replace **all** `RUN_SCHEMA` occurrences with the successful compute run ID. Run the working SQL file through the client inside the Trino pod:

```bash
oc exec -i trino-0 -- trino --server http://localhost:8080 --user team --file /dev/stdin < working/validation.sql
```

Here `-i` carries input into the container; `<` reads the file from the VM. Save the output, compare it with `data/expected-summary.json`, and explain the checks rather than merely recording that the command ran.

**Check:** 3,095 sellers, 3,379 items, merchandise value `390764.28`, 23 geography rows, and zero differing rows for both business tables. The supplied SQL also shows HDFS and S3 file locations and the durable verification record. Inspect HDFS while it is still running; reference: `oc exec namenode-0 -- hdfs dfs -ls -R /olist`. Distinct orders and item rows measure different things.

### 9. Scale and collect logs

Stop the completed Trino coordinator to release memory: use `oc scale statefulset/trino --replicas=0`. Retain its PVC. Record the original worker count and registered workers before making the change.

```bash
oc get deployment spark-worker
oc scale deployment/spark-worker --replicas=2
oc rollout status deployment/spark-worker --timeout=300s
```

Record the after-state and refresh Spark UI or its JSON endpoint from step 6. Save master, worker and Job logs before any shutdown. Multi-worker log example:

```bash
oc logs deployment/spark-worker --all-pods=true
```

**Check:** two desired and Ready replicas **and** two alive registered workers. If a worker is Pending, capture scheduling events and resource requests. Explain available capacity; this workload uses one execution core, so adding a registered worker does not guarantee faster execution.

### 10. Check Hive access and release batch resources

Run `oc scale deployment/hiveserver2 --replicas=1` and `oc rollout status deployment/hiveserver2 --timeout=300s`. Use its supplied client to run the statement in `queries/hive_metadata.sql`:

```bash
oc exec deployment/hiveserver2 -- /opt/hive/bin/beeline -u jdbc:hive2://localhost:10000/default -n team -e 'SHOW DATABASES;'
```

Save the output and logs, then stop the completed batch servers with the scale pattern used in step 9:

| Resource type | Names | Required replicas |
|---|---|---:|
| Deployment | `hiveserver2`, `spark-worker`, `hive-metastore` | 0 |
| StatefulSet | `namenode`, `datanode` | 0 |
| StatefulSet | `spark-master` | Keep running |
| StatefulSet | `trino` | Restore to 1 by reapplying `50-trino.yaml` |

**Check:** Hive metadata query succeeded, selected batch pods stop, Trino is Ready again, and PVCs remain Bound. Use `oc get pods,pvc` to distinguish stopped workloads from deleted storage. Hive/HDFS business queries are unavailable while their servers are stopped; that is why step 8 comes first.

### 11. Observe the platform and resolve the assigned fault

Apply `62-prometheus.yaml`, `63-grafana.yaml` and `64-routes.yaml`. Wait for Deployments `prometheus` and `grafana`. List access points and backends:

```bash
oc get services,routes,endpointslices
```

Open the Spark and Grafana Route hosts. Grafana uses `team` / `team1234` as prepared in step 2. If browser Route access is unavailable, adapt the step 6 forwarding pattern for Service `grafana` with local port `13000` and Service port `3000`.

In the supplied Grafana dashboard, record job success, processing seconds, input items and output rows. In Explore, select the Loki datasource and search for the same successful run. Query example:

```logql
{namespace="olist-seller-ops"} |= "SELLER_OPS_PASS"
```

Check Prometheus target health through its UI; forwarding example: `oc port-forward service/prometheus 19090:9090`, then open `http://localhost:19090/targets` in the VM browser. PromQL references include `olist_job_success`, `olist_job_duration_seconds`, `olist_input_items` and `olist_output_rows`.

Save a healthy baseline first, then tell the instructor you are ready for the assigned connectivity fault. The instructor will arrange the fault in your seller project. Compare the failing request with the same request after your correction. Save the symptom, investigation, root cause, correction and verified recovery. Useful investigation references are `oc describe service REPLACE_NAME`, `oc get pods --show-labels` and `oc get endpointslices`. Compare findings and choose a correction; no fault patch is supplied here.

**Check:** exporter target up, job success `1`, nonzero processing duration, matching run in Loki, authenticated dashboard access, and demonstrated fault recovery. For empty panels, inspect datasource health, scrape status and time range first. Do not introduce extra faults or change platform services.

### 12. Check the Metrics API

Inspect the Kubernetes Metrics API last. Registration alone does not prove it can serve readings.

```bash
oc get apiservice v1beta1.metrics.k8s.io
oc describe apiservice v1beta1.metrics.k8s.io
oc top nodes
oc top pods
```

**Check:** when available, save node and project pod CPU/memory readings. Otherwise, save the API condition or absence and explain the limitation. Use the backing Service named in the APIService to investigate endpoints if needed; do not start or reconfigure platform monitoring. Explain why the separate exporter/Prometheus path still provides application metrics. Save this as step 12 proof and leave permissions unchanged.

## Part 2 Automate your product and customer analytics

Turn your completed [Assignment 2](../openshift/Assignments-2/README.md) work into a workflow that a reviewer can deploy on OKD/CRC and trigger from Airflow. Use its four input datasets, business definitions and acceptance checks. Choose how to structure and package the notebooks, scripts and SQL that implement your workflow.

### Part 2 preflight

On the training VM, from a Bash terminal with `oc` already configured, check the shared runtime explicitly by namespace:

```bash
oc -n bigdata get pods,pvc
oc -n bigdata get svc airflow spark-master trino polaris seaweedfs
oc -n bigdata exec airflow-0 -- airflow version
oc -n bigdata exec airflow-0 -- airflow dags list-import-errors
oc -n bigdata exec airflow-0 -- airflow config get-value core executor
oc -n bigdata exec trino-0 -- trino --server http://localhost:8080 --user team --execute 'SHOW CATALOGS'
```

The course runtime uses Airflow 3. Confirm an approved DAG publication path and enough capacity for one Spark driver and an executor. If following the Spark Job example, check that Airflow can read its course template and that its service account can create and observe Jobs in the chosen project. The course RoleBinding grants these permissions in `bigdata`. Jobs and their mounted ConfigMaps, Secrets and PVC claims must be in the same project. If a prerequisite is missing, save the symptom and ask the instructor for the prepared runtime or access.

Use the full four-file Assignment 2 dataset and the Bronze location from your completed work. The input archive is about 21 MB. Stage inputs in S3 or the course workspace as appropriate. Keep CSVs out of ConfigMaps. Confirm the Spark catalog and the Trino catalog resolve the same Polaris warehouse. On the course stack Spark typically uses `polaris` and Trino uses `iceberg_polaris`. The seller project's Trino uses its own configuration.

### Deploy your workflow

- Write OpenShift manifests for the resources your workflow needs. Include configuration, delivery of the DAG and executable assets to Airflow, and any workload resources it launches, such as Spark Jobs. If the DAG creates Jobs dynamically, submit the Job template. Provide Secret references and placeholder templates where needed.
- Reuse training Airflow, Spark, Trino and Polaris/Iceberg services with SeaweedFS storage as appropriate. Document the project, endpoints, access, input paths and output namespace. Scope your resources and outputs to avoid collisions. Check service readiness. Keep the Part 1 batch services stopped when using the shared Part 2 stack. Use the approved publishing mechanism to put the DAG where Airflow discovers it and mount or stage Spark code where the driver can read it. The course uses separate Airflow and Spark workspace paths.

### Run and validate it in Airflow

1. The DAG must prepare or verify unchanged Bronze inputs, run the transformations that publish all four Silver tables, and build both Gold Iceberg tables from committed Silver. The Gold outputs are monthly delivered sales by customer state and customer value. Preserve Assignment 2's grains and definitions and document any namespace changes.
2. Execute Trino queries from Airflow against the persisted outputs. Verify Assignment 2's acceptance checks, including counts, grain keys, the missing-payment order and monetary reconciliation. Failed processing or validation must surface as a failed Airflow task. After triggering the workflow, it must finish without opening Jupyter or running queries manually.
3. Trigger it again with unchanged inputs. Verify that the second run preserves row counts, grain keys and business totals. Iceberg snapshot IDs may change. Save both Airflow run IDs, task statuses and relevant logs, plus the Trino results for correctness and repeatability.

Use the [OpenShift Airflow, Trino and Spark exercise](../openshift/09-OpenShift-Airflow-Trino-Spark-Ecommerce/README.md) and the [Airflow getting-started exercise](../12-airflow-getting-started/README.md) for deployment and orchestration examples. Use your own Assignment 2 implementation for the workflow.

### Troubleshooting hints

- Confirm DAG discovery before triggering. If a task has not queued, check the DAG import errors, pause state and active runs. The classroom executor has one task slot. Use one active run at a time.
- Test connectivity from the task or driver context. Use in-cluster Service names and ports. Add the project to the DNS name when calling a Service in another project. A VM port-forward is for interactive access from the VM.
- After submitting a Spark Job, wait for its terminal status before starting Trino validation. Use a bounded wait and record the Job name in the task log. For a Pending Job inspect pod events. For a running driver with no executor, check Spark worker registration and free cores and memory. Release the Spark session on exit.
- Use stable output table names and dedicated storage prefixes. Reuse the Assignment 2 full-refresh approach with existing schema and location checks. Avoid appending the same full snapshot. Where useful, compare the grain keys in both directions across runs and report missing or extra keys alongside summary totals.
- Troubleshoot SQL with a small read of a persisted Silver table first. Check catalog alias, schema, table visibility and engine credentials. Use exact decimal amounts for money comparisons. A successful SQL request still needs assertions on its returned results.

### Instructor release checks

Before assigning the 10-hour work, confirm the approved Part 1 project, image pulls and fault handoff, the Part 2 publication path and job permissions, and sufficient capacity to run the two workloads in sequence. A full rehearsal should run the supplied seller manifests through validation and fault recovery, then trigger a representative Assignment 2 workflow twice and capture Airflow and Trino evidence. Record elapsed time and any instructor setup outside the student clock.

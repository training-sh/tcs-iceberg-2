# Polaris and SeaweedFS: an Iceberg catalog backed by S3

Run these steps after [15 - SeaweedFS S3](15-seaweedfs.md). Commands run in the VM terminal unless a step explicitly switches to a container Bash shell or the PySpark Python prompt. Each command has a separate purpose; check its result before continuing.

This exercise creates a catalog, namespace, and table, writes rows, and examines the resulting S3 files. **Keep these resources: lesson 17 reuses them.** The `temp` suffix marks classroom examples; it does not mean they are deleted automatically. Leave the existing `training` catalog and `warehouse` bucket untouched. All new demo names end in `temp`.

| Layer | Demo name | Purpose |
|---|---|---|
| SeaweedFS S3 bucket | `demo-catalog-temp` | Stores this exercise's files |
| Polaris catalog | `demo_catalog_temp` | Registers Iceberg namespaces and tables |
| Spark catalog alias | `demo_catalog_temp` | Refers to that Polaris catalog from Spark SQL |
| Namespace / database | `demo_database_temp` | Groups tables within the catalog |
| Iceberg table | `demo_table_temp` | Stores three sample rows and their snapshot history |
| Warehouse root | `s3://demo-catalog-temp/iceberg` | Allowed S3 location for this catalog |

The Spark alias and Polaris catalog have the same name here for clarity. They are separate settings: Spark's `warehouse` property selects the **Polaris catalog name**, while Polaris's `default-base-location` specifies the **S3 path**.

## 1. Initialize and inspect the deployment

Open a VM Bash terminal and load cluster access. If CRC is stopped, use `okd-start` first.

```bash
okd-env
```

Find the Polaris pod. Confirm it is `Running` and ready.

```bash
oc -n bigdata get pods -l app=polaris -o wide
```

Inspect the Deployment that runs Polaris.

```bash
oc -n bigdata get deployment polaris
```

Inspect the Service and its endpoints. `8181` serves OAuth, management APIs, and the Iceberg REST catalog. `8182` serves health and operational endpoints.

```bash
oc -n bigdata describe service polaris
```

Check SeaweedFS, PostgreSQL, and the Spark master pod. Polaris stores its catalog state in PostgreSQL; Iceberg files live in SeaweedFS S3. The master pod's Jupyter container supplies the PySpark client for this lesson.

```bash
oc -n bigdata get pods -l 'app in (seaweedfs,postgres,spark-master)' -o wide
```

Read Polaris startup logs without changing resources.

```bash
oc -n bigdata logs deployment/polaris -c polaris --tail=40
```

## 2. Forward the APIs to the VM

In **terminal A**, run `okd-env`, then forward Polaris's API and health ports. Keep this terminal running.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/polaris 18181:8181 18182:8182
```

In **terminal B**, run `okd-env`, then forward the SeaweedFS S3 API and admin UI. If lesson 15's forwards already occupy these ports, reuse them or stop them before starting this replacement.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/seaweedfs 19001:8333 19002:23646
```

Use a separate **terminal C** for the API and AWS commands below. Keep that terminal open through the API and S3 inspection steps so its variables remain available. The later container/PySpark shell runs in **terminal D**.

| Interface | URL from the VM | Credentials |
|---|---|---|
| Polaris OAuth | `http://127.0.0.1:18181/api/catalog/v1/oauth/tokens` | Client ID `team`, client secret `team1234`, realm `POLARIS` |
| Polaris management API | `http://127.0.0.1:18181/api/management/v1` | OAuth bearer token and realm header |
| Iceberg REST catalog | `http://127.0.0.1:18181/api/catalog` | OAuth bearer token and realm header |
| Polaris readiness | [http://127.0.0.1:18182/q/health/ready](http://127.0.0.1:18182/q/health/ready) | No login |
| SeaweedFS S3 API | `http://127.0.0.1:19001` | Access key `team`, secret key `team1234` |
| SeaweedFS admin | [http://127.0.0.1:19002](http://127.0.0.1:19002) | Username `team`, password `team1234` |

Open browser links inside the VM, for example through RDP. This Polaris deployment has no catalog browser or enabled Swagger UI; `/q/swagger-ui/` returns 404. Use the authenticated APIs below to inspect catalogs. The existing `expose-uis.py` entry named `polaris-api` points at that unavailable Swagger path, so use the manual Polaris forward above. For SeaweedFS UI helper instructions, see lesson 15; avoid duplicate forwards on `19002`.

## 3. Configure terminal C and obtain an OAuth token

Load cluster access in terminal C.

```bash
okd-env
```

Create an isolated directory for this lesson's request and response files.

```bash
DEMO_DIR=$(mktemp -d /tmp/polaris-demo-temp.XXXXXX)
```

Set the forwarded Polaris API address.

```bash
export POLARIS_URL=http://127.0.0.1:18181
```

Set the forwarded S3 endpoint for VM-side commands. The Spark client inside the cluster will use the Service address instead.

```bash
export S3_ENDPOINT=http://127.0.0.1:19001
```

Set the S3 access key.

```bash
export AWS_ACCESS_KEY_ID=team
```

Set its S3 secret key.

```bash
export AWS_SECRET_ACCESS_KEY=team1234
```

Set the signing region.

```bash
export AWS_DEFAULT_REGION=us-east-1
```

Disable the AWS CLI pager.

```bash
export AWS_PAGER=""
```

Use an isolated AWS configuration rather than changing your normal profile.

```bash
export AWS_CONFIG_FILE="$DEMO_DIR/aws-config"
```

Configure path-style S3 addressing.

```bash
aws configure set default.s3.addressing_style path
```

Check Polaris health. Expect `"status": "UP"`.

```bash
curl -fsS http://127.0.0.1:18182/q/health/ready
```

Request an OAuth access token using the classroom client credentials. This multiline command saves the response without printing the token. The supplied account has administrative access for this lab; application access should normally use scoped roles.

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/oauth/tokens" \
  -H 'Polaris-Realm: POLARIS' \
  --data-urlencode grant_type=client_credentials \
  --data-urlencode client_id=team \
  --data-urlencode client_secret=team1234 \
  --data-urlencode scope=PRINCIPAL_ROLE:ALL \
  -o "$DEMO_DIR/token.json"
```

Extract the access token for later requests in this terminal. Tokens expire; repeat these two token steps if requests return 401 or after a Polaris restart.

```bash
TOKEN=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["access_token"])' "$DEMO_DIR/token.json")
```

List existing catalogs. Confirm `demo_catalog_temp` is absent before creating it. If it already exists, stop and inspect ownership rather than reusing or deleting it.

```bash
curl -fsS "$POLARIS_URL/api/management/v1/catalogs" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' | python3 -m json.tool
```

## 4. Create the dedicated S3 bucket

List buckets and confirm `demo-catalog-temp` is absent. Use these exact disposable names only when they are free; do not adopt an existing bucket.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls
```

Create the demo bucket. Continue only if creation succeeds and the bucket did not exist before this lesson.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 mb s3://demo-catalog-temp
```

List its contents. It should be empty because we have not created a table yet.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls s3://demo-catalog-temp/ --recursive
```

## 5. Define and create the Polaris catalog

Write the management API request to a local JSON file. This is a **catalog configuration**, not a Kubernetes manifest or an Iceberg manifest. Paste the complete heredoc through its closing `JSON` line.

```bash
cat > "$DEMO_DIR/catalog-temp.json" <<'JSON'
{
  "catalog": {
    "name": "demo_catalog_temp",
    "type": "INTERNAL",
    "properties": {
      "default-base-location": "s3://demo-catalog-temp/iceberg"
    },
    "storageConfigInfo": {
      "storageType": "S3",
      "allowedLocations": ["s3://demo-catalog-temp/iceberg"],
      "region": "us-east-1",
      "endpoint": "http://seaweedfs.bigdata.svc.cluster.local:8333",
      "endpointInternal": "http://seaweedfs.bigdata.svc.cluster.local:8333",
      "pathStyleAccess": true,
      "stsUnavailable": true
    }
  }
}
JSON
```

`allowedLocations` limits where this catalog may place tables. Both endpoint settings use cluster DNS because Polaris accesses storage from inside the cluster, not through the VM forward. `stsUnavailable` disables reliance on AWS STS for this S3-compatible lab; Spark supplies static S3 credentials separately. These settings use the deployment's existing local-storage feature configuration.

Create the catalog. If the API reports a conflict, stop rather than changing the existing catalog.

```bash
curl -fsS -X POST "$POLARIS_URL/api/management/v1/catalogs" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_DIR/catalog-temp.json"
```

Read the stored catalog configuration. Check its name, S3 root, and Service endpoint.

```bash
curl -fsS "$POLARIS_URL/api/management/v1/catalogs/demo_catalog_temp" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' | python3 -m json.tool
```

Inspect Iceberg REST configuration discovery for this catalog. Notice the catalog prefix in the response. Creating the catalog alone does not create data files or Iceberg manifests.

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/config?warehouse=demo_catalog_temp" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' | python3 -m json.tool
```

## 6. Open Bash and start an Iceberg-aware PySpark session

In **terminal D** on the VM, run `okd-env`, then open Bash in the Jupyter container. This container has Spark and the required Iceberg runtime and AWS bundle jars.

```bash
oc -n bigdata exec -it spark-master-0 -c jupyter -- bash
```

The next command runs **inside the container Bash shell**. It starts a small local Spark client with one execution thread; it does not submit to the standalone worker pool. This keeps the catalog demo independent of worker scheduling. The existing container environment supplies OAuth and S3 credentials. Paste the full multiline command.

```bash
pyspark --master 'local[1]' --driver-memory 512m \
  --conf spark.ui.enabled=false \
  --conf spark.eventLog.enabled=false \
  --conf spark.sql.shuffle.partitions=1 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.demo_catalog_temp=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.demo_catalog_temp.type=rest \
  --conf spark.sql.catalog.demo_catalog_temp.uri=http://polaris:8181/api/catalog \
  --conf spark.sql.catalog.demo_catalog_temp.warehouse=demo_catalog_temp \
  --conf spark.sql.catalog.demo_catalog_temp.oauth2-server-uri=http://polaris:8181/api/catalog/v1/oauth/tokens \
  --conf "spark.sql.catalog.demo_catalog_temp.credential=$POLARIS_CLIENT_ID:$POLARIS_CLIENT_SECRET" \
  --conf spark.sql.catalog.demo_catalog_temp.scope=PRINCIPAL_ROLE:ALL \
  --conf spark.sql.catalog.demo_catalog_temp.rest.auth.type=oauth2 \
  --conf spark.sql.catalog.demo_catalog_temp.header.Polaris-Realm=POLARIS \
  --conf spark.sql.catalog.demo_catalog_temp.rest-metrics-reporting-enabled=false \
  --conf spark.sql.catalog.demo_catalog_temp.io-impl=org.apache.iceberg.aws.s3.S3FileIO \
  --conf spark.sql.catalog.demo_catalog_temp.s3.endpoint=http://seaweedfs:8333 \
  --conf spark.sql.catalog.demo_catalog_temp.s3.path-style-access=true \
  --conf "spark.sql.catalog.demo_catalog_temp.s3.access-key-id=$AWS_ACCESS_KEY_ID" \
  --conf "spark.sql.catalog.demo_catalog_temp.s3.secret-access-key=$AWS_SECRET_ACCESS_KEY" \
  --conf spark.sql.catalog.demo_catalog_temp.client.region=us-east-1
```

Event logging is disabled for this small demo so the session does not write Spark history logs into the shared `warehouse` bucket.

Wait for the Python `>>>` prompt. All `python` blocks below run at that prompt, where `spark` already exists. Do not type them into Bash or paste Markdown fences. Keep this session open through section 10; terminal C remains available for REST and S3 inspection.

Reduce routine Spark logs so query results are easier to read.

```python
spark.sparkContext.setLogLevel("WARN")
```

## 7. Create the namespace and Iceberg table

Create the namespace, also called a database in Spark SQL. Its location is within the catalog's allowed S3 root. No `IF NOT EXISTS` is used: an unexpected existing resource should be investigated.

```python
spark.sql("CREATE NAMESPACE demo_catalog_temp.demo_database_temp LOCATION 's3://demo-catalog-temp/iceberg/demo_database_temp'").show()
```

List namespaces registered in the demo Polaris catalog.

```python
spark.sql("SHOW NAMESPACES IN demo_catalog_temp").show(truncate=False)
```

Create an Iceberg v2 table with an explicit S3 location. Creating an empty table writes table metadata JSON; it does not yet create a data-bearing snapshot or data manifests.

```python
spark.sql("CREATE TABLE demo_catalog_temp.demo_database_temp.demo_table_temp (id BIGINT, product STRING, amount DECIMAL(10,2)) USING iceberg LOCATION 's3://demo-catalog-temp/iceberg/demo_database_temp/demo_table_temp' TBLPROPERTIES ('format-version'='2')").show()
```

List tables to confirm registration.

```python
spark.sql("SHOW TABLES IN demo_catalog_temp.demo_database_temp").show(truncate=False)
```

Inspect the table definition, provider, and S3 location.

```python
spark.sql("DESCRIBE TABLE EXTENDED demo_catalog_temp.demo_database_temp.demo_table_temp").show(truncate=False)
```

## 8. Write rows and generate Iceberg manifests

Insert two rows. Iceberg writes Parquet data, an Avro manifest, an Avro manifest list, and a new table metadata JSON version, then commits the new metadata pointer through Polaris. Do not hand-write or upload fake manifest files.

```python
spark.sql("INSERT INTO demo_catalog_temp.demo_database_temp.demo_table_temp VALUES (1, 'keyboard', 120.50), (2, 'mouse', 75.00)").show()
```

Read the table through the Polaris catalog. Expect two rows.

```python
spark.sql("SELECT * FROM demo_catalog_temp.demo_database_temp.demo_table_temp ORDER BY id").show()
```

Save the first snapshot ID for a time-travel comparison. Keep this Python variable in the current PySpark session.

```python
first_snapshot = spark.sql("SELECT snapshot_id FROM demo_catalog_temp.demo_database_temp.demo_table_temp.snapshots ORDER BY committed_at").first()[0]
```

Append one row in a separate transaction. This creates another snapshot and its associated metadata files.

```python
spark.sql("INSERT INTO demo_catalog_temp.demo_database_temp.demo_table_temp VALUES (3, 'monitor', 210.25)").show()
```

Read the current table. Expect three rows.

```python
spark.sql("SELECT * FROM demo_catalog_temp.demo_database_temp.demo_table_temp ORDER BY id").show()
```

Read the first snapshot. Expect only rows 1 and 2; the latest table still has all three rows.

```python
spark.sql(f"SELECT * FROM demo_catalog_temp.demo_database_temp.demo_table_temp VERSION AS OF {first_snapshot} ORDER BY id").show()
```

## 9. Inspect manifests, data files, and history

Read Iceberg's snapshot metadata table. Each append has an ID, operation, and `manifest_list` location in the demo bucket.

```python
spark.sql("SELECT committed_at, snapshot_id, parent_id, operation, manifest_list FROM demo_catalog_temp.demo_database_temp.demo_table_temp.snapshots ORDER BY committed_at").show(truncate=False)
```

Inspect the current snapshot's manifest files. `path` points to an Avro manifest in S3; file counts summarize its entries.

```python
spark.sql("SELECT path, length, added_data_files_count, existing_data_files_count, deleted_data_files_count FROM demo_catalog_temp.demo_database_temp.demo_table_temp.manifests").show(truncate=False)
```

Read manifest entries through Iceberg's metadata-table interface, which decodes the Avro records. Each entry points to an actual data file and includes its row count.

```python
spark.sql("SELECT status, snapshot_id, data_file.file_path, data_file.record_count FROM demo_catalog_temp.demo_database_temp.demo_table_temp.entries").show(truncate=False)
```

Inspect current data files. Expect Parquet paths, record counts, and file sizes. An Iceberg table is more than a collection of Parquet files: its metadata defines which files belong to each snapshot.

```python
spark.sql("SELECT file_path, file_format, record_count, file_size_in_bytes FROM demo_catalog_temp.demo_database_temp.demo_table_temp.files").show(truncate=False)
```

Inspect committed table history and which snapshots are ancestors of the current state.

```python
spark.sql("SELECT * FROM demo_catalog_temp.demo_database_temp.demo_table_temp.history").show(truncate=False)
```

The relationships for this Iceberg v2 table are:

```text
Polaris table registration
  -> current metadata/*.metadata.json
     -> snapshot
        -> metadata/snap-*.avro        (manifest list)
           -> metadata/*.avro          (manifest files)
              -> data/*.parquet        (table rows)
```

File names include generated IDs; inspect the actual paths rather than guessing filenames. The table metadata JSON records the schema, locations, snapshot IDs, and manifest-list references. Manifest lists describe manifests, and manifest entries describe data/delete files. Iceberg creates these files consistently as part of its commit process.

## 10. Prove the catalog points to files in SeaweedFS

Switch back to **VM terminal C** while leaving PySpark open. List namespaces through the REST catalog API.

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/demo_catalog_temp/namespaces" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' | python3 -m json.tool
```

List the namespace's tables through the same API.

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/demo_catalog_temp/namespaces/demo_database_temp/tables" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' | python3 -m json.tool
```

Load the table registration and save the response. It contains `metadata-location` and the Iceberg table metadata.

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/demo_catalog_temp/namespaces/demo_database_temp/tables/demo_table_temp" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Polaris-Realm: POLARIS' \
  -o "$DEMO_DIR/table-temp.json"
```

Extract the current metadata JSON object's S3 URI.

```bash
METADATA_URI=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["metadata-location"])' "$DEMO_DIR/table-temp.json")
```

Print it and confirm that it starts with `s3://demo-catalog-temp/iceberg/`.

```bash
printf '%s\n' "$METADATA_URI"
```

Read that exact object directly from SeaweedFS S3 and format the JSON. Compare its snapshot IDs and table UUID with the REST response and Spark output. The final `-` streams the object instead of saving it locally.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 cp "$METADATA_URI" - | python3 -m json.tool
```

List the table's metadata objects. You should find `.metadata.json`, `snap-*.avro` manifest lists, and other `.avro` manifest files. Do not `cat` binary Avro files as text; use section 9's metadata tables to read their contents.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls s3://demo-catalog-temp/iceberg/demo_database_temp/demo_table_temp/metadata/ --recursive
```

List the Parquet data objects separately.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls s3://demo-catalog-temp/iceberg/demo_database_temp/demo_table_temp/data/ --recursive
```

Show the whole demo bucket and its total object count and size. You can also inspect this bucket in the SeaweedFS admin UI at [http://127.0.0.1:19002](http://127.0.0.1:19002), using `team` / `team1234`.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls s3://demo-catalog-temp/ --recursive --human-readable --summarize
```

In the verified run, the two appends produced nine objects: two Parquet data files, three metadata JSON versions, two Avro manifests, and two Avro manifest lists. Generated names and file counts can vary with write planning; use the metadata tables to identify the files actually referenced by each snapshot.

## 11. Keep the demo for the Jupyter notebook

**Do not drop the table, namespace, catalog, or bucket.** [17-0-Jupyter.md](17-0-Jupyter.md) explains how to open [17-1-pypark.ipynb](17-1-pypark.ipynb), which reads this table, its three rows, and its snapshot history before adding separate examples.

In terminal D's PySpark prompt, release this Spark session. Stopping Spark does not remove catalog registrations or stored data.

```python
spark.stop()
```

Leave the Python interpreter.

```python
exit()
```

Return from the container Bash shell to the VM.

```bash
exit
```

Stop the manual forwards with Ctrl+C when finished. Close terminal C to discard its token and temporary client environment. The in-cluster notebook uses Service addresses and does not need these forwards to access Polaris or SeaweedFS.

Retain all of the following for the next lesson:

| Resource | Expected state |
|---|---|
| `demo-catalog-temp` | Contains Iceberg data and metadata objects |
| `demo_catalog_temp` | Registered in Polaris |
| `demo_database_temp` | Contains `demo_table_temp` |
| `demo_table_temp` | Three rows, with two append snapshots |

## 12. Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Polaris serves catalog requests, SeaweedFS serves object requests, and Jupyter hosts the notebook kernel. Do not restart a workload merely to see its logs.

Follow Polaris logs in a separate VM terminal. Ctrl+C stops following logs; it does not stop Polaris.

```bash
oc -n bigdata logs -f deployment/polaris -c polaris --tail=50 --timestamps
```

Read recent SeaweedFS server logs while investigating storage errors.

```bash
oc -n bigdata logs seaweedfs-0 -c seaweedfs --since=10m --timestamps
```

Read Jupyter server and kernel lifecycle logs. Notebook cell output is displayed in the notebook; it is not guaranteed to appear in container logs.

```bash
oc -n bigdata logs spark-master-0 -c jupyter --tail=50 --timestamps
```

## 13. Troubleshoot without resetting the lab

For 401 errors, request a fresh token. For 403 errors, check the realm, catalog privileges, and S3 credentials; an OAuth token and an S3 key are different credentials. For catalog conflicts, stop and inspect the existing resource instead of overwriting it.

For location errors, compare the table location against `allowedLocations`. For connection errors inside Spark or Polaris, use `polaris:8181` and `seaweedfs:8333`; `127.0.0.1` inside a pod is not the VM port-forward. If PySpark cannot find Iceberg classes, use this deployment's Jupyter container with the installed runtime jars.

For failures after a partial run, inspect whether the demo table, namespace, and catalog still exist. Continue from the next missing step after checking existing contents; do not blindly repeat inserts or recreate resources. Preserve the completed demo for lesson 17. Do not reset PostgreSQL, rerun bootstrap, or delete shared PVCs to repeat this exercise.

References: [Polaris 1.7.0 S3 configuration](https://polaris.apache.org/releases/1.7.0/configuration/configuring-polaris-for-production/configuring-aws-s3-cloud-storage-specific/), [Iceberg metadata queries](https://iceberg.apache.org/docs/1.10.0/spark-queries/), and [Iceberg table specification](https://iceberg.apache.org/spec/).

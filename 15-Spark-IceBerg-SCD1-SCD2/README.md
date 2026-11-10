# MySQL binlog CDC with Spark, Iceberg, Polaris and SeaweedFS

Capture product changes, maintain a current dimension with SCD Type 1, and preserve attribute history with SCD Type 2.

| Notebook | Run it to |
|---|---|
| [01 - MySQL binlog capture](01-MySQL-Binlog-Capture.ipynb) | Create an isolated source, apply changes and export committed binlog events |
| [02 - Spark Iceberg SCD1](02-Spark-Iceberg-SCD1.ipynb) | Upload batches to SeaweedFS, preserve CDC history and merge current product attributes |
| [03 - Spark Iceberg SCD2](03-Spark-Iceberg-SCD2.ipynb) | Expire and insert versions, process deletes/reinserts and validate results |

Each notebook defines its own configuration and functions. No helper scripts or local utility modules are required. Captured JSON, CSV and manifests are input data.

## Run the supplied example

1. Keep this folder and its `captured-binlog` subdirectory together in Jupyter.
2. Open notebook 02 with a fresh Spark-enabled kernel. Keep `DB = "scd_workshop"` and `CAPTURE_MODE = "replay"` in its configuration cell. Run all cells, including the final `spark.stop()`.
3. Open notebook 03 in a fresh kernel and run all cells with the same defaults. Inspect current products, historical versions and the validation messages.
4. Repeat notebooks 02 and 03. Compare their counts and fingerprints; the second run must preserve the same results.

This route uses genuine captured binlog events and requires no MySQL password, replication privileges or source configuration. Notebook 01 provides a separate live-capture exercise. Choose one source history per database/namespace.

## Prepare the kernel

Open the notebooks in the existing OpenShift Jupyter environment. Select the Python kernel with PySpark and the installed Spark 3.5 Iceberg runtime, Iceberg AWS bundle, Hadoop AWS and AWS Java SDK JARs. Run notebooks 02 and 03 separately; stop Spark with the final cell before switching notebooks. Each uses one executor core and 512 MB executor memory.

The environment must provide `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `POLARIS_CLIENT_ID` and `POLARIS_CLIENT_SECRET` through the existing credential wiring. Keep their values out of notebook cells and output. Defaults are `http://polaris:8181/api/catalog`, Polaris catalog `training`, `http://seaweedfs:8333` and Spark master `spark://spark-master:7077`.

Use `SCD_DATABASE=scd_workshop` consistently. This selects the MySQL database and Polaris namespace. For another live dataset, choose a new name before starting capture. Keep `SCD_CAPTURE_DIR` identical in all notebooks; it points to the directory containing `start.json` and `batches`, not directly to `batches`. Notebook 01 writes to `lab_data/scd_workshop`. Notebooks 02 and 03 default to `captured-binlog/scd_workshop` for replay; select `CAPTURE_MODE = "live"` to read `lab_data/scd_workshop` instead.

## Capture directly from MySQL

1. Use a fresh database name such as `scd_live` in the configuration cell of all three notebooks, before the paths are derived. Select `CAPTURE_MODE = "live"` in notebooks 02 and 03. Run notebook 01 configuration and dependency installation. Its installation cell adds PyMySQL and the binlog reader to the active kernel.
2. Connect with `MYSQL_HOST=mysql` and `MYSQL_USER=root`; enter the configured password at the prompt. An application account such as `team` needs explicit replication and database privileges before it can perform this exercise. Source setup requires CREATE DATABASE, CREATE TABLE, SELECT, INSERT, UPDATE and DELETE; the reader requires REPLICATION CLIENT and REPLICATION SLAVE.
3. Verify binary logging, ROW format, FULL row images, FULL row metadata and disabled transaction compression. Follow the notebook setup notes if verification fails. Configure the source before writing changes; do not restart a shared database from the notebook.
4. Run setup, Change 0 and capture. Run notebook 02, stop Spark, then run notebook 03 and stop Spark.
5. Repeat for Changes 1 through 7. Alternatively, run all of notebook 01 before running 02 and 03. Intermediate product versions remain in the captured history.
6. Repeat capture without a new source change. It must report no new batch.

Keep one writer and one capture process active. The capture checks that the source position remains unchanged during its read. Keep the source binlogs until capture finishes. Do not reuse a checkpoint after recreating its source database.

## Replay the supplied capture

Use `captured-binlog/scd_workshop` beside these notebooks when direct MySQL capture is unavailable. It contains decoded events captured from the MySQL binary log, including before/after images, source log positions and batch manifests. It is not a raw MySQL binary-log file and cannot be passed to `mysqlbinlog`.

Skip notebook 01. Keep the following settings in the configuration cell of **both** notebooks 02 and 03; these are the supplied defaults:

```python
DB = "scd_workshop"
CAPTURE_MODE = "replay"
```

Keep the configuration cell's database name unchanged; the manifests identify that source database. Run 02 completely, stop Spark, then run 03 completely. Neither notebook requires a connection to MySQL for replay. Use a separate clean environment or the existing identical capture for a repeat run; different source histories must not share the same namespace and raw prefix.

## Copy a capture into OpenShift

Copy the complete directory, preserving file names and relative paths. For an existing capture, replace `CAPTURE_SOURCE` with the directory containing `start.json` and `batches`. Run in a shell with the existing OpenShift CLI login:

```bash
POD=$(oc -n bigdata get pod -l app=spark-master -o jsonpath='{.items[0].metadata.name}')
oc -n bigdata exec "$POD" -c jupyter -- mkdir -p /workspace/user_notebooks/15-Spark-IceBerg-SCD1-SCD2/captured-binlog/scd_workshop
oc -n bigdata cp CAPTURE_SOURCE/. "$POD":/workspace/user_notebooks/15-Spark-IceBerg-SCD1-SCD2/captured-binlog/scd_workshop/ -c jupyter
```

To copy between hosts, first transfer the directory with `scp -r CAPTURE_SOURCE HOST:DESTINATION`, then use `oc cp` from that host. Replace `HOST` and `DESTINATION` with the connection and path for the environment. OpenShift's internal MySQL service name resolves inside the cluster.

Directory layout:

```text
captured-binlog/scd_workshop/
  start.json
  batches/
    batch_000001/
      product_cdc_001.json
      orders_001.csv
      manifest.json
    batch_000002/
      ...
```

`start.json` records the original source position. Each manifest records the next position and high-water marks. Copy these files for provenance. Replay reads immutable batches; resuming capture also requires the original source identity and available binlogs. Never point notebook 01 at a copied checkpoint from another source.

## Follow the data

Raw objects: `s3://warehouse/scd-capture/scd_workshop/batch_*/...`.

Iceberg namespace: `polaris.scd_workshop`, with its location under `s3://warehouse/iceberg/scd_workshop`. Polaris resolves table metadata; SeaweedFS stores object bytes. `s3a://` in Spark raw reads and `s3://` in Iceberg locations address the same bucket through their respective clients.

| Table | Purpose |
|---|---|
| `product_changes` | Every product CDC event, identified by `cdc_id` |
| `order_history` | Order lifecycle events, identified by `event_id` |
| `latest_orders` | One latest business state per order |
| `dim_product_scd1` | One current row per existing product |
| `dim_product_scd2` | Attribute versions with `valid_from`, `valid_to`, `is_current` |
| `scd2_applied_events` | Ledger preventing duplicate event application |

SCD1 selects the last product event by source sequence before MERGE. SCD2 processes all events in sequence. Validity uses half-open intervals `[valid_from, valid_to)`. A monotonically increasing capture time distinguishes events sharing a binlog timestamp; `binlog_time` preserves that original timestamp. Order resolution uses business event time, breaking ties with event ID. Actual selling prices determine booked value.

## Verify results and replay

After all source changes, product 1 has current attributes Standard / Silver / 90.00 and five historical versions. A timestamp-only update creates no extra version. Product 3 is deleted and reinserted, giving two lifetimes and one current row.

| Result | Expected |
|---|---:|
| Product CDC events / applied-event ledger | 10 |
| Current products in SCD1 | 3 |
| Order history / latest orders | 16 / 9 |
| Historical product versions in SCD2 | 8 |
| Current product versions in SCD2 | 3 |

Run notebooks 02 and 03 again against the same capture. Counts, values and historical intervals must remain unchanged. Notebook 03 checks version uniqueness, current-row uniqueness, interval validity, nonoverlap, complete CDC coverage, SCD1/SCD2 current agreement, late order events and equal-time tie-breaking.

The raw uploader compares object bytes before reuse and publishes each manifest last. It rejects a different capture at an existing raw key. Use complete batches, one uploader and one SCD writer. The SCD2 example uses multiple commits per event; inspect results after the notebook finishes. For large datasets, replace the per-event collection with an appropriately designed distributed pipeline.

## Troubleshoot

| Symptom | Action |
|---|---|
| No batches found | Check `LAB_DIR`, copy layout and completed manifests |
| Capture access denied | Use an account with source DDL/DML and replication privileges |
| Metadata verification fails | Configure FULL metadata before writes, or use supplied replay data |
| Polaris 401/403 | Check the existing identity and grants |
| S3 read or write fails | Check SeaweedFS endpoint, credential wiring and bucket access |
| Spark cannot start | Stop another notebook session and use a fresh Spark-enabled kernel |
| Existing raw object differs | Keep the original capture; use an isolated environment for another history |
| Duplicate or overlapping versions | Stop concurrent writers and inspect source sequence and event IDs |

Do not delete warehouse objects manually. Choose a new database/namespace for a new live capture. Preserve the existing batches for replay.

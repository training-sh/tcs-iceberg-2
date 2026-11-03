# OpenShift Spark Streaming Data Lake

Two student notebooks port the HDFS ecommerce examples to the existing Polaris / SeaweedFS / Iceberg stack. No image changes or new services are required.

| File | Purpose |
|---|---|
| [01-bronze-to-silver.ipynb](01-bronze-to-silver.ipynb) | CSV arrivals, validation, exact-line deduplication, insert-only Iceberg MERGE |
| [02-silver-to-country-totals.ipynb](02-silver-to-country-totals.ipynb) | Stream Silver commits, calculate lifetime distinct orders and amounts by country |
| Matching `.md` files | Readable notebook code and explanations, including Mermaid architecture diagrams |
| [SPARK-STREAMING-PRESENTATION.md](SPARK-STREAMING-PRESENTATION.md) | Detailed presentation with speaker notes and 25 teaching sections |
| [VALIDATION.md](VALIDATION.md) | VM test procedure and measured results |
| [verification-results.json](verification-results.json) | Machine-readable test evidence |
| [upload-csv.py](upload-csv.py) | Upload one original CSV through the signed SeaweedFS S3 API |

The sources were `D45_SparkStream/D451-Ecomm-Bronze-To-Silver-Stream.ipynb` and `D45_SparkStream/D452-Ecomm-Analytics.ipynb`. The second notebook now computes lifetime country totals as requested, rather than the old hourly country/product aggregates.

## Run in Jupyter

Open the existing OpenShift Jupyter service and create a fresh Python 3 kernel for each notebook. The existing Python 3 kernel can import PySpark through the image's PYTHONPATH. Connection settings are included in the notebooks; credentials come from the existing Jupyter environment.

The VM originally advertised only one Spark worker core. Two simultaneous notebook drivers each need one core and a 512 MiB executor. The validation raises `SPARK_WORKER_CORES` to 2 within the worker pod's existing 2 CPU / 2 GiB limit and existing 1 GiB Spark executor memory budget. The image is unchanged. On another clone, an administrator can apply the same prerequisite with `oc -n bigdata set env statefulset/spark-worker SPARK_WORKER_CORES=2`, then wait for its rollout before class. This restarts the worker, so apply it before students run jobs. Stop each query and use the final `spark.stop()` cell to release its executor after class.

1. Extract the supplied `ecomm-stream-small (3).zip` outside the watched prefix.
2. Upload one unchanged CSV to bucket `warehouse`, key prefix `ecomm/bronze/`.
3. Open notebook 01, check the constants, and run its definition cells in order.
4. Run its **A. Process once** cell. Inspect the output.
5. Open notebook 02, check its constants, run definitions and its **A. Process once** cell.
6. Upload another CSV and repeat the Once cell in notebook 01, then notebook 02.
7. For the live demonstration, run **B. Run every 15 seconds** in both notebooks, upload additional CSVs and inspect the results.
8. Drain upstream with `query.processAllAvailable()`, then downstream in the other notebook. Stop both with `query.stop()` when finished.

**A and B are alternatives. Do not use Run All:** it would start the recurring query and immediately run later drain/stop cells. Select the desired trigger cells explicitly. Wait for Once to terminate before starting recurring mode. Reuse checkpoints when switching modes.

## Upload through the SeaweedFS S3 API

Run the provided `upload-csv.py` from a terminal inside the existing Jupyter container. It uses Python's standard library to send one SigV4 authenticated S3 PUT request. No package installation or image change is required. The example assumes the original CSV is already present at `/workspace/uploads/first.csv`. It preserves bytes; the delivery object name may be different from the local filename.

```bash
python3 upload-csv.py /workspace/uploads/first.csv ecomm/bronze/delivery-001.csv
```

Use a fresh object name for the next delivery. To demonstrate replay protection, upload the same original file under another fresh delivery name. Keep uploads serial for a clear class demonstration. There is no notebook cell that modifies the original files or seeds classroom data automatically.

The helper's default endpoint is `http://seaweedfs:8333`, internal OpenShift DNS reachable inside the cluster. From the VM host, use an existing port-forward to the SeaweedFS S3 service and set the `S3_ENDPOINT` environment variable accordingly. It also needs the existing AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables; never paste credentials into a student notebook. Do not confuse the SeaweedFS filer UI endpoint with the S3 API port 8333.

Upload the first CSV before defining notebook 01's source so the prefix exists. Empty S3 folders need a marker; the notebook itself does not create or rewrite input.

## Storage and semantics

Original uploads: `s3a://warehouse/ecomm/bronze`. Silver and country_totals: `s3://warehouse/iceberg/ecomm/...`, matching the existing Polaris training catalog's allowed location. Checkpoints: `s3a://warehouse/ecomm/checkpoints/...`.

LineID identifies an exact cleaned CSV row. Repeated identical source lines are collapsed even if legitimate; the source has no unique line ID. Changed values become new identities. Cancellations and invalid sales are filtered. TotalOrders means distinct InvoiceNo per country. TotalAmount is accepted sales excluding returns.

Silver must remain append-only. Its insert-only MERGE is tested for append snapshot behavior on the installed Iceberg version. Do not add matched updates/deletes or skip unsupported snapshots silently. Gold recomputes all committed Silver totals per notification and merges absolute values. This makes retries simple and exact for a small dataset, at the cost of a full Silver scan.

Use one writer per table. For separate student exercises, change namespace, table names, physical locations and checkpoints together; stay under the catalog's allowed Iceberg root. A changed location constant does not relocate an already registered table. Do not delete a shared checkpoint to reset another student's work.

## One-time method names

Spark has `trigger(once=True)`, `awaitTermination()` and `processAllAvailable()`. It has no `processOnce()` API. The requested one-time mode is a separate notebook cell using Once. Spark 3.5 Once may ignore maxFilesPerTrigger; recurring mode respects the one-file admission limit. See the presentation for the difference from AvailableNow.

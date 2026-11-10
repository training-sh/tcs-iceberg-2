# HTTP REST to Spark, Iceberg, Polaris and SeaweedFS

Start a simulated Python API, pull its paginated data through HTTP, and store raw responses and typed datasets in Iceberg. Polaris provides the catalog; SeaweedFS stores the physical objects.

| Notebook | Work |
|---|---|
| [01 - Python REST API server](01-Python-REST-API-Server.ipynb) | Start a read-only API, inspect pagination and verify success/error responses |
| [02 - HTTP to Spark and Bronze](02-HTTP-to-Spark-and-Iceberg-Bronze.ipynb) | Pull pages on the driver, demonstrate worker HTTP GETs and write Iceberg Bronze |
| [03 - Typed Iceberg tables](03-REST-Bronze-to-Typed-Iceberg.ipynb) | Parse nested responses, preserve types/nulls, compare extraction methods and query the lake |

Each notebook contains its complete code and configuration. No shared helper modules, separate server scripts, external API accounts or local input files are required. The source API uses Python standard-library modules. This exercise does not use MySQL, CDC, HDFS, Hive or Kafka.

## Prepare the environment

Use the existing OpenShift Jupyter environment with the Spark 3.5 kernel and installed Iceberg Spark runtime, Iceberg AWS bundle, Hadoop AWS and AWS Java SDK JARs. Spark master/worker, Polaris and SeaweedFS must be running. Stop other Spark notebook sessions before starting this exercise.

Notebook 01 is an ordinary Python kernel running a background HTTP server. Notebooks 02 and 03 each start one Spark application with one executor core and 512 MB driver/executor heap. Each Spark notebook contains its complete Polaris and S3 configuration.

The existing environment supplies `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `POLARIS_CLIENT_ID` and `POLARIS_CLIENT_SECRET`. Keep their values out of notebook cells and output. The underlying Polaris catalog is `training`; the Spark alias is `polaris`. The existing bucket is `warehouse`.

## Run the notebooks

1. Open notebook 01 and run all cells. Confirm the API tests pass. **Keep its kernel running.** The server continues on a background thread after the cells finish.
2. Open notebook 02 in a separate Spark-enabled kernel in the same Jupyter environment. Run every cell. Confirm seven stored response pages and six unique orders from worker HTTP requests. Run the final `spark.stop()` cell.
3. Open notebook 03 in a fresh Spark-enabled kernel. Run all cells and inspect the typed tables, comparison checks, country revenue, physical files and fingerprints. Stop Spark with the final cell.
4. Repeat the workflow with the same settings. Re-running notebook 01 restarts only its own server object. Counts and fingerprints must remain identical. Iceberg snapshots and physical file names may change.
5. Stop the API after HTTP extraction is finished. Run the optional shutdown code shown at the end of notebook 01, or shut down that kernel.

Notebook 03 reads persisted Iceberg Bronze and does not call the API. The API can be stopped after notebook 02 completes. Do not stop the API kernel while driver or worker HTTP requests are still running.

If a cell fails, stop that notebook's Spark session, check service health and rerun from the top in a fresh kernel. Keep the API kernel separate from Spark kernel cleanup.

## Follow the API

Default address: `http://spark-master:18717`. The server binds inside the existing Spark/Jupyter Pod. Its headless DNS name resolves to that Pod, allowing both notebook drivers and Spark workers to connect directly. A new public Route or Service is not needed. This is a small workshop server with no authentication or TLS; it is not a production API deployment.

If using another reachable endpoint, set `REST_API_BASE_URL` in each kernel's environment before running configuration, or edit `API_BASE` consistently. The API contract and country filters must remain compatible. Worker `localhost` refers to the worker itself and will not reach the notebook API.

| Request | Response |
|---|---|
| `GET /health` | Status and immutable dataset version |
| `GET /v1/products?page=1&page_size=2` | Paginated product records |
| `GET /v1/customers?page=1&page_size=2` | Paginated customer records |
| `GET /v1/orders?page=1&page_size=2` | Paginated order records |
| `GET /v1/orders?country=IN&page=1&page_size=2` | Orders filtered by a disjoint country key |
| Invalid page or country | HTTP 400 with JSON error |
| Unknown endpoint | HTTP 404 with JSON error |

Each page includes `dataset_version`, `entity`, `page`, `total`, `next_page` and `items`. Follow `next_page` until it is null. Products and customers each have two pages; orders have three pages at the default size of two records. The source contains 4 products, 4 customers and 6 orders.

Money is represented as a JSON string such as `"25.00"`. One product category and one customer email are null. A product name contains a comma. Spark casts money to DECIMAL rather than using floating-point arithmetic.

## Understand the two HTTP approaches

The configured Spark 3.5 runtime has no generic REST SQL reader installed. The notebooks use actual Python HTTP clients, then Spark DataFrames and JSON parsing. They do not invent `spark.read.http` or claim an HTTP response envelope is a directly supported JSON file path.

**Driver pull:** fetch all pages with Python `urllib`, validate pagination and create a small DataFrame of full response JSON strings. This is the easier pattern for small or rate-limited sources. It buffers the extract on the driver; larger workloads should persist bounded batches to durable storage rather than collect an unbounded source.

**Worker pull:** create a Spark RDD of disjoint country filters, then use `mapPartitions` to perform read-only HTTP GET requests from workers. Spark parses the returned record strings with an explicit JSON schema. Two partitions cap the request plan at two concurrent tasks; the configured one-core application can execute them sequentially. The small result is cached while it is checked and written.

HTTP requests have five-second timeouts, up to three attempts for selected transient failures, and at most 100 pages per filtered extract. HTTP 400 and 404 fail immediately. Selected 429 and 5xx responses retry, with a bounded delay. Source version, page sequence, totals and unique record IDs are checked.

Spark tasks can be retried, so worker GETs may occur more than once. Use read-only, repeatable endpoints and disjoint source filters. Do not apply non-idempotent POST writes inside Spark tasks. This simulated source is immutable; a changing real API needs a version/snapshot contract for consistent pagination. Avoid embedding access tokens in serialized task code.

## Inspect Bronze and typed tables

Keep `LAB = "http_rest_lake"` consistent in notebooks 02 and 03. For an independent target dataset, choose a fresh LAB in both notebooks before paths are derived.

| Iceberg table | Rows | Meaning |
|---|---:|---|
| `polaris.http_rest_lake.api_pages` | 7 | One complete response envelope per entity/page |
| `polaris.http_rest_lake.orders_parallel_http` | 6 | Orders extracted by Spark worker HTTP GETs |
| `polaris.http_rest_lake.products` | 4 | Typed product records parsed from Bronze |
| `polaris.http_rest_lake.customers` | 4 | Typed customer records parsed from Bronze |
| `polaris.http_rest_lake.orders` | 6 | Typed order records parsed from Bronze |

Each table has a separate location under `s3://warehouse/iceberg/http_rest_lake/<table>/`. The complete Bronze response envelope is reserialized with sorted JSON keys and stored as a column in an Iceberg table, not as separate local JSON files. It preserves response content rather than the exact wire-byte formatting. Polaris publishes Iceberg metadata references; SeaweedFS stores metadata, manifests and Parquet objects.

Notebook 03 uses `from_json` with an explicit nested schema and explodes the response `items` array. It verifies nulls, unique IDs and decimal casts. It then compares the resulting orders against the worker HTTP extraction in both directions.

Every write replaces the table's full current snapshot instead of appending duplicate batches. Each table commits independently; this example is a single-writer pipeline, not an atomic multi-table transaction. Retained Iceberg snapshots may continue to reference older objects. Keep object cleanup within Iceberg management operations.

Inspect the stored pages and physical files:

```sql
SELECT entity, page, response_json
FROM polaris.http_rest_lake.api_pages
ORDER BY entity, page;

SELECT * FROM polaris.http_rest_lake.orders ORDER BY order_id;
SELECT file_path, record_count FROM polaris.http_rest_lake.orders.files;
SELECT snapshot_id, operation FROM polaris.http_rest_lake.orders.snapshots;
```

Target file paths must begin with `s3://warehouse/iceberg/http_rest_lake/`, not a local or HDFS path.

## Verify the outcome

| Country | Orders | Revenue |
|---|---:|---:|
| IN | 3 | 85.00 |
| UK | 2 | 55.00 |
| US | 1 | 50.00 |
| Total | 6 | 190.00 |

Revenue uses the order quantity and selling price. Joining orders to products and customers must retain six orders. The final fingerprints cover all five current Iceberg datasets. Repeated runs must match row counts and hashes, although snapshot IDs and file names can differ.

## Troubleshoot

| Symptom | Action |
|---|---|
| HTTP connection refused | Run notebook 01 and keep its kernel alive; check port 18717 |
| Address already in use | Stop the known API kernel using this port before restarting it |
| Driver succeeds but workers cannot connect | Use the reachable Pod/headless service address, not localhost; check network policy |
| Service name fails to resolve | Check cluster DNS and retry from a fresh Spark kernel after it recovers |
| Pagination or version check fails | Stop processing and investigate the source contract; do not publish an incomplete extract |
| Spark already active | Stop the previous Spark session and use a fresh kernel |
| Polaris authorization or location error | Check existing identity, grants and allowed warehouse root |
| S3 access or timeout error | Check SeaweedFS readiness, DNS and credential wiring |

References: [Spark JSON data sources](https://spark.apache.org/docs/3.5.6/sql-data-sources-json.html), [Spark data sources](https://spark.apache.org/docs/3.5.6/sql-data-sources.html), [Python HTTP server](https://docs.python.org/3/library/http.server.html), [Python urllib requests](https://docs.python.org/3/library/urllib.request.html).

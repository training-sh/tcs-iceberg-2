# MySQL JDBC to Hive, HDFS and Polaris Iceberg

Insert source data into MySQL, extract it through Spark JDBC, store it in three HDFS layouts, then rewrite it into Iceberg tables on SeaweedFS through Polaris.

Run the notebooks in order. Each contains its complete configuration and code; no helper scripts, shared setup notebooks or lesson-specific imports are needed. No binlogs, CDC reader, replication privileges or local input files are required.

| Notebook | Work |
|---|---|
| [01 - MySQL seed and JDBC read](01-MySQL-Seed-and-JDBC-Read.ipynb) | Create three dedicated tables, insert data and read it using both Spark JDBC APIs |
| [02 - JDBC to Hive and HDFS](02-JDBC-to-Hive-and-HDFS.ipynb) | Write partitioned external Hive Parquet, direct HDFS CSV and direct HDFS JSON |
| [03 - HDFS to Polaris Iceberg](03-Hive-and-HDFS-to-Polaris-Iceberg.ipynb) | Read the three HDFS sources, rewrite them to Iceberg on SeaweedFS, reconcile and query |

## Prepare the environment

Use the existing OpenShift Jupyter environment and its Spark-enabled Python kernel. The runtime needs Spark 3.5, the MySQL Connector/J JAR, Spark Hive support, the matching Iceberg Spark runtime and Iceberg AWS bundle. These are supplied by the existing Spark image. Do not install another PySpark version into the kernel.

MySQL, the NameNode, a DataNode, the Hive metastore, Spark master/worker, Polaris and SeaweedFS must be running. HiveServer2 and YARN are not required: Spark uses the Hive metastore directly and runs on its standalone workers.

Run these commands from an OpenShift-authenticated terminal if the existing HDFS and metastore workloads are scaled down:

```bash
oc -n bigdata scale statefulset/namenode statefulset/datanode deployment/hive-metastore --replicas=1
oc -n bigdata rollout status statefulset/namenode --timeout=180s
oc -n bigdata rollout status statefulset/datanode --timeout=180s
oc -n bigdata rollout status deployment/hive-metastore --timeout=180s
```

Prepare the dedicated exercise parent once with the NameNode's filesystem administrator identity. Leave other directories unchanged:

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /workshop/16-mysql-hdfs-iceberg
oc -n bigdata exec namenode-0 -- hdfs dfs -chown spark:spark /workshop/16-mysql-hdfs-iceberg
```

This parent is already prepared in the configured environment. The notebook creates its own child paths below it. Use one writer and stop other Spark notebook sessions before starting. Each notebook uses one executor core and 512 MB executor memory.

## Configure the notebooks

Keep these values consistent in all three configuration cells:

```python
MYSQL_DB = "training"
TABLE_PREFIX = "lake16_"
LAB = "mysql_hdfs_2"
```

`TABLE_PREFIX` isolates the MySQL source tables. `LAB` names the Hive database, the HDFS exercise child directory and the Polaris namespace. For a separate exercise, choose a fresh prefix and LAB in all three notebooks before their paths and identifiers are derived. Use the existing MySQL database unless another one has been provisioned.

| Connection | Default | Override |
|---|---|---|
| MySQL | `mysql:3306`, database `training` | `MYSQL_HOST`, `MYSQL_PORT`; edit `MYSQL_DB` in the cell |
| MySQL credentials | Existing `DB_USER` and `DB_PASSWORD` | `MYSQL_USER`, `MYSQL_PASSWORD`; otherwise enter the password when prompted |
| Spark | `spark://spark-master:7077` | `SPARK_MASTER_URL` |
| HDFS | `hdfs://namenode:9000` | `WORKSHOP_HDFS_URI` |
| Hive metastore | `thrift://hive-metastore:9083` | `HIVE_METASTORE_URI` |
| Polaris | `http://polaris:8181/api/catalog`, catalog `training` | `POLARIS_URI` |
| SeaweedFS | `http://seaweedfs:8333`, bucket `warehouse` | `S3_ENDPOINT` |

The `team` MySQL account needs CREATE, SELECT, INSERT and UPDATE in `training`. Root and replication privileges are unnecessary. Notebook 03 does not connect to MySQL and does not need its password.

Notebook 03 reads `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `POLARIS_CLIENT_ID` and `POLARIS_CLIENT_SECRET` from the existing credential environment. Do not print their values, `JDBC_OPTIONS` or the Spark configuration. Exports in another terminal do not change the environment of an already running notebook kernel.

All HDFS paths use an explicit `hdfs://` URI. The notebook deliberately uses `WORKSHOP_HDFS_URI` instead of the image's generic `HDFS_URI=file:///` or an outdated external HDFS address. Short service names resolve inside the cluster; override them if using another namespace.

## Run the exercise

1. Open notebook 01 in a fresh kernel. Run every cell. Confirm 4 products, 4 customers, 6 orders and an order value of 190.00. Run the final `spark.stop()` cell.
2. Open notebook 02 in a fresh kernel and run every cell. Inspect the three Hive country partitions and the printed HDFS file paths. Confirm all three stored datasets exactly match MySQL. Stop Spark.
3. Open notebook 03 in a fresh kernel and run every cell. Inspect the Iceberg files and snapshots, reconciliation checks and country revenue. Stop Spark.
4. Repeat 01, 02 and 03 with the same settings. Current rows, nulls, totals and fingerprints must match the first run. Iceberg snapshot IDs and physical file names may change.

If a cell fails, stop Spark before retrying and run the notebook from the top in a fresh kernel. Do not continue from a later transformation with incomplete state.

The notebooks preserve their tables and files for inspection. Notebook 01 uses primary-key upserts for its fixed seed records. Notebook 02 overwrites only the three dedicated exercise directories. Notebook 03 replaces each complete Iceberg table snapshot. Keep source data unchanged while reading: multiple JDBC connections are not a coordinated transaction snapshot.

## Inspect the MySQL source

| MySQL table | Rows | Meaning |
|---|---:|---|
| `training.lake16_products_2` | 4 | Product name, category and decimal list price |
| `training.lake16_customers_2` | 4 | Customer name, country and nullable email |
| `training.lake16_orders_2` | 6 | Order, customer and product IDs, quantity, selling price and country |

A product name contains a comma. One product category and one customer email are null. These values check whether CSV quoting and null handling survive storage and conversion.

Notebook 01 uses a driver-side Java JDBC connection to execute CREATE TABLE and INSERT statements. Spark's JDBC reader then extracts the actual MySQL rows; it does not substitute an in-memory copy of the seed data.

Products and customers use `spark.read.jdbc(...)`. Orders use `spark.read.format("jdbc").options(...).load()` with `order_id` bounds and two JDBC partitions. Bounds calculate partition strides; they do not filter source rows. Use a WHERE clause in a subquery when filtering is required. Keep the number of partitions small enough for the source database.

## Compare the HDFS approaches

| Dataset | HDFS location under the exercise root | Format | Hive registration |
|---|---|---|---|
| Orders | `orders_parquet/country=IN`, `country=UK`, `country=US` | Partitioned Parquet | `spark_catalog.mysql_hdfs_2.orders_external_2` |
| Products | `products_csv` | CSV with header, quoting and explicit null marker | None |
| Customers | `customers_json` | One JSON object per line, including null fields | None |

The full root is `hdfs://namenode:9000/workshop/16-mysql-hdfs-iceberg/mysql_hdfs_2`.

Orders are written first with `partitionBy("country")`. `CREATE EXTERNAL TABLE ... STORED AS PARQUET LOCATION ...` registers those files in Hive. `MSCK REPAIR TABLE` registers the partition directories. Hive stores schema, location and partition metadata; HDFS stores the bytes. The EXTERNAL property identifies separate data ownership; registering the table does not copy the files.

Products and customers are directory-only datasets. Spark reads them with a path and an explicit schema, without looking up a Hive table. Spark output paths are directories with part files and success markers, not a single CSV or JSON file. The CSV writer and reader use matching header, quote/escape and null-marker settings. The JSON reader uses an explicit schema to keep types stable.

Inspect the external table from Spark SQL:

```sql
DESCRIBE EXTENDED spark_catalog.mysql_hdfs_2.orders_external_2;
SHOW PARTITIONS spark_catalog.mysql_hdfs_2.orders_external_2;
SELECT * FROM spark_catalog.mysql_hdfs_2.orders_external_2 WHERE country = 'IN';
```

## Convert to Iceberg on SeaweedFS

Notebook 03 reads orders by Hive table name and the other datasets directly by HDFS path. It writes three new Iceberg datasets:

| Iceberg table | Rows | SeaweedFS location |
|---|---:|---|
| `polaris.mysql_hdfs_2.orders_2` | 6 | `s3://warehouse/iceberg/mysql_hdfs_2/orders_2` |
| `polaris.mysql_hdfs_2.products_2` | 4 | `s3://warehouse/iceberg/mysql_hdfs_2/products_2` |
| `polaris.mysql_hdfs_2.customers_2` | 4 | `s3://warehouse/iceberg/mysql_hdfs_2/customers_2` |

`polaris` is the Spark catalog alias; the underlying Polaris catalog is `training`. Polaris publishes Iceberg metadata references. SeaweedFS stores the Iceberg metadata and Parquet objects. The source Hive registration and HDFS files remain available. This conversion rewrites the data into S3; it is not an in-place migration or a zero-copy import of HDFS files.

Orders use country partitioning in Iceberg. The small product and customer tables are unpartitioned. An empty CTAS establishes each table's schema and location. `writeTo(...).overwrite(lit(True))` commits a complete replacement snapshot, so reruns do not append duplicates. Retained snapshots can still reference older files; do not delete S3 objects manually.

Query Iceberg data and metadata:

```sql
SELECT * FROM polaris.mysql_hdfs_2.orders_2 ORDER BY order_id;
SELECT file_path, record_count FROM polaris.mysql_hdfs_2.orders_2.files;
SELECT snapshot_id, operation FROM polaris.mysql_hdfs_2.orders_2.snapshots;
```

The `files` query must show paths under `s3://warehouse/iceberg/mysql_hdfs_2/orders_2/`, not HDFS paths.

## Check the results

| Country | Orders | Revenue |
|---|---:|---:|
| IN | 3 | 85.00 |
| UK | 2 | 55.00 |
| US | 1 | 50.00 |
| Total | 6 | 190.00 |

Revenue uses order quantity multiplied by the order selling price. Joining products and customers must retain exactly six orders. Both directions of `exceptAll` compare source and target values, including duplicates. The final fingerprints compare current business rows across repeated runs; physical file names and snapshot IDs are not part of that comparison.

## Troubleshoot

| Symptom | Action |
|---|---|
| MySQL access denied | Check the existing account and its database grants; replication access is not needed |
| MySQL driver class missing | Select the existing Spark kernel/image with Connector/J |
| HDFS connection refused | Confirm NameNode/DataNode readiness and `WORKSHOP_HDFS_URI` |
| HDFS permission denied | Prepare only the dedicated exercise parent for the Spark filesystem identity |
| Hive connection refused | Confirm the existing metastore deployment and `HIVE_METASTORE_URI` |
| No Hive partitions | Confirm the country directories exist and rerun `MSCK REPAIR TABLE` |
| Existing external table has another location | Select a fresh LAB instead of overwriting another table's files |
| CSV nulls or commas differ | Keep the explicit schema and matching CSV options |
| Polaris authorization or location error | Check existing identity, grants and allowed `warehouse/iceberg` root |
| S3 read/write fails | Check SeaweedFS readiness and existing credential wiring |
| A service name temporarily fails to resolve | Confirm cluster DNS is healthy, stop Spark, then retry from a fresh kernel |
| Spark already active | Stop the previous session and start a fresh kernel |

Choose fresh exercise names for independent datasets. Do not drop unrelated MySQL tables, remove shared HDFS roots or delete Iceberg objects outside the catalog.

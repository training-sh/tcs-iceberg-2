# 01 — Trino with Iceberg, Polaris and SeaweedFS

**Outcome:** create a small ecommerce dataset directly in Iceberg Bronze, publish completed sales to Silver, build daily Gold totals, and inspect Iceberg files and snapshots. Read [the introduction](00-trino-introduction.md) first. Open the Trino CLI and apply its session limits. This exercise does not require MySQL or Spark.

## 1. Follow a table lookup

``` 
sequenceDiagram
    participant T as Trino
    participant P as Polaris REST catalog
    participant S as SeaweedFS S3
    T->>P: Resolve table using existing catalog identity
    P-->>T: Current Iceberg metadata location
    T->>S: Read metadata, manifests and selected data files
    S-->>T: Object bytes
    Note over T,S: Writes create objects; catalog commit publishes new metadata
```

`iceberg_polaris.trino_ecomm_s01.silver_order_lines` contains a Trino catalog alias, Polaris namespace and table name. The configured underlying Polaris catalog is `training`. The URI `s3://warehouse/iceberg/...` identifies bucket objects accessed through SeaweedFS's configured S3 endpoint on port **8333**. It is not a Windows path or VM directory.

Use existing credentials and configuration. Do not print connection properties, obtain tokens or edit catalog files. Namespace discovery can succeed while an S3 read fails: catalog authorization and object access are different checks.

## 2. Create an isolated namespace

Inspect first:

```sql
SHOW SCHEMAS FROM iceberg_polaris;
```

The exact namespace `trino_ecomm_s01` should be absent for a new run. Create it under the existing allowed Iceberg root:

```sql
CREATE SCHEMA iceberg_polaris.trino_ecomm_s01
WITH (location = 's3://warehouse/iceberg/trino_ecomm_s01');
```

If permissions or location validation fail, review existing grants and allowed locations. Do not create another Polaris catalog or weaken policies. Each table below has its own nonoverlapping object location.

## 3. Bronze: create the ecommerce seed directly in Iceberg

Create nine order lines using VALUES. Keep completed, pending and cancelled orders in Bronze. Unit prices use one reporting currency, CU. This dataset matches the MySQL source introduced in the next exercise.

```sql
CREATE TABLE iceberg_polaris.trino_ecomm_s01.bronze_order_lines
WITH (
    format = 'PARQUET',
    format_version = 2,
    location = 's3://warehouse/iceberg/trino_ecomm_s01/bronze_order_lines'
) AS
SELECT CAST(line_id AS BIGINT) AS line_id,
       CAST(order_id AS BIGINT) AS order_id,
       CAST(customer_id AS BIGINT) AS customer_id,
       CAST(product_id AS BIGINT) AS product_id,
       order_date, order_status, customer_name, country, product_name, category,
       quantity, CAST(unit_price AS DECIMAL(12,2)) AS unit_price,
       CAST(quantity * unit_price AS DECIMAL(18,2)) AS line_amount
FROM (VALUES
    (1, 1001, 1, 101, DATE '2026-11-01', 'COMPLETED', 'Asha', 'IN', 'Keyboard', 'Accessories', 2, DECIMAL '25.00'),
    (2, 1001, 1, 102, DATE '2026-11-01', 'COMPLETED', 'Asha', 'IN', 'Mouse', 'Accessories', 1, DECIMAL '15.00'),
    (3, 1002, 2, 101, DATE '2026-11-01', 'COMPLETED', 'Ravi', 'IN', 'Keyboard', 'Accessories', 1, DECIMAL '25.00'),
    (4, 1002, 2, 103, DATE '2026-11-01', 'COMPLETED', 'Ravi', 'IN', 'Cable', 'Connectivity', 2, DECIMAL '10.00'),
    (5, 1003, 3, 102, DATE '2026-11-02', 'COMPLETED', 'Emma', 'UK', 'Mouse', 'Accessories', 2, DECIMAL '15.00'),
    (6, 1004, 1, 103, DATE '2026-11-02', 'CANCELLED', 'Asha', 'IN', 'Cable', 'Connectivity', 3, DECIMAL '10.00'),
    (7, 1005, 4, 101, DATE '2026-11-02', 'COMPLETED', 'Liam', 'US', 'Keyboard', 'Accessories', 1, DECIMAL '25.00'),
    (8, 1005, 4, 103, DATE '2026-11-02', 'COMPLETED', 'Liam', 'US', 'Cable', 'Connectivity', 1, DECIMAL '10.00'),
    (9, 1006, 2, 102, DATE '2026-11-03', 'PENDING', 'Ravi', 'IN', 'Mouse', 'Accessories', 1, DECIMAL '15.00')
) AS seed(line_id, order_id, customer_id, product_id, order_date, order_status,
          customer_name, country, product_name, category, quantity, unit_price);
```

This is **CTAS**, CREATE TABLE AS SELECT. Trino evaluates the VALUES rows, writes Parquet and Iceberg metadata to SeaweedFS, and registers the table through Polaris. No external source database is needed.

```sql
SELECT order_status, count(*) AS lines,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS amount
FROM iceberg_polaris.trino_ecomm_s01.bronze_order_lines
GROUP BY order_status
ORDER BY order_status;
```

| order_status | lines | amount |
|---|---:|---:|
| CANCELLED | 1 | 30.00 |
| COMPLETED | 7 | 175.00 |
| PENDING | 1 | 15.00 |

Bronze has **9 lines / 220.00 CU** across all statuses. Reading it back is the first actual Iceberg object-read check in this course.

## 4. Silver: publish valid completed sales

```sql
CREATE TABLE iceberg_polaris.trino_ecomm_s01.silver_order_lines
WITH (
    format = 'PARQUET',
    format_version = 2,
    partitioning = ARRAY['order_date'],
    location = 's3://warehouse/iceberg/trino_ecomm_s01/silver_order_lines'
) AS
SELECT line_id, order_id, customer_id, product_id, order_date,
       customer_name, country, product_name, category,
       quantity, unit_price, line_amount
FROM iceberg_polaris.trino_ecomm_s01.bronze_order_lines
WHERE order_status = 'COMPLETED'
  AND line_id IS NOT NULL
  AND order_id IS NOT NULL
  AND customer_id IS NOT NULL
  AND product_id IS NOT NULL
  AND order_date IS NOT NULL
  AND country IS NOT NULL
  AND quantity > 0
  AND unit_price >= 0;
```

Partitioning by DATE illustrates date pruning. For nine source lines it is a teaching choice, not a performance recommendation. Excessive partitioning produces small files. The seed has unique line IDs. Check Bronze line IDs before repeating this pattern with other data: value filtering does not deduplicate keys.

```sql
SELECT count(*) AS lines, count(DISTINCT order_id) AS orders,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines;

SELECT line_id, count(*) AS copies
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
GROUP BY line_id HAVING count(*) > 1;
```

Expected: **7 lines / 4 orders / 175.00 revenue**, then no duplicate rows. This table is separate from the streaming lesson's `polaris.ecomm.silver`.

## 5. Gold: daily country totals

```sql
CREATE TABLE iceberg_polaris.trino_ecomm_s01.gold_daily_sales
WITH (
    format = 'PARQUET',
    format_version = 2,
    location = 's3://warehouse/iceberg/trino_ecomm_s01/gold_daily_sales'
) AS
SELECT order_date, country,
       count(DISTINCT order_id) AS completed_orders,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
GROUP BY order_date, country;

SELECT * FROM iceberg_polaris.trino_ecomm_s01.gold_daily_sales
ORDER BY order_date, country;
```

| order_date | country | completed_orders | revenue |
|---|---|---:|---:|
| 2026-11-01 | IN | 2 | 110.00 |
| 2026-11-02 | UK | 1 | 30.00 |
| 2026-11-02 | US | 1 | 35.00 |

Gold is a stored table, not a live view. It stays unchanged until refreshed in lesson 03. Distinct orders are measured at day/country grain. Summing these counts is safe here because each order has exactly one date and country.

## 6. Inspect physical files and metadata

```sql
SHOW CREATE TABLE iceberg_polaris.trino_ecomm_s01.silver_order_lines;

SELECT file_path, file_format, record_count, file_size_in_bytes
FROM iceberg_polaris.trino_ecomm_s01."silver_order_lines$files"
ORDER BY file_path;

SELECT committed_at, snapshot_id, parent_id, operation
FROM iceberg_polaris.trino_ecomm_s01."silver_order_lines$snapshots"
ORDER BY committed_at, snapshot_id;

SELECT made_current_at, snapshot_id, parent_id, is_current_ancestor
FROM iceberg_polaris.trino_ecomm_s01."silver_order_lines$history"
ORDER BY made_current_at;
```

Double quotes keep the `$` metadata-table suffix inside one identifier. Paths should be inside the exercise's Silver location in bucket `warehouse`, using Parquet files. File names, counts, snapshot IDs and commit times vary. `$files` describes current files, `$snapshots` retained versions, and `$history` changes to the current snapshot.

For this fresh insert-only table, current data-file record counts should total seven. After row-level deletes or updates, physical file record counts may differ from logical row counts because delete files can affect visibility.

Record the current Silver snapshot ID **before lesson 03**:

```sql
SELECT snapshot_id
FROM iceberg_polaris.trino_ecomm_s01."silver_order_lines$history"
WHERE is_current_ancestor
ORDER BY made_current_at DESC
LIMIT 1;
```

The ID is a table version, not a credential. Save it for time travel. Do not manually edit or delete objects through the SeaweedFS UI; Iceberg commits keep files, metadata and catalog references consistent.

## 7. Compare Silver and Gold totals

```sql
SELECT 'silver' AS dataset, CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
UNION ALL
SELECT 'gold', CAST(sum(revenue) AS DECIMAL(18,2))
FROM iceberg_polaris.trino_ecomm_s01.gold_daily_sales;
```

Expected: **175.00** in both layers. Keep these tables. The next exercise creates matching MySQL source tables without recreating Bronze, Silver or Gold.

## Checkpoint and troubleshooting

| Layer | Rows | Amount |
|---|---:|---|
| Bronze | 9 | All statuses: 220.00 |
| Silver | 7 | Completed: 175.00 |
| Gold | 3 | Day/country groups: 175.00 |

| Symptom | Inspect |
|---|---|
| Polaris 401/403 | Existing identity, roles and grants |
| Location rejected | Allowed root in the existing Polaris catalog |
| S3 signature/access error | Existing credentials, region and path-style settings |
| S3 connection refused | SeaweedFS readiness and S3 port 8333, not the filer UI |
| Table exists or location populated | Reused identifier or interrupted CTAS |
| Totals differ | Duplicate keys, filters or concurrent source changes |

A failed create can leave unreferenced objects. Record the path and error without secrets. Use a fresh identifier for retries instead of deleting objects manually. Do not run orphan cleanup against shared storage.

**Discussion:** Which service stores Parquet? Which resolves table metadata? Why does Gold become stale? How is a snapshot different from a partition?

Continue to [MySQL and federation](02-trino-mysql-ecommerce.md).

# 03 — Incremental orders, replay-safe MERGE and federation

**Outcome:** add one order, prove replay does not duplicate it, refresh Gold, join Iceberg facts with live MySQL dimensions, reconcile results and time travel. Complete [the MySQL exercise](02-trino-mysql-ecommerce.md). Keep the same names and reapply session limits after reconnecting.

This is a manually triggered batch pipeline, not streaming or CDC. It does not start Spark. MySQL inserts and Iceberg writes commit independently. If a stage fails, earlier commits remain; inspect state and resume the failed stage.

## 1. Confirm the starting checkpoint

```sql
SELECT count(*) AS lines, count(DISTINCT order_id) AS orders,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines;

SELECT count(*) AS groups,
       CAST(sum(revenue) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.gold_daily_sales;
```

Expected: Silver **7 / 4 / 175.00**, Gold **3 groups / 175.00**. If already at 225.00, inspect before proceeding. Record the pre-change Silver snapshot ID as shown in exercise 01.

## 2. Receive another MySQL order

Emma orders two keyboards at 25.00 CU each on 3 November. INSERT SELECT skips its stable key on serial reruns:

```sql
INSERT INTO mysql.trino_ecomm.trino_s01_orders
    (order_id, customer_id, order_date, order_status)
SELECT BIGINT '1007', BIGINT '3', DATE '2026-11-03', 'COMPLETED'
WHERE NOT EXISTS (
    SELECT 1 FROM mysql.trino_ecomm.trino_s01_orders WHERE order_id = 1007
);

INSERT INTO mysql.trino_ecomm.trino_s01_order_items
    (line_id, order_id, product_id, quantity, unit_price)
SELECT BIGINT '10', BIGINT '1007', BIGINT '101', 2, DECIMAL '25.00'
WHERE NOT EXISTS (
    SELECT 1 FROM mysql.trino_ecomm.trino_s01_order_items WHERE line_id = 10
);

SELECT * FROM mysql.trino_ecomm.trino_s01_orders WHERE order_id = 1007;
SELECT * FROM mysql.trino_ecomm.trino_s01_order_items WHERE line_id = 10;
```

Expected: exactly one row per query with the values above. The existence checks do not correct a conflicting row or guarantee concurrency safety. Stop if an existing key has different values. Rerun exercise 02's source uniqueness checks. Production ingestion needs enforced keys and defined event ordering.

## 3. Merge the new extract into Bronze

```sql
MERGE INTO iceberg_polaris.trino_ecomm_s01.bronze_order_lines t
USING (
    SELECT i.line_id, o.order_id, o.customer_id, i.product_id,
           o.order_date, o.order_status,
           c.customer_name, c.country, p.product_name, p.category,
           i.quantity, i.unit_price,
           CAST(i.quantity * i.unit_price AS DECIMAL(18,2)) AS line_amount
    FROM mysql.trino_ecomm.trino_s01_order_items i
    JOIN mysql.trino_ecomm.trino_s01_orders o ON i.order_id = o.order_id
    JOIN mysql.trino_ecomm.trino_s01_customers c ON o.customer_id = c.customer_id
    JOIN mysql.trino_ecomm.trino_s01_products p ON i.product_id = p.product_id
    WHERE o.order_id = 1007
) s
ON t.line_id = s.line_id
WHEN NOT MATCHED THEN INSERT (
    line_id, order_id, customer_id, product_id, order_date, order_status,
    customer_name, country, product_name, category,
    quantity, unit_price, line_amount
) VALUES (
    s.line_id, s.order_id, s.customer_id, s.product_id, s.order_date, s.order_status,
    s.customer_name, s.country, s.product_name, s.category,
    s.quantity, s.unit_price, s.line_amount
);

SELECT count(*) AS lines,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS all_status_amount
FROM iceberg_polaris.trino_ecomm_s01.bronze_order_lines;
```

Expected: **10 lines / 270.00** across all statuses. MySQL is the source; Iceberg is the target. The insert-only clause keeps loaded lines unchanged. It handles immutable new lines, not later quantity changes, cancellations, refunds or source deletes. Reusing a line key for a correction requires a different pipeline contract.

## 4. Merge completed lines into Silver

Revisit the ten Bronze rows. The stable `line_id` prevents inserting the existing seven sales again:

```sql
MERGE INTO iceberg_polaris.trino_ecomm_s01.silver_order_lines t
USING (
    SELECT line_id, order_id, customer_id, product_id, order_date,
           customer_name, country, product_name, category,
           quantity, unit_price, line_amount
    FROM iceberg_polaris.trino_ecomm_s01.bronze_order_lines
    WHERE order_status = 'COMPLETED'
      AND line_id IS NOT NULL AND order_id IS NOT NULL
      AND customer_id IS NOT NULL AND product_id IS NOT NULL
      AND order_date IS NOT NULL AND country IS NOT NULL
      AND quantity > 0 AND unit_price >= 0
) s
ON t.line_id = s.line_id
WHEN NOT MATCHED THEN INSERT (
    line_id, order_id, customer_id, product_id, order_date,
    customer_name, country, product_name, category,
    quantity, unit_price, line_amount
) VALUES (
    s.line_id, s.order_id, s.customer_id, s.product_id, s.order_date,
    s.customer_name, s.country, s.product_name, s.category,
    s.quantity, s.unit_price, s.line_amount
);

SELECT count(*) AS lines, count(DISTINCT order_id) AS orders,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines;
```

Expected: **8 lines / 5 orders / 225.00**. Rerun only the Bronze and Silver MERGE blocks once. Results must remain **10 Bronze lines**, **8 Silver lines** and **225.00** Silver revenue. Replay safety means stable logical contents; do not require a particular snapshot count after no-op writes.

MERGE does not enforce permanent uniqueness. Duplicate unmatched source rows can both be inserted; multiple source rows matching one existing target can fail. Validate keys before merging rather than choosing arbitrary duplicate rows.

## 5. Refresh Gold with absolute totals

Gold is still at 175.00 because source and Silver commits did not refresh it:

```sql
SELECT CAST(sum(revenue) AS DECIMAL(18,2)) AS stale_gold_revenue
FROM iceberg_polaris.trino_ecomm_s01.gold_daily_sales;
```

Recompute each group. Assign absolute totals instead of adding them to existing values:

```sql
MERGE INTO iceberg_polaris.trino_ecomm_s01.gold_daily_sales t
USING (
    SELECT order_date, country,
           count(DISTINCT order_id) AS completed_orders,
           CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
    FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
    GROUP BY order_date, country
) s
ON t.order_date = s.order_date AND t.country = s.country
WHEN MATCHED AND (
    t.completed_orders IS DISTINCT FROM s.completed_orders
    OR t.revenue IS DISTINCT FROM s.revenue
) THEN UPDATE SET completed_orders = s.completed_orders, revenue = s.revenue
WHEN NOT MATCHED THEN INSERT (order_date, country, completed_orders, revenue)
VALUES (s.order_date, s.country, s.completed_orders, s.revenue);

SELECT * FROM iceberg_polaris.trino_ecomm_s01.gold_daily_sales
ORDER BY order_date, country;
```

| order_date | country | completed_orders | revenue |
|---|---|---:|---:|
| 2026-11-01 | IN | 2 | 110.00 |
| 2026-11-02 | UK | 1 | 30.00 |
| 2026-11-02 | US | 1 | 35.00 |
| 2026-11-03 | UK | 1 | 50.00 |

Rerun Gold MERGE: four groups and **225.00** must remain. The matched branch supports recalculation of existing groups; this new-order example adds a new group. The algorithm assumes append-only Silver. If a group disappears entirely after deletes or moves, its old Gold row remains. Handling removals requires an explicit delete/rebuild strategy and is not implemented here.

## 6. Federate lake facts and live MySQL dimensions

```sql
SELECT c.customer_id, c.customer_name, c.country,
       count(DISTINCT s.order_id) AS completed_orders,
       CAST(sum(s.line_amount) AS DECIMAL(18,2)) AS revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines s
JOIN mysql.trino_ecomm.trino_s01_customers c ON s.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.country
ORDER BY revenue DESC, c.customer_id;
```

| customer_id | customer_name | country | completed_orders | revenue |
|---:|---|---|---:|---:|
| 3 | Emma | UK | 2 | 80.00 |
| 1 | Asha | IN | 1 | 65.00 |
| 2 | Ravi | IN | 1 | 45.00 |
| 4 | Liam | US | 1 | 35.00 |

This reads SeaweedFS-backed Iceberg facts and live MySQL dimensions. Country here is the customer's **current MySQL country**. Silver contains country captured at extraction. A later customer move would make these different business meanings. Historical reporting needs the captured value or a historical dimension.

Find the top product per captured country:

```sql
WITH product_sales AS (
    SELECT country, product_name,
           CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
    FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
    GROUP BY country, product_name
), ranked AS (
    SELECT country, product_name, revenue,
           row_number() OVER (
               PARTITION BY country ORDER BY revenue DESC, product_name
           ) AS position
    FROM product_sales
)
SELECT country, product_name, revenue
FROM ranked WHERE position = 1
ORDER BY country;
```

Expected: **IN / Keyboard / 75.00**, **UK / Keyboard / 50.00**, **US / Keyboard / 25.00**. Product name breaks ties. Use dense_rank on revenue alone if every tied winner should appear.

## 7. Reconcile the stages

```sql
WITH source_totals AS (
    SELECT count(*) AS lines, count(DISTINCT o.order_id) AS orders,
           CAST(sum(i.quantity * i.unit_price) AS DECIMAL(18,2)) AS revenue
    FROM mysql.trino_ecomm.trino_s01_orders o
    JOIN mysql.trino_ecomm.trino_s01_order_items i ON o.order_id = i.order_id
    WHERE o.order_status = 'COMPLETED'
), lake_totals AS (
    SELECT count(*) AS lines, count(DISTINCT order_id) AS orders,
           CAST(sum(line_amount) AS DECIMAL(18,2)) AS revenue
    FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
), gold_totals AS (
    SELECT sum(completed_orders) AS orders,
           CAST(sum(revenue) AS DECIMAL(18,2)) AS revenue
    FROM iceberg_polaris.trino_ecomm_s01.gold_daily_sales
)
SELECT s.lines = l.lines AS line_count_matches,
       s.orders = l.orders AND l.orders = g.orders AS order_count_matches,
       s.revenue = l.revenue AND l.revenue = g.revenue AS revenue_matches
FROM source_totals s CROSS JOIN lake_totals l CROSS JOIN gold_totals g;
```

Expected: **true / true / true** with other writers stopped. Summed Gold order counts work here because each order belongs to one day/country group.

Also compare rows; totals alone can hide offsetting errors. Expected: no rows from either check:

```sql
WITH expected AS (
    SELECT line_id, order_id, line_amount
    FROM iceberg_polaris.trino_ecomm_s01.bronze_order_lines
    WHERE order_status = 'COMPLETED'
), actual AS (
    SELECT line_id, order_id, line_amount
    FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
)
SELECT 'missing_from_silver' AS issue, line_id, order_id, line_amount
FROM (SELECT * FROM expected EXCEPT SELECT * FROM actual) missing
UNION ALL
SELECT 'unexpected_in_silver', line_id, order_id, line_amount
FROM (SELECT * FROM actual EXCEPT SELECT * FROM expected) extra;

SELECT line_id, count(*) AS copies
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
GROUP BY line_id HAVING count(*) > 1;
```

EXCEPT compares sets, so duplicates need their own check. The expected set assumes this valid seed; general reconciliation must use Silver's full quality policy.

## 8. Time travel

```sql
SELECT committed_at, snapshot_id, operation
FROM iceberg_polaris.trino_ecomm_s01."silver_order_lines$snapshots"
ORDER BY committed_at, snapshot_id;
```

The following is a **template**. Replace `PRE_LOAD_SNAPSHOT_ID` with the numeric ID saved before lesson 03, without quotes. Do not paste the placeholder unchanged:

```sql
SELECT count(*) AS old_lines,
       CAST(sum(line_amount) AS DECIMAL(18,2)) AS old_revenue
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines
FOR VERSION AS OF PRE_LOAD_SNAPSHOT_ID;
```

Expected: the retained pre-load snapshot returns **7 / 175.00**; normal SELECT returns **8 / 225.00**. Time travel does not roll back the current table or rewind MySQL, another table or catalog permissions. Avoid expiring snapshots during the exercise; expiration can remove required history.

For service controls, worker scaling and cleanup, use [operations](04-trino-operations.md). For browser access and optional password authentication, use [web UI and access](05-trino-web-ui-and-access.md).

## Assessment

1. Explain Bronze's 270.00 versus completed revenue of 225.00.
2. Show replay row counts and explain the role of line_id.
3. Explain why Gold assigns totals instead of adding them.
4. Identify current versus captured country in the two reports.
5. Describe changes required for cancellations and corrections.
6. Explain why cross-catalog SQL does not imply a transaction across systems.

Extension: design correction events with increasing source versions and explicit deletion semantics. Discuss the MERGE contract before executing more writes; a unique key alone does not establish which out-of-order event is newest.

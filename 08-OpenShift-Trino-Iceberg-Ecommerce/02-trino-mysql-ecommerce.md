# 02 — MySQL ecommerce and Trino federation

**Outcome:** create a small ecommerce source in MySQL and query it through Trino. Learn catalog/schema/table names, joins, order-level aggregation, decimal arithmetic and query planning. Read the [README](README.md), especially naming and rerun rules. Use the connection procedure in [the introduction](00-trino-introduction.md).

Complete [the Iceberg exercise](01-iceberg-polaris-seaweedfs.md) first. Its tables already contain the baseline sales. This exercise creates equivalent operational source tables in a separate MySQL database and queries both stores through Trino. Keep the existing Iceberg tables.

## 1. Create the dedicated MySQL database

Open a host terminal on the Linux desktop:

```bash
cd ~/openshift/08-OpenShift-Trino-Iceberg-Ecommerce
export PATH="$HOME/.crc/bin/oc:$PATH"
oc exec -it -n bigdata mysql-0 -- mysql -h 127.0.0.1 -u root -p
```

Enter `team1234` at the prompt. At the **MySQL prompt**, inspect the existing databases and application account, then create the exercise database:

```mysql
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'team';
CREATE DATABASE trino_ecomm;
GRANT ALL PRIVILEGES ON trino_ecomm.* TO 'team'@'%';
exit
```

The grant targets the existing `team` account at host `%`; use the host returned by the account inspection if it differs. Do not modify Hive's database. If `trino_ecomm` already exists, inspect its tables and reuse it only for these exercises; skip CREATE DATABASE rather than dropping it. Each run uses a distinct table suffix inside this database.

Open the Trino CLI, apply the session limits from the introduction and confirm the new schema is visible:

```bash
oc exec -it -n bigdata trino-0 -- trino --server http://localhost:8080 --user team
```

```sql
SHOW SCHEMAS FROM mysql;
```

Expected: `trino_ecomm`. All remaining SQL blocks use **Trino syntax**, not the MySQL prompt.

## 2. Understand catalog.schema.table

| Part of `mysql.trino_ecomm.trino_s01_orders` | Meaning |
|---|---|
| `mysql` | Trino catalog using the MySQL connector |
| `trino_ecomm` | Dedicated MySQL exercise database exposed as a schema |
| `trino_s01_orders` | Exercise table |

Creating a table through this catalog creates a **MySQL table**. Connector support determines which SQL operations are available. Inspect before writing:

```sql
SHOW TABLES FROM mysql.trino_ecomm LIKE 'trino_s01_%';
```

Expected: no matching tables for a new identifier. `_` is a LIKE wildcard, so inspect any returned names. If the intended names exist, use a fresh identifier or review optional cleanup; do not overwrite them.

## Optional: inspect MySQL directly

Run in a separate host terminal to connect with the application account:

```bash
oc exec -it -n bigdata mysql-0 -- mysql -h 127.0.0.1 -u team -p trino_ecomm
```

Enter `team1234` at the password prompt. To inspect with the administrator account instead:

```bash
oc exec -it -n bigdata mysql-0 -- mysql -h 127.0.0.1 -u root -p trino_ecomm
```

Enter `team1234`. At the MySQL prompt, use `SHOW TABLES;` or `SELECT DATABASE(), CURRENT_USER();`, then `exit`. Run the remaining exercise SQL in the **Trino CLI**, not in the MySQL client: the SQL uses Trino three-part names and syntax.

## 3. Create four source tables

These statements create course data, not Kubernetes configuration. The teaching tables omit enforced keys and indexes so the lab can use Trino throughout. Production systems should enforce business keys; the checks below detect duplicates here.

```sql
CREATE TABLE mysql.trino_ecomm.trino_s01_customers (
    customer_id BIGINT,
    customer_name VARCHAR(40),
    country VARCHAR(2)
);

CREATE TABLE mysql.trino_ecomm.trino_s01_products (
    product_id BIGINT,
    product_name VARCHAR(40),
    category VARCHAR(20)
);

CREATE TABLE mysql.trino_ecomm.trino_s01_orders (
    order_id BIGINT,
    customer_id BIGINT,
    order_date DATE,
    order_status VARCHAR(12)
);

CREATE TABLE mysql.trino_ecomm.trino_s01_order_items (
    line_id BIGINT,
    order_id BIGINT,
    product_id BIGINT,
    quantity INTEGER,
    unit_price DECIMAL(12,2)
);
```

The item table records the checkout price. Revenue should use this historical price rather than a product's current list price.

## 4. Seed the source exactly once

```sql
INSERT INTO mysql.trino_ecomm.trino_s01_customers VALUES
    (1, 'Asha', 'IN'),
    (2, 'Ravi', 'IN'),
    (3, 'Emma', 'UK'),
    (4, 'Liam', 'US');

INSERT INTO mysql.trino_ecomm.trino_s01_products VALUES
    (101, 'Keyboard', 'Accessories'),
    (102, 'Mouse', 'Accessories'),
    (103, 'Cable', 'Connectivity');

INSERT INTO mysql.trino_ecomm.trino_s01_orders VALUES
    (1001, 1, DATE '2026-11-01', 'COMPLETED'),
    (1002, 2, DATE '2026-11-01', 'COMPLETED'),
    (1003, 3, DATE '2026-11-02', 'COMPLETED'),
    (1004, 1, DATE '2026-11-02', 'CANCELLED'),
    (1005, 4, DATE '2026-11-02', 'COMPLETED'),
    (1006, 2, DATE '2026-11-03', 'PENDING');

INSERT INTO mysql.trino_ecomm.trino_s01_order_items VALUES
    (1, 1001, 101, 2, DECIMAL '25.00'),
    (2, 1001, 102, 1, DECIMAL '15.00'),
    (3, 1002, 101, 1, DECIMAL '25.00'),
    (4, 1002, 103, 2, DECIMAL '10.00'),
    (5, 1003, 102, 2, DECIMAL '15.00'),
    (6, 1004, 103, 3, DECIMAL '10.00'),
    (7, 1005, 101, 1, DECIMAL '25.00'),
    (8, 1005, 103, 1, DECIMAL '10.00'),
    (9, 1006, 102, 1, DECIMAL '15.00');
```

Each INSERT commits separately. If interrupted, inspect counts and resume carefully. Repeating this block duplicates rows; the seed load is not replay-safe.

## 5. Validate before joining

```sql
SELECT 'customers' AS entity, count(*) AS rows
FROM mysql.trino_ecomm.trino_s01_customers
UNION ALL
SELECT 'products', count(*) FROM mysql.trino_ecomm.trino_s01_products
UNION ALL
SELECT 'orders', count(*) FROM mysql.trino_ecomm.trino_s01_orders
UNION ALL
SELECT 'order_items', count(*) FROM mysql.trino_ecomm.trino_s01_order_items;
```

Expected: **4 customers, 3 products, 6 orders, 9 lines**. UNION ALL output order is not guaranteed.

Check uniqueness for all four business keys. Expected: no rows.

```sql
SELECT 'customer_id' AS key_name, customer_id AS key_value, count(*) AS copies
FROM mysql.trino_ecomm.trino_s01_customers GROUP BY customer_id HAVING count(*) > 1
UNION ALL
SELECT 'product_id', product_id, count(*)
FROM mysql.trino_ecomm.trino_s01_products GROUP BY product_id HAVING count(*) > 1
UNION ALL
SELECT 'order_id', order_id, count(*)
FROM mysql.trino_ecomm.trino_s01_orders GROUP BY order_id HAVING count(*) > 1
UNION ALL
SELECT 'line_id', line_id, count(*)
FROM mysql.trino_ecomm.trino_s01_order_items GROUP BY line_id HAVING count(*) > 1;
```

Check references and values. Expected: both counts are zero.

```sql
SELECT count(*) AS invalid_lines
FROM mysql.trino_ecomm.trino_s01_order_items i
LEFT JOIN mysql.trino_ecomm.trino_s01_orders o ON i.order_id = o.order_id
LEFT JOIN mysql.trino_ecomm.trino_s01_products p ON i.product_id = p.product_id
WHERE i.line_id IS NULL OR o.order_id IS NULL OR p.product_id IS NULL
   OR i.quantity IS NULL OR i.quantity <= 0
   OR i.unit_price IS NULL OR i.unit_price < 0;

SELECT count(*) AS orders_without_customer
FROM mysql.trino_ecomm.trino_s01_orders o
LEFT JOIN mysql.trino_ecomm.trino_s01_customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
```

Stop on any failure. Duplicate dimension keys multiply joined rows and inflate revenue.

## 6. Calculate completed sales

```sql
SELECT o.order_id, c.customer_name, c.country,
       CAST(sum(i.quantity * i.unit_price) AS DECIMAL(18,2)) AS order_amount
FROM mysql.trino_ecomm.trino_s01_orders o
JOIN mysql.trino_ecomm.trino_s01_customers c ON o.customer_id = c.customer_id
JOIN mysql.trino_ecomm.trino_s01_order_items i ON o.order_id = i.order_id
WHERE o.order_status = 'COMPLETED'
GROUP BY o.order_id, c.customer_name, c.country
ORDER BY o.order_id;
```

| order_id | customer_name | country | order_amount |
|---:|---|---|---:|
| 1001 | Asha | IN | 65.00 |
| 1002 | Ravi | IN | 45.00 |
| 1003 | Emma | UK | 30.00 |
| 1005 | Liam | US | 35.00 |

There are four completed orders and seven completed lines. Counting joined rows as orders would be wrong. Group item-level data using distinct order IDs:

```sql
SELECT c.country,
       count(DISTINCT o.order_id) AS completed_orders,
       CAST(sum(i.quantity * i.unit_price) AS DECIMAL(18,2)) AS revenue
FROM mysql.trino_ecomm.trino_s01_orders o
JOIN mysql.trino_ecomm.trino_s01_customers c ON o.customer_id = c.customer_id
JOIN mysql.trino_ecomm.trino_s01_order_items i ON o.order_id = i.order_id
WHERE o.order_status = 'COMPLETED'
GROUP BY c.country
ORDER BY c.country;
```

| country | completed_orders | revenue |
|---|---:|---:|
| IN | 2 | 110.00 |
| UK | 1 | 30.00 |
| US | 1 | 35.00 |

Completed revenue is **175.00 CU**. Including cancelled and pending orders incorrectly produces **220.00 CU**. DECIMAL avoids binary floating-point rounding for these calculations.

## 7. Inspect a query plan

```sql
EXPLAIN
SELECT order_id, order_date
FROM mysql.trino_ecomm.trino_s01_orders
WHERE order_date = DATE '2026-11-01';
```

Find the table scan and date predicate. Supported operations may be pushed toward MySQL. Exact plan text varies; do not assume all expressions or joins are pushed down. EXPLAIN ANALYZE actually runs the query, so ordinary EXPLAIN is enough here.

For browser monitoring, use [web UI and access](05-trino-web-ui-and-access.md).

## Checkpoint and troubleshooting

| Symptom | Action |
|---|---|
| `oc: command not found` | Export the CRC CLI path shown above |
| Connection refused | Check readiness and resolve the unavailable prerequisite |
| MySQL access denied | Review existing catalog permissions; do not print credentials |
| Table exists | Inspect it; use a fresh identifier rather than overwriting it |
| Revenue exceeds 175 | Check duplicate keys, repeated seeds and status filter |
| Timeout or memory failure | Confirm only the tiny exercise tables are queried; do not raise server limits |

Keep both MySQL and Iceberg tables. Compare the baseline totals without copying the data again:

```sql
SELECT 'mysql' AS source,
       CAST(sum(i.quantity * i.unit_price) AS DECIMAL(18,2)) AS revenue
FROM mysql.trino_ecomm.trino_s01_orders o
JOIN mysql.trino_ecomm.trino_s01_order_items i ON o.order_id = i.order_id
WHERE o.order_status = 'COMPLETED'
UNION ALL
SELECT 'iceberg', CAST(sum(line_amount) AS DECIMAL(18,2))
FROM iceberg_polaris.trino_ecomm_s01.silver_order_lines;
```

Expected: **175.00** from each source. Continue to [incremental loading and federation](03-incremental-federation.md).

**Discussion:** Why is a query user name different from database authentication? Why must joined order counts use DISTINCT? Which table owns historical selling price?

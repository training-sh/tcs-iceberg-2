-- Replace RUN_SCHEMA with the run ID printed by the completed compute Job.
SELECT count(*) AS sellers,
       sum(distinct_orders) AS seller_order_pairs,
       sum(item_rows) AS item_rows,
       sum(merchandise_value) AS merchandise_value,
       sum(delivered_orders) AS delivered_orders,
       sum(canceled_orders) AS canceled_orders,
       sum(other_orders) AS other_orders,
       sum(on_time_items) AS on_time_items,
       sum(late_items) AS late_items,
       sum(missing_handoff_items) AS missing_handoff_items
FROM iceberg_polaris.RUN_SCHEMA.seller_activity;

SELECT seller_state, seller_count, item_rows
FROM iceberg_polaris.RUN_SCHEMA.seller_geography
ORDER BY seller_state;

SELECT count(*) AS differing_activity_rows FROM (
    (SELECT * FROM hive.RUN_SCHEMA.seller_activity
     EXCEPT SELECT * FROM iceberg_polaris.RUN_SCHEMA.seller_activity)
    UNION ALL
    (SELECT * FROM iceberg_polaris.RUN_SCHEMA.seller_activity
     EXCEPT SELECT * FROM hive.RUN_SCHEMA.seller_activity)
);

SELECT count(*) AS differing_geography_rows FROM (
    (SELECT * FROM hive.RUN_SCHEMA.seller_geography
     EXCEPT SELECT * FROM iceberg_polaris.RUN_SCHEMA.seller_geography)
    UNION ALL
    (SELECT * FROM iceberg_polaris.RUN_SCHEMA.seller_geography
     EXCEPT SELECT * FROM hive.RUN_SCHEMA.seller_geography)
);

SELECT DISTINCT "$path" AS hdfs_file
FROM hive.RUN_SCHEMA.seller_activity
LIMIT 2;

SELECT file_path, record_count
FROM iceberg_polaris.RUN_SCHEMA."seller_activity$files";

SELECT status, input_items
FROM iceberg_polaris.RUN_SCHEMA.verification;

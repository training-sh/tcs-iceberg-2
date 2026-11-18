CREATE TABLE IF NOT EXISTS {lake}.bronze_order_lines
WITH (
    format = 'PARQUET',
    format_version = 2,
    location = '{location}/bronze_order_lines'
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
          customer_name, country, product_name, category, quantity, unit_price)

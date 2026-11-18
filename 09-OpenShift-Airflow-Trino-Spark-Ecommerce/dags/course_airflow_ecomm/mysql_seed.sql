CREATE DATABASE IF NOT EXISTS {database};
GRANT SELECT ON {database}.* TO 'team'@'%';
USE {database};

CREATE TABLE IF NOT EXISTS customers (
    customer_id BIGINT PRIMARY KEY,
    customer_name VARCHAR(40),
    country VARCHAR(2)
);

CREATE TABLE IF NOT EXISTS products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(40),
    category VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT,
    order_date DATE,
    order_status VARCHAR(12)
);

CREATE TABLE IF NOT EXISTS order_items (
    line_id BIGINT PRIMARY KEY,
    order_id BIGINT,
    product_id BIGINT,
    quantity INT,
    unit_price DECIMAL(12,2)
);

-- The fixture commits as one transaction. Primary keys make a repeat safe.
START TRANSACTION;
INSERT INTO customers VALUES
    (1,'Asha','IN'), (2,'Ravi','IN'), (3,'Emma','UK'), (4,'Liam','US')
ON DUPLICATE KEY UPDATE customer_id = customer_id;

INSERT INTO products VALUES
    (101,'Keyboard','Accessories'), (102,'Mouse','Accessories'), (103,'Cable','Connectivity')
ON DUPLICATE KEY UPDATE product_id = product_id;

INSERT INTO orders VALUES
    (1001,1,'2026-11-01','COMPLETED'), (1002,2,'2026-11-01','COMPLETED'),
    (1003,3,'2026-11-02','COMPLETED'), (1004,1,'2026-11-02','CANCELLED'),
    (1005,4,'2026-11-02','COMPLETED'), (1006,2,'2026-11-03','PENDING'),
    (1007,3,'2026-11-03','COMPLETED')
ON DUPLICATE KEY UPDATE order_id = order_id;

INSERT INTO order_items VALUES
    (1,1001,101,2,25.00), (2,1001,102,1,15.00), (3,1002,101,1,25.00),
    (4,1002,103,2,10.00), (5,1003,102,2,15.00), (6,1004,103,3,10.00),
    (7,1005,101,1,25.00), (8,1005,103,1,10.00), (9,1006,102,1,15.00),
    (10,1007,101,2,25.00)
ON DUPLICATE KEY UPDATE line_id = line_id;
COMMIT;

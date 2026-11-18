# Ecommerce prerequisites

The advanced DAGs require matching MySQL and Iceberg course data: eight accepted lines, five completed orders, four daily/country report groups and 225.00 revenue. The initial seven-line/four-order/175.00 Iceberg seed is not enough.

For the additional lessons, use `bash publish-course.sh --lessons`, then run `python3 prepare-ecommerce-data.py` while those DAGs are idle. This command prepares their shared MySQL and Iceberg baseline. Expected final marker `ECOMMERCE_DATA_READY`.

This command requires the preceding Trino Iceberg lesson's Bronze table. It does not drop existing tables or overwrite conflicting source keys. If the seed is absent or differs, stop and complete or inspect that prerequisite. Do not lower expected totals to make a check pass.

The `prepare` task in lesson 02 checks these inputs and creates only its output namespace; it does not seed MySQL. The independent Airflow introduction does not need this ecommerce data.

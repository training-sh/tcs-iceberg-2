# 04: Cleanup only this exercise run

Cleanup is optional after inspecting the results. It removes this run's data and identities; afterward its saved credentials no longer work. Do not remove the existing training catalog, bootstrap principal or shared warehouse bucket. Save any results you need first. The cleanup steps have not been executed; see VALIDATION for test details.

## 1. Remove the exercise tables and namespaces

Open a fresh Python notebook beside `private-lab.json`. Copy the connection cell from the developer notebook but set `ROLE = 'admin'` before starting Spark. Do not reuse a viewer SparkContext. Then run:

```python
import re
assert re.fullmatch(r'p[0-9a-f]{10}', config['run_id'])
assert config['catalog'] == 'polaris_ops_' + config['run_id']
spark.sql('DROP TABLE lab.sales.order_totals PURGE')
spark.sql('DROP TABLE lab.sales.orders PURGE')
spark.sql('DROP NAMESPACE lab.audit')
spark.sql('DROP NAMESPACE lab.sales')
# Remove only this run's remaining independent Parquet or residual objects.
root = 's3a://warehouse/polaris-operations/' + config['run_id']
path = spark._jvm.org.apache.hadoop.fs.Path(root)
fs = path.getFileSystem(spark._jsc.hadoopConfiguration())
if fs.exists(path):
    assert fs.delete(path, True)
spark.stop()
```

If notebook 1 was never run, `order_totals` and `audit` do not exist; omit those two drops after checking the actual namespaces/tables. Do not ignore unrelated errors. Inspect references before purging a table; this exercise created its own storage prefix and no external readers are expected.

## 2. Remove catalog-role mappings and the empty catalog

Use the original Bash terminal with STATE/PREFIX/CATALOG and the bootstrap credentials. Refresh the bootstrap token. These operations require the original bootstrap identity because the scoped exercise admin is not allowed to manage realm-wide principals.

```bash
export BOOTSTRAP_TOKEN=$(get_token "$BOOTSTRAP_ID" "$BOOTSTRAP_SECRET")
test "$CATALOG" = "polaris_ops_$RUN_ID"
test "$PREFIX" = "$CATALOG"
for ROLE in admin developer ops viewer; do
  curl -fsS -X DELETE \
    "$MGMT/principal-roles/${PREFIX}_${ROLE}_role/catalog-roles/$CATALOG/${ROLE}_catalog_role" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
  curl -fsS -X DELETE "$MGMT/catalogs/$CATALOG/catalog-roles/${ROLE}_catalog_role" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
done
curl -fsS -X DELETE "$MGMT/catalogs/$CATALOG" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
```

If a role was left revoked during an interrupted exercise, its mapping DELETE can return 404. Inspect that specific state before continuing rather than disabling all error checks.

## 3. Remove only this run's principals and principal roles

```bash
for ROLE in admin developer ops viewer; do
  NAME="${PREFIX}_${ROLE}"
  curl -fsS -X DELETE "$MGMT/principals/$NAME/principal-roles/${NAME}_role" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
  curl -fsS -X DELETE "$MGMT/principal-roles/${NAME}_role" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
  curl -fsS -X DELETE "$MGMT/principals/$NAME" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
  printf 'Removed exercise identity: %s\n' "$NAME"
done
unset ADMIN_TOKEN DEVELOPER_TOKEN OPS_TOKEN VIEWER_TOKEN BOOTSTRAP_TOKEN
unset BOOTSTRAP_SECRET CLIENT_SECRET S3_SECRET_KEY S3_ACCESS_KEY
```

Remove the run's private credential files from the host and notebook PVC after reviewing the exact paths. The source folder's `.gitignore` excludes them; never commit them. Keep the redacted validation record and executed notebook evidence if required. Stop the temporary port-forward terminal with Ctrl+C. No workload stop, scale change, Kubernetes Secret deletion or cluster shutdown is part of cleanup.

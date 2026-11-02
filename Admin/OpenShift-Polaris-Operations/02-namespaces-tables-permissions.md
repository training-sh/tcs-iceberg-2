# 02: Namespaces, tables and permission checks

Continue in the same Bash terminal. Use curl for metadata operations, then PySpark for records. Polaris is not a SQL endpoint: do not send INSERT SQL to the management API.

## Developer creates and edits a namespace

```bash
export ICEBERG="$REST/$CATALOG"
curl -fsS -X POST "$ICEBERG/namespaces" \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' \
  -d '{"namespace":["sales"],"properties":{"owner":"developer"}}' \
  > "$STATE/namespace-created.json"
curl -fsS -X POST "$ICEBERG/namespaces/sales/properties" \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' \
  -d '{"removals":[],"updates":{"description":"Orders used for the authorization exercise"}}' \
  > "$STATE/namespace-updated.json"
curl -fsS "$ICEBERG/namespaces" \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Polaris-Realm: POLARIS' \
  > "$STATE/ops-namespaces.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert ["sales"] in d["namespaces"]; print("PASS: developer created namespace; ops can list it")' "$STATE/ops-namespaces.json"
python3 -m json.tool "$STATE/ops-namespaces.json"
```

## Developer creates an empty Iceberg table

```bash
cat > "$STATE/create-orders.json" <<'JSON'
{
  "name":"orders",
  "schema":{
    "type":"struct",
    "fields":[
      {"id":1,"name":"order_id","required":false,"type":"long"},
      {"id":2,"name":"region","required":false,"type":"string"},
      {"id":3,"name":"amount","required":false,"type":"long"}
    ]
  },
  "partition-spec":{"spec-id":0,"fields":[]},
  "write-order":{"order-id":0,"fields":[]},
  "stage-create":false,
  "properties":{"format-version":"2","purpose":"authorization-demo"}
}
JSON
curl -fsS -X POST "$ICEBERG/namespaces/sales/tables" \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' --data-binary "@$STATE/create-orders.json" \
  > "$STATE/orders-created.json"
curl -fsS "$ICEBERG/namespaces/sales/tables" \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Polaris-Realm: POLARIS' \
  > "$STATE/ops-table-list.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert any(t["name"]=="orders" for t in d["identifiers"]); print("PASS: ops can list orders metadata")' "$STATE/ops-table-list.json"
```

Curl has created the schema and metadata, not order records. The first notebook will insert four rows and update one of them.

## Ops reads metadata but cannot request data credentials

Loading a table's schema/location is distinct from requesting credentials to read its files. Ops can inspect the former. A request for delegated storage credentials requires data privileges and is denied for ops:

```bash
curl -fsS "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Polaris-Realm: POLARIS' \
  > "$STATE/ops-table-metadata.json"
STATUS=$(curl -sS -o "$STATE/ops-data-delegation-denied.json" -w '%{http_code}' \
  "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'X-Iceberg-Access-Delegation: vended-credentials')
printf 'Ops data-credential request: HTTP %s (expected 403)\n' "$STATUS"
test "$STATUS" = 403
```

This demonstrates the Polaris data-privilege check, not a working STS service. The current SeaweedFS catalog has STS unavailable: even viewer cannot obtain vended credentials through that path (the inspected request returns 400). The viewer notebook instead uses its valid Polaris role plus the separately configured lab S3 credentials. Never distribute those broad S3 credentials to the ops role when demonstrating its intended metadata-only workflow.

## Developer edits table properties using a REST commit

Read the table UUID so the commit asserts it is modifying the expected table.

```bash
curl -fsS "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  > "$STATE/orders-current.json"
python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ['STATE'])
metadata = json.loads((p/'orders-current.json').read_text())['metadata']
payload = {'requirements': [{'type':'assert-table-uuid','uuid':metadata['table-uuid']}],
           'updates': [{'action':'set-properties','updates':{'reviewed-by':'developer'}}]}
(p/'table-update.json').write_text(json.dumps(payload))
PY
curl -fsS -X POST "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' --data-binary "@$STATE/table-update.json" \
  > "$STATE/orders-updated.json"
curl -fsS "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  > "$STATE/viewer-table-view.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["metadata"]["properties"]["reviewed-by"]=="developer"; print("PASS: developer edited table; viewer loaded it")' "$STATE/viewer-table-view.json"
```

## Authorization failures with valid credentials

Expected failures deliberately use curl without `-f` so the body and status can be inspected. Assert the status; an empty result, expired token or connection failure is not proof of authorization.

```bash
# Viewer cannot create a namespace.
STATUS=$(curl -sS -o "$STATE/viewer-denied.json" -w '%{http_code}' \
  -X POST "$ICEBERG/namespaces" \
  -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' -d '{"namespace":["viewer_should_not_create"]}')
printf 'Viewer namespace creation: HTTP %s (expected 403)\n' "$STATUS"
test "$STATUS" = 403
# Ops cannot create a table.
STATUS=$(curl -sS -o "$STATE/ops-denied.json" -w '%{http_code}' \
  -X POST "$ICEBERG/namespaces/sales/tables" \
  -H "Authorization: Bearer $OPS_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' --data-binary "@$STATE/create-orders.json")
printf 'Ops table creation: HTTP %s (expected 403)\n' "$STATUS"
test "$STATUS" = 403
# Viewer cannot modify existing table metadata.
STATUS=$(curl -sS -o "$STATE/viewer-update-denied.json" -w '%{http_code}' \
  -X POST "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' --data-binary "@$STATE/table-update.json")
printf 'Viewer table update: HTTP %s (expected 403)\n' "$STATUS"
test "$STATUS" = 403
# Developer cannot grant catalog privileges.
STATUS=$(curl -sS -o "$STATE/developer-grant-denied.json" -w '%{http_code}' \
  -X PUT "$MGMT/catalogs/$CATALOG/catalog-roles/viewer_catalog_role/grants" \
  -H "Authorization: Bearer $DEVELOPER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' \
  -d '{"grant":{"type":"catalog","privilege":"TABLE_WRITE_DATA"}}')
printf 'Developer access grant: HTTP %s (expected 403)\n' "$STATUS"
test "$STATUS" = 403
```

A 409 about an existing object is not the expected denial. It could mean the principal had enough permission to reach the conflict check; stop and inspect grants rather than marking the test passed.

## Admin revokes and restores the viewer's catalog role

The principal can still authenticate after revocation. Authentication and authorization are separate.

```bash
curl -fsS -X DELETE \
  "$MGMT/principal-roles/${PREFIX}_viewer_role/catalog-roles/$CATALOG/viewer_catalog_role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Polaris-Realm: POLARIS' > /dev/null
export VIEWER_TOKEN=$(role_token viewer)
STATUS=$(curl -sS -o "$STATE/viewer-revoked.json" -w '%{http_code}' \
  "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Polaris-Realm: POLARIS')
printf 'Authenticated viewer after catalog-role revocation: HTTP %s\n' "$STATUS"
test "$STATUS" = 403
curl -fsS -X PUT "$MGMT/principal-roles/${PREFIX}_viewer_role/catalog-roles/$CATALOG" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Polaris-Realm: POLARIS' \
  -H 'Content-Type: application/json' \
  -d '{"catalogRole":{"name":"viewer_catalog_role"}}' > /dev/null
export VIEWER_TOKEN=$(role_token viewer)
curl -fsS "$ICEBERG/namespaces/sales/tables/orders" \
  -H "Authorization: Bearer $VIEWER_TOKEN" -H 'Polaris-Realm: POLARIS' \
  > "$STATE/viewer-restored.json"
printf 'PASS: viewer authenticated while revoked; table access restored by admin.\n'
```

## Inspect the final grants without exposing credentials

```bash
for ROLE in admin developer ops viewer; do
  curl -fsS "$MGMT/catalogs/$CATALOG/catalog-roles/${ROLE}_catalog_role/grants" \
    -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Polaris-Realm: POLARIS' \
    > "$STATE/$ROLE-grants.json"
  printf '%s grants saved for review.\n' "$ROLE"
  python3 -m json.tool "$STATE/$ROLE-grants.json"
done
```

Review grant documents, not principal creation documents: the latter contain client secrets. Ops metadata visibility does not grant S3 credentials. The shared-storage boundary in README still applies to anyone who separately obtains those credentials.

## Scoped admin cannot read an unrelated catalog

```bash
STATUS=$(curl -sS -o "$STATE/admin-unrelated-catalog-denied.json" -w '%{http_code}' \
  "$MGMT/catalogs/training" \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Polaris-Realm: POLARIS')
printf 'Exercise admin reading unrelated training catalog: HTTP %s (expected 403)\n' "$STATUS"
test "$STATUS" = 403
```

The existing bootstrap administrator can see training; the newly created exercise admin cannot. This is why initial realm-wide principal/catalog provisioning uses the bootstrap identity rather than granting every exercise admin global service-admin authority.

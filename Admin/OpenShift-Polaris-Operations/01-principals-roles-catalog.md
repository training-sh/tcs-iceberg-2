# 01: Principals, roles and an isolated catalog

Continue in the working terminal from section 00. Do not print generated credential response files. The bootstrap identity performs initial provisioning; exercise admin remains scoped to this catalog rather than receiving realm-wide administrator access.

## Create four principals and their principal roles

```bash
for ROLE in admin developer ops viewer; do
  NAME="${PREFIX}_${ROLE}"
  curl -fsS -X POST "$MGMT/principals" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' \
    -d "{\"principal\":{\"name\":\"$NAME\"},\"credentialRotationRequired\":false}"     > "$STATE/$ROLE.json"
  curl -fsS -X POST "$MGMT/principal-roles" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' \
    -d "{\"principalRole\":{\"name\":\"${NAME}_role\"}}" > /dev/null
  curl -fsS -X PUT "$MGMT/principals/$NAME/principal-roles" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' \
    -d "{\"principalRole\":{\"name\":\"${NAME}_role\"}}" > /dev/null
  printf 'Created principal and principal role: %s\n' "$NAME"
done
```

A principal role alone grants no catalog privileges. The next steps create catalog roles, connect them to principal roles, and add privileges.

## Create the catalog using the existing storage configuration

Read the existing training catalog only to obtain its known-working endpoint/region flags. Give the new catalog a distinct allowed storage prefix. Never PUT this modified document back to training.

```bash
curl -fsS "$MGMT/catalogs/training" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS'   > "$STATE/training-source.json"
python3 - <<'PY'
import json, os
from pathlib import Path
state = Path(os.environ['STATE'])
source = json.loads((state/'training-source.json').read_text())
source = source.get('catalog', source)
location = 's3://warehouse/polaris-operations/' + os.environ['RUN_ID']
storage = dict(source['storageConfigInfo'])
storage['allowedLocations'] = [location]
payload = {'catalog': {'name': os.environ['CATALOG'], 'type': 'INTERNAL',
    'properties': {'default-base-location': location, 'purpose': 'polaris-access-lab'},
    'storageConfigInfo': storage}}
(state/'create-catalog.json').write_text(json.dumps(payload))
PY
curl -fsS -X POST "$MGMT/catalogs" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' --data-binary "@$STATE/create-catalog.json"   > "$STATE/catalog-created.json"
printf 'Created isolated catalog: %s\n' "$CATALOG"
```

## Add catalog roles and privileges

```bash
for ROLE in admin developer ops viewer; do
  curl -fsS -X POST "$MGMT/catalogs/$CATALOG/catalog-roles" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' \
    -d "{\"catalogRole\":{\"name\":\"${ROLE}_catalog_role\"}}" > /dev/null
  curl -fsS -X PUT "$MGMT/principal-roles/${PREFIX}_${ROLE}_role/catalog-roles/$CATALOG" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' \
    -d "{\"catalogRole\":{\"name\":\"${ROLE}_catalog_role\"}}" > /dev/null
done
# Grant at catalog scope: privileges apply to this catalog's descendants only.
for ROLE in admin developer ops viewer; do
  case "$ROLE" in
    admin) PRIVILEGES='CATALOG_MANAGE_ACCESS CATALOG_MANAGE_CONTENT CATALOG_READ_PROPERTIES CATALOG_WRITE_PROPERTIES' ;;
    developer) PRIVILEGES='CATALOG_MANAGE_CONTENT CATALOG_READ_PROPERTIES' ;;
    ops) PRIVILEGES='CATALOG_READ_PROPERTIES NAMESPACE_LIST NAMESPACE_READ_PROPERTIES TABLE_LIST TABLE_READ_PROPERTIES' ;;
    viewer) PRIVILEGES='CATALOG_READ_PROPERTIES NAMESPACE_LIST NAMESPACE_READ_PROPERTIES TABLE_LIST TABLE_READ_PROPERTIES TABLE_READ_DATA' ;;
  esac
  for PRIVILEGE in $PRIVILEGES; do
    curl -fsS -X PUT "$MGMT/catalogs/$CATALOG/catalog-roles/${ROLE}_catalog_role/grants" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' \
    -d "{\"grant\":{\"type\":\"catalog\",\"privilege\":\"$PRIVILEGE\"}}" > /dev/null
  done
  printf 'Granted %s privileges: %s\n' "$ROLE" "$PRIVILEGES"
done
```

Developer has full content-management rights in the exercise catalog, including table deletion. Developer has no catalog-access-management grant and is not a realm administrator. Ops has metadata privileges but receives no S3 credentials in this tutorial. Viewer has data-read permission without content-management permission.

## Obtain tokens for all four identities

```bash
role_token() {
  CLIENT_ID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["credentials"]["clientId"])' "$STATE/$1.json")
  CLIENT_SECRET=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["credentials"]["clientSecret"])' "$STATE/$1.json")
  get_token "$CLIENT_ID" "$CLIENT_SECRET"
}
export ADMIN_TOKEN=$(role_token admin)
export DEVELOPER_TOKEN=$(role_token developer)
export OPS_TOKEN=$(role_token ops)
export VIEWER_TOKEN=$(role_token viewer)
printf 'All four principals authenticated; tokens retained privately.\n'
```

## Admin views and edits catalog properties

Use optimistic concurrency: read the current entity version, preserve existing properties, then send the update.

```bash
curl -fsS "$MGMT/catalogs/$CATALOG" \
    -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Polaris-Realm: POLARIS'   > "$STATE/catalog-current.json"
python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ['STATE'])
c = json.loads((p/'catalog-current.json').read_text())
c = c.get('catalog', c)
props = dict(c['properties']); props['description'] = 'Managed by the exercise admin'
(p/'catalog-update.json').write_text(json.dumps({'currentEntityVersion': c['entityVersion'], 'properties': props}))
PY
curl -fsS -X PUT "$MGMT/catalogs/$CATALOG" \
    -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Polaris-Realm: POLARIS' \
    -H 'Content-Type: application/json' --data-binary "@$STATE/catalog-update.json"   > "$STATE/catalog-updated.json"
curl -fsS "$MGMT/catalogs/$CATALOG" \
    -H "Authorization: Bearer $OPS_TOKEN" -H 'Polaris-Realm: POLARIS'   > "$STATE/ops-catalog-view.json"
python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); c=c.get("catalog",c); assert c["properties"]["description"]=="Managed by the exercise admin"; print("PASS: admin edited catalog; ops viewed it")' "$STATE/ops-catalog-view.json"
python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); c=c.get("catalog",c); print(c["name"],c["properties"])' "$STATE/ops-catalog-view.json"
```

A 409 on update means the entity version changed; re-read and rebuild the update. Do not replace the default storage location just to edit the description.

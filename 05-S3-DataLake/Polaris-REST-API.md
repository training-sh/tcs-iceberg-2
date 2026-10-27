# Polaris REST API with SeaweedFS on OpenShift

Use Polaris Management and Iceberg REST APIs to create a catalog, a database/namespace and an empty table backed by a dedicated S3 location. All names start with `test-polaris-demo_`; the corresponding S3 bucket uses hyphens because underscores are not valid in S3 bucket names.

```text
test-polaris-demo_catalog_<random-id>
  test-polaris-demo_database_<random-id>
    test-polaris-demo_table_<random-id>
      id: long, required
      name: string, optional
```

This exercise is separate from the `training` catalog and `warehouse` bucket. It does not rebuild images or change deployment settings.

## 1. Check OpenShift services

In a Linux Bash terminal, from the course repository root:

```bash
source ~/.bashrc
okd-env
oc -n bigdata get pods -l 'app in (polaris,postgres,seaweedfs)'
oc -n bigdata get service polaris seaweedfs
command -v curl jq aws python3
```

If the cluster is stopped, use `okd-start` first and wait for completion. Required services must be Ready.

## 2. Forward the APIs

In one separate terminal after `okd-env`:

```bash
bash 05-S3-DataLake/forward-seaweedfs.sh
```

In another terminal after `okd-env`:

```bash
bash 05-S3-DataLake/forward-polaris.sh
```

Keep both running, or reuse working existing forwards.

| Interface | Terminal endpoint |
|---|---|
| Polaris Management / Iceberg REST API | `http://127.0.0.1:18181` |
| Polaris readiness | `http://127.0.0.1:18182/q/health/ready` |
| SeaweedFS S3 API | `http://127.0.0.1:19001` |

```bash
curl -fsS http://127.0.0.1:18182/q/health/ready | jq
```

Expect `status: UP`. This does not by itself prove catalog permissions or storage writes.

## 3. Configure credentials

```bash
export AWS_ACCESS_KEY_ID=team
export AWS_SECRET_ACCESS_KEY=team1234
export AWS_DEFAULT_REGION=us-east-1
export AWS_PAGER=""
export POLARIS_CLIENT_ID=team
export POLARIS_CLIENT_SECRET=team1234
export S3_ENDPOINT=http://127.0.0.1:19001
export POLARIS_URL=http://127.0.0.1:18181
export POLARIS_HEALTH_URL=http://127.0.0.1:18182
```

Use configured credentials if changed. `root:s3cr3t` belongs to the original example and is not assumed here. The exercise needs catalog-creation and catalog/namespace/table permissions; use the configured principal rather than changing global authorization settings.

## 4. Run the executable REST walkthrough

```bash
bash 05-S3-DataLake/test-polaris-rest.sh create
```

The script checks readiness, obtains a token without printing it, confirms the new names are unused, creates a dedicated bucket, verifies a storage probe, and performs the REST operations below. It also downloads the table's actual metadata JSON from S3 and checks its UUID, format version and schema ID against the REST response. Every request checks its HTTP status; errors are not silently piped into a success message.

On success it prints the generated resource names and:

```text
POLARIS_REST_CREATE_LIST_LOAD_PASS
STATE_FILE=/path/to/private/state.json
```

Keep that exact state-file path. Request and response JSON files are saved alongside it so each operation can be inspected. Tokens are kept in that private directory rather than printed.

## 5. Inspect authentication and request files

Set `STATE_FILE` to the printed path, then in the same terminal:

```bash
source 05-S3-DataLake/demo-common.sh
load_state "$STATE_FILE"
CATALOG="test-polaris-demo_catalog_$DEMO_ID"
DATABASE="test-polaris-demo_database_$DEMO_ID"
TABLE="test-polaris-demo_table_$DEMO_ID"
polaris_auth
```

Authentication uses this endpoint and the `Polaris-Realm: POLARIS` header:

```text
POST /api/catalog/v1/oauth/tokens
grant_type=client_credentials
scope=PRINCIPAL_ROLE:ALL
```

Check only that a token exists; do not print its value:

```bash
test -n "$TOKEN" && echo 'Token obtained'
```

## 6. Catalog configuration and discovery

Inspect the exact request used to create the catalog:

```bash
jq . "$STATE_DIR/catalog-request.json"
```

Its storage configuration uses:

| Setting | Value |
|---|---|
| Storage type | `S3` |
| Base location | `s3://<dedicated-test-bucket>/iceberg` |
| Allowed locations | That same isolated S3 root |
| Endpoint and internal endpoint | `http://seaweedfs.bigdata.svc.cluster.local:8333` |
| Region | `us-east-1` |
| Path-style access | `true` |
| STS unavailable | `true` |

Polaris accesses storage from inside OpenShift, so its endpoint must be Service DNS, not the terminal's localhost forward. AWS CLI in the terminal uses its explicitly configured local S3 endpoint. `stsUnavailable` does not create static credentials; the deployment's existing server-side storage configuration must supply the applicable access.

The create operation is `POST /api/management/v1/catalogs`. Do not repeat it against the same resource; inspect it instead:

```bash
curl -fsS "$POLARIS_URL/api/management/v1/catalogs" "${HEADERS[@]}" | jq
curl -fsS "$POLARIS_URL/api/management/v1/catalogs/$CATALOG" "${HEADERS[@]}" | jq
curl -fsS "$POLARIS_URL/api/catalog/v1/config?warehouse=$CATALOG" "${HEADERS[@]}" | jq
```

## 7. Database / namespace

The namespace was created with `POST /api/catalog/v1/<catalog>/namespaces` and this request shape:

```bash
jq . "$STATE_DIR/namespace-request.json"
```

Its `namespace` array contains the generated database name; its location is inside the dedicated catalog root.

List and describe it:

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/$CATALOG/namespaces" "${HEADERS[@]}" | jq
curl -fsS "$POLARIS_URL/api/catalog/v1/$CATALOG/namespaces/$DATABASE" "${HEADERS[@]}" | jq
```

## 8. Table creation and load

The table was created with `POST /api/catalog/v1/<catalog>/namespaces/<namespace>/tables`. Inspect the request schema and isolated location:

```bash
jq . "$STATE_DIR/table-request.json"
```

List and load it:

```bash
curl -fsS "$POLARIS_URL/api/catalog/v1/$CATALOG/namespaces/$DATABASE/tables" "${HEADERS[@]}" | jq
curl -fsS "$POLARIS_URL/api/catalog/v1/$CATALOG/namespaces/$DATABASE/tables/$TABLE" "${HEADERS[@]}" | jq
```

Inspect the saved response:

```bash
jq '.metadata.schemas' "$STATE_DIR/table-load.json"
jq '.metadata["current-schema-id"]' "$STATE_DIR/table-load.json"
jq '.["metadata-location"]' "$STATE_DIR/table-load.json"
```

The schema check expects required `id` of type `long` and optional `name` of type `string`. This REST exercise creates an empty table; it does not insert rows or prove Spark execution. For actual row writes, snapshots and manifests, continue to [Polaris and Iceberg](../06-Polaris-Iceberg/README.md).

## 9. Inspect S3 storage

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/" --recursive
```

The tested deployment writes an Iceberg metadata JSON object when this empty table is created; the script verifies that object against the API response. The empty table has no data-bearing snapshots or data manifests. The storage probe separately verifies S3 write/read access. You can repeat the metadata verification while the test exists:

```bash
bash 05-S3-DataLake/test-polaris-rest.sh verify "$STATE_FILE"
```

## 10. Delete the isolated test resources

Delete catalog entries from the bottom upward, then remove physical objects from the dedicated test bucket. Never point cleanup at `training`, `warehouse` or an existing catalog.

The guarded cleanup performs and verifies all deletion steps:

```bash
bash 05-S3-DataLake/test-polaris-rest.sh cleanup "$STATE_FILE"
```

It reconstructs and checks the names from the saved random ID, refreshes the token, drops the table registration **without a purge request**, verifies table absence, deletes/verifies the namespace and catalog, checks for unexpected objects in the test bucket, then removes only that test bucket's remaining objects and the bucket itself. The configured principal rejects `purgeRequested=true` with HTTP 403; no broader permissions are granted to work around that policy.

The corresponding REST deletion requests are:

```bash
curl -fsS -X DELETE "$POLARIS_URL/api/catalog/v1/$CATALOG/namespaces/$DATABASE/tables/$TABLE?purgeRequested=false" "${HEADERS[@]}"
curl -fsS -X DELETE "$POLARIS_URL/api/catalog/v1/$CATALOG/namespaces/$DATABASE" "${HEADERS[@]}"
curl -fsS -X DELETE "$POLARIS_URL/api/management/v1/catalogs/$CATALOG" "${HEADERS[@]}"
```

Prefer the cleanup script: it checks ownership, expected responses and storage contents. Dropping catalog registration and deleting physical S3 files are separate operations. The script removes only the bucket it created, after its catalog is gone. Local request/response files are retained for inspection.

#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/demo-common.sh"
action=${1:-create}
names() {
  CATALOG="test-polaris-demo_catalog_$DEMO_ID"
  DATABASE="test-polaris-demo_database_$DEMO_ID"
  TABLE="test-polaris-demo_table_$DEMO_ID"
  MANAGEMENT="/api/management/v1/catalogs/$CATALOG"
  REST="/api/catalog/v1/$CATALOG"
  TABLE_PATH="$REST/namespaces/$DATABASE/tables/$TABLE"
}
verify_table_storage() {
  api GET "$TABLE_PATH" 200 "$STATE_DIR/table-load.json"
  jq -e '.metadata.schemas[0].fields == [{id:1,name:"id",required:true,type:"long"},{id:2,name:"name",required:false,type:"string"}]' "$STATE_DIR/table-load.json" >/dev/null
  local location metadata_key uuid
  location=$(jq -er '.["metadata-location"]' "$STATE_DIR/table-load.json")
  [[ $location == "s3://$BUCKET/iceberg/$DATABASE/$TABLE/metadata/"*.metadata.json ]] || { echo 'Unexpected metadata location' >&2; exit 1; }
  metadata_key=${location#s3://$BUCKET/}
  s3 s3api list-objects-v2 --bucket "$BUCKET" > "$STATE_DIR/storage.json"
  jq -e --arg key "$metadata_key" 'any(.Contents[]; .Key == $key)' "$STATE_DIR/storage.json" >/dev/null
  s3 s3api get-object --bucket "$BUCKET" --key "$metadata_key" "$STATE_DIR/physical-metadata.json" > "$STATE_DIR/metadata-download.json"
  uuid=$(jq -er '.metadata["table-uuid"]' "$STATE_DIR/table-load.json")
  jq -e --arg uuid "$uuid" '.["table-uuid"] == $uuid and .["format-version"] == 2 and .["current-schema-id"] == 0' "$STATE_DIR/physical-metadata.json" >/dev/null
  echo 'POLARIS_PHYSICAL_S3_METADATA_PASS'
}
case "$action" in
create)
  new_state; names; polaris_auth
  require_absent_bucket
  api GET /api/management/v1/catalogs 200 "$STATE_DIR/catalogs-before.json"
  jq -e --arg name "$CATALOG" 'all(.catalogs[]; .name != $name)' "$STATE_DIR/catalogs-before.json" >/dev/null
  s3 s3api create-bucket --bucket "$BUCKET"
  jq -n --arg id "$DEMO_ID" --arg bucket "$BUCKET" --arg endpoint "$S3_ENDPOINT" --arg url "$POLARIS_URL" \
    '{kind:"polaris-rest-demo",id:$id,bucket:$bucket,s3_endpoint:$endpoint,polaris_url:$url}' > "$STATE_FILE"
  echo "STATE_FILE=$STATE_FILE"
  printf 'Polaris SeaweedFS storage probe\n' > "$STATE_DIR/probe.txt"
  s3 s3api put-object --bucket "$BUCKET" --key "test-polaris-demo_probe_$DEMO_ID.txt" --body "$STATE_DIR/probe.txt" > "$STATE_DIR/probe-upload.json"
  s3 s3api get-object --bucket "$BUCKET" --key "test-polaris-demo_probe_$DEMO_ID.txt" "$STATE_DIR/probe-read.txt" > "$STATE_DIR/probe-download.json"
  cmp "$STATE_DIR/probe.txt" "$STATE_DIR/probe-read.txt"
  jq -n --arg name "$CATALOG" --arg location "s3://$BUCKET/iceberg" \
    '{catalog:{type:"INTERNAL",name:$name,properties:{"default-base-location":$location},storageConfigInfo:{storageType:"S3",allowedLocations:[$location],endpoint:"http://seaweedfs.bigdata.svc.cluster.local:8333",endpointInternal:"http://seaweedfs.bigdata.svc.cluster.local:8333",region:"us-east-1",pathStyleAccess:true,stsUnavailable:true}}}' > "$STATE_DIR/catalog-request.json"
  api POST /api/management/v1/catalogs '200 201' "$STATE_DIR/catalog-create.json" --data-binary @"$STATE_DIR/catalog-request.json"
  api GET "$MANAGEMENT" 200 "$STATE_DIR/catalog-describe.json"
  api GET "/api/catalog/v1/config?warehouse=$CATALOG" 200 "$STATE_DIR/discovery.json"
  jq -n --arg name "$DATABASE" --arg location "s3://$BUCKET/iceberg/$DATABASE" \
    '{namespace:[$name],properties:{location:$location}}' > "$STATE_DIR/namespace-request.json"
  api POST "$REST/namespaces" '200 201' "$STATE_DIR/namespace-create.json" --data-binary @"$STATE_DIR/namespace-request.json"
  api GET "$REST/namespaces" 200 "$STATE_DIR/namespaces.json"
  jq -e --arg name "$DATABASE" 'any(.namespaces[]; . == [$name])' "$STATE_DIR/namespaces.json" >/dev/null
  api GET "$REST/namespaces/$DATABASE" 200 "$STATE_DIR/namespace-describe.json"
  jq -n --arg name "$TABLE" --arg location "s3://$BUCKET/iceberg/$DATABASE/$TABLE" \
    '{name:$name,location:$location,schema:{type:"struct","schema-id":0,fields:[{id:1,name:"id",required:true,type:"long"},{id:2,name:"name",required:false,type:"string"}]},properties:{"format-version":"2"}}' > "$STATE_DIR/table-request.json"
  api POST "$REST/namespaces/$DATABASE/tables" '200 201' "$STATE_DIR/table-create.json" --data-binary @"$STATE_DIR/table-request.json"
  api GET "$REST/namespaces/$DATABASE/tables" 200 "$STATE_DIR/tables.json"
  jq -e --arg name "$TABLE" 'any(.identifiers[]; .name == $name)' "$STATE_DIR/tables.json" >/dev/null
  verify_table_storage
  echo "CATALOG=$CATALOG DATABASE=$DATABASE TABLE=$TABLE BUCKET=$BUCKET"
  jq '{metadata_location:."metadata-location",current_schema_id:.metadata."current-schema-id",snapshot_count:(.metadata.snapshots // [] | length)}' "$STATE_DIR/table-load.json"
  jq '[.Contents[]?.Key]' "$STATE_DIR/storage.json"
  echo 'POLARIS_REST_CREATE_LIST_LOAD_PASS'
  echo "STATE_FILE=$STATE_FILE"
  echo "Cleanup: bash $0 cleanup '$STATE_FILE'"
  ;;
verify)
  [[ $# == 2 ]] || { echo 'Usage: test-polaris-rest.sh verify STATE_FILE' >&2; exit 1; }
  load_state "$2"; names
  [[ $(jq -er '.kind' "$STATE_FILE") == polaris-rest-demo ]] || exit 1
  [[ $(jq -er '.polaris_url' "$STATE_FILE") == "$POLARIS_URL" ]] || exit 1
  polaris_auth
  verify_table_storage
  ;;
cleanup)
  [[ $# == 2 ]] || { echo 'Usage: test-polaris-rest.sh cleanup STATE_FILE' >&2; exit 1; }
  load_state "$2"; names
  [[ $(jq -er '.kind' "$STATE_FILE") == polaris-rest-demo ]] || exit 1
  [[ $(jq -er '.polaris_url' "$STATE_FILE") == "$POLARIS_URL" ]] || exit 1
  polaris_auth
  api DELETE "$TABLE_PATH?purgeRequested=false" '200 204 404' "$STATE_DIR/table-delete.json"
  api GET "$TABLE_PATH" 404 "$STATE_DIR/table-after-delete.json"
  api DELETE "$REST/namespaces/$DATABASE" '200 204 404' "$STATE_DIR/namespace-delete.json"
  api GET "$REST/namespaces/$DATABASE" 404 "$STATE_DIR/namespace-after-delete.json"
  api DELETE "$MANAGEMENT" '200 204 404' "$STATE_DIR/catalog-delete.json"
  api GET "$MANAGEMENT" 404 "$STATE_DIR/catalog-after-delete.json"
  # All catalog entries are gone before removing physical objects from its own
  # newly created bucket. Never use --force against warehouse or other buckets.
  s3 s3api list-objects-v2 --bucket "$BUCKET" > "$STATE_DIR/storage-before-delete.json"
  jq -e --arg prefix "iceberg/$DATABASE/$TABLE/" --arg probe "test-polaris-demo_probe_$DEMO_ID.txt" \
    'all(.Contents[]?; (.Key == $probe) or (.Key | startswith($prefix)))' "$STATE_DIR/storage-before-delete.json" >/dev/null
  s3 s3 rm "s3://$BUCKET/" --recursive
  s3 s3api delete-bucket --bucket "$BUCKET"
  s3 s3api list-buckets > "$STATE_DIR/buckets-after.json"
  jq -e --arg bucket "$BUCKET" 'all(.Buckets[]; .Name != $bucket)' "$STATE_DIR/buckets-after.json" >/dev/null
  echo 'POLARIS_REST_DELETE_TABLE_NAMESPACE_CATALOG_BUCKET_PASS'
  ;;
*) echo 'Use create, verify STATE_FILE or cleanup STATE_FILE' >&2; exit 1 ;;
esac

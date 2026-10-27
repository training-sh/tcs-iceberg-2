#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/demo-common.sh"
action=${1:-create}
case "$action" in
create)
  new_state
  OBJECT="test-polaris-demo_object_$DEMO_ID.txt"
  require_absent_bucket
  s3 s3api create-bucket --bucket "$BUCKET"
  jq -n --arg id "$DEMO_ID" --arg bucket "$BUCKET" --arg key "$OBJECT" --arg endpoint "$S3_ENDPOINT" \
    '{kind:"seaweedfs-s3-demo",id:$id,bucket:$bucket,key:$key,s3_endpoint:$endpoint}' > "$STATE_FILE"
  echo "STATE_FILE=$STATE_FILE"
  printf 'SeaweedFS S3 test: %s\n' "$DEMO_ID" > "$STATE_DIR/input.txt"
  s3 s3api put-object --bucket "$BUCKET" --key "$OBJECT" --body "$STATE_DIR/input.txt" > "$STATE_DIR/upload.json"
  s3 s3api head-object --bucket "$BUCKET" --key "$OBJECT" > "$STATE_DIR/head.json"
  s3 s3api list-objects-v2 --bucket "$BUCKET" > "$STATE_DIR/objects.json"
  jq -e --arg key "$OBJECT" 'any(.Contents[]; .Key == $key)' "$STATE_DIR/objects.json" >/dev/null
  s3 s3api get-object --bucket "$BUCKET" --key "$OBJECT" "$STATE_DIR/download.txt" > "$STATE_DIR/download.json"
  cmp "$STATE_DIR/input.txt" "$STATE_DIR/download.txt"
  s3 s3 cp "s3://$BUCKET/$OBJECT" - > "$STATE_DIR/stdout.txt"
  cmp "$STATE_DIR/input.txt" "$STATE_DIR/stdout.txt"
  echo 'SEAWEEDFS_S3_CREATE_UPLOAD_LIST_DOWNLOAD_PASS'
  echo "STATE_FILE=$STATE_FILE"
  echo "Cleanup: bash $0 cleanup '$STATE_FILE'"
  ;;
cleanup)
  [[ $# == 2 ]] || { echo 'Usage: test-seaweedfs-s3.sh cleanup STATE_FILE' >&2; exit 1; }
  load_state "$2"
  [[ $(jq -er '.kind' "$STATE_FILE") == seaweedfs-s3-demo ]] || exit 1
  OBJECT=$(jq -er '.key' "$STATE_FILE")
  [[ $OBJECT == "test-polaris-demo_object_$DEMO_ID.txt" ]] || exit 1
  # Do not remove a bucket that has acquired other objects.
  s3 s3api list-objects-v2 --bucket "$BUCKET" > "$STATE_DIR/before-delete.json"
  jq -e --arg key "$OBJECT" 'all(.Contents[]?; .Key == $key)' "$STATE_DIR/before-delete.json" >/dev/null
  s3 s3api delete-object --bucket "$BUCKET" --key "$OBJECT"
  s3 s3api list-objects-v2 --bucket "$BUCKET" > "$STATE_DIR/after-delete.json"
  jq -e '(.Contents // []) | length == 0' "$STATE_DIR/after-delete.json" >/dev/null
  s3 s3api delete-bucket --bucket "$BUCKET"
  s3 s3api list-buckets > "$STATE_DIR/buckets-after.json"
  jq -e --arg bucket "$BUCKET" 'all(.Buckets[]; .Name != $bucket)' "$STATE_DIR/buckets-after.json" >/dev/null
  echo 'SEAWEEDFS_S3_DELETE_OBJECT_BUCKET_PASS'
  ;;
*) echo 'Use create or cleanup STATE_FILE' >&2; exit 1 ;;
esac

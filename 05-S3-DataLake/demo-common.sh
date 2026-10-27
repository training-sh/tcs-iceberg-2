#!/usr/bin/env bash
# Shared functions; source this file from the demo scripts.
set -euo pipefail
umask 077
export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-team}
export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-team1234}
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
export AWS_PAGER=''
export AWS_EC2_METADATA_DISABLED=true
S3_ENDPOINT=${S3_ENDPOINT:-http://127.0.0.1:19001}
POLARIS_URL=${POLARIS_URL:-http://127.0.0.1:18181}
POLARIS_HEALTH_URL=${POLARIS_HEALTH_URL:-http://127.0.0.1:18182}
for tool in curl jq aws python3 cmp; do command -v "$tool" >/dev/null || { echo "Missing command: $tool" >&2; exit 1; }; done
s3() { aws --endpoint-url "$S3_ENDPOINT" "$@"; }
new_state() {
  DEMO_ID=$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')
  local root=${TEST_STATE_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/s3-datalake}
  mkdir -p "$root"
  STATE_DIR=$(mktemp -d "$root/test-polaris-demo.XXXXXX")
  STATE_FILE="$STATE_DIR/state.json"
  BUCKET="test-polaris-demo-$DEMO_ID"
}
load_state() {
  STATE_FILE=$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "$1")
  STATE_DIR=$(dirname "$STATE_FILE")
  DEMO_ID=$(jq -er '.id' "$STATE_FILE")
  [[ $DEMO_ID =~ ^[0-9a-f]{12}$ ]] || { echo 'Invalid demo identifier' >&2; exit 1; }
  BUCKET=$(jq -er '.bucket' "$STATE_FILE")
  [[ $BUCKET == "test-polaris-demo-$DEMO_ID" ]] || { echo 'Bucket ownership guard failed' >&2; exit 1; }
  [[ $(jq -er '.s3_endpoint' "$STATE_FILE") == "$S3_ENDPOINT" ]] || { echo 'S3 endpoint differs from recorded test' >&2; exit 1; }
}
require_absent_bucket() {
  s3 s3api list-buckets > "$STATE_DIR/buckets-before.json"
  jq -e --arg bucket "$BUCKET" 'all(.Buckets[]; .Name != $bucket)' "$STATE_DIR/buckets-before.json" >/dev/null || { echo 'Bucket already exists; stop' >&2; exit 1; }
}
polaris_auth() {
  curl -fsS --connect-timeout 10 --max-time 30 "$POLARIS_HEALTH_URL/q/health/ready" | jq -e '.status == "UP"' >/dev/null
  curl -fsS --connect-timeout 10 --max-time 30 "$POLARIS_URL/api/catalog/v1/oauth/tokens" \
    -H 'Polaris-Realm: POLARIS' --data-urlencode grant_type=client_credentials \
    --data-urlencode "client_id=${POLARIS_CLIENT_ID:-team}" \
    --data-urlencode "client_secret=${POLARIS_CLIENT_SECRET:-team1234}" \
    --data-urlencode scope=PRINCIPAL_ROLE:ALL > "$STATE_DIR/token.json"
  TOKEN=$(jq -er '.access_token | select(type == "string" and length > 0)' "$STATE_DIR/token.json")
  HEADERS=(-H "Authorization: Bearer $TOKEN" -H 'Polaris-Realm: POLARIS')
}
api() {
  local method=$1 path=$2 expected=$3 output=$4; shift 4
  local status
  status=$(curl -sS --connect-timeout 10 --max-time 40 -X "$method" "${HEADERS[@]}" \
    -H 'Content-Type: application/json' "$POLARIS_URL$path" -o "$output" -w '%{http_code}' "$@")
  echo "$method $path -> $status"
  [[ " $expected " == *" $status "* ]] || { cat "$output" >&2; return 1; }
}

# 00: Access and authentication

Read [Fundamentals](FUNDAMENTALS.md) first. This chapter puts authentication into practice; the next chapter connects roles and privileges.

## Preflight

Use the existing oc binary and kubeconfig for your VM. Change the paths below if your installation differs.

```bash
export PATH="$HOME/.crc/bin/oc:$HOME/.crc/bin:$PATH"
export KUBECONFIG="$HOME/.crc/machines/crc/kubeconfig"
export NS=bigdata
oc whoami
oc get nodes
oc -n "$NS" get deployment/polaris statefulset/postgres statefulset/seaweedfs statefulset/spark-master statefulset/spark-worker
oc -n "$NS" get pods,svc
command -v curl
command -v python3
oc -n "$NS" wait --for=condition=Available deployment/polaris --timeout=180s
oc -n "$NS" wait --for=condition=Ready pod/postgres-0 pod/seaweedfs-0 pod/spark-master-0 pod/spark-worker-0 --timeout=180s
```

If CRC is stopped, `crc start` starts the existing instance. Do not use `crc setup`, recreate the cluster, apply manifests or change workload replica counts for this exercise. Wait for the existing Polaris/PostgreSQL/SeaweedFS workloads to become ready after startup. A missing or deliberately stopped dependency is a preflight failure to resolve with the environment owner.

## Forward the existing Polaris API

Run in a separate terminal and keep it open:

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/polaris 28181:8181
```

In the working terminal, enter the course folder. All state below is created under your current directory, so use a writable course copy.

```bash
cd ~/openshift/OpenShift-Polaris-Operations
umask 077
export BASE=http://127.0.0.1:28181
export MGMT="$BASE/api/management/v1"
export REST="$BASE/api/catalog/v1"
export RUN_ID="p$(python3 -c 'import uuid; print(uuid.uuid4().hex[:10])')"
export CATALOG="polaris_ops_$RUN_ID"
export PREFIX="polaris_ops_$RUN_ID"
export STATE="$PWD/.local-state/$RUN_ID"
mkdir -p "$STATE"
printf 'Run: %s\nCatalog: %s\nPrivate state: %s\n' "$RUN_ID" "$CATALOG" "$STATE"
```

The bootstrap credentials come from the existing Secret; no Secret is created or changed. Shell tracing must be off before retrieving them.

```bash
set +x
BOOTSTRAP_ID=$(oc -n "$NS" get secret lab-credentials -o jsonpath='{.data.polaris-client-id}' | base64 --decode)
BOOTSTRAP_SECRET=$(oc -n "$NS" get secret lab-credentials -o jsonpath='{.data.polaris-client-secret}' | base64 --decode)
# This function returns a token without displaying the client secret.
get_token() {
  curl -fsS "$REST/oauth/tokens" \
    -H 'Polaris-Realm: POLARIS' \
    --data-urlencode grant_type=client_credentials \
    --data-urlencode "client_id=$1" \
    --data-urlencode "client_secret=$2" \
    --data-urlencode scope=PRINCIPAL_ROLE:ALL |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
}
export BOOTSTRAP_TOKEN=$(get_token "$BOOTSTRAP_ID" "$BOOTSTRAP_SECRET")
test -n "$BOOTSTRAP_TOKEN"
curl -fsS "$MGMT/catalogs" \
    -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
    -H 'Polaris-Realm: POLARIS' > "$STATE/catalogs-before.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("Bootstrap catalog listing succeeded")' "$STATE/catalogs-before.json"
```

Never print tokens, the Secret JSON or principal creation responses. The response files in STATE contain private client credentials. A token is temporary; obtain a new one with the same function if it expires. A valid token alone does not imply permission to create a namespace or modify a table.

## Demonstrate authentication failure

```bash
STATUS=$(curl -sS -o "$STATE/bad-credentials.json" -w '%{http_code}'   "$REST/oauth/tokens" -H 'Polaris-Realm: POLARIS' \
    --data-urlencode grant_type=client_credentials \
    --data-urlencode client_id=not_a_real_principal \
    --data-urlencode client_secret=not_a_real_secret \
    --data-urlencode scope=PRINCIPAL_ROLE:ALL)
printf 'Invalid credentials: HTTP %s\n' "$STATUS"
test "$STATUS" = 400 -o "$STATUS" = 401
```

OAuth endpoints may report invalid client credentials as 400 or 401 depending on version. Do not mistake an authentication error for a catalog permission denial. A network failure is neither outcome; curl then reports a connection error.

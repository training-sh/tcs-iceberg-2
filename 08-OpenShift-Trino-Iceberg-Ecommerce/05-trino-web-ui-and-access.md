# 05 — Trino web UI, HTTPS Route and optional passwords

The UI shows query activity, state, plans and execution statistics. Submit SQL through the CLI or a query client. Use the Linux desktop browser; no connection from another machine is required.

## 1. Default access without changing Trino configuration

Open a host terminal:

```bash
export PATH="$HOME/.crc/bin/oc:$PATH"
oc port-forward -n bigdata svc/trino 8089:8080 --address=127.0.0.1
```

Keep it open. Browse to `http://127.0.0.1:8089/ui/`. In the default exercise profile, enter `team`; there is no password check. A disabled password field is expected. Submit a small query from the CLI and inspect it in the UI. End the forward with Ctrl+C.

This is the access method used by the core exercises and the existing Airflow HTTP client. It creates a temporary loopback listener and changes no Trino server configuration.

## 2. What the prepared Route does

Read [trino-routes.yaml](trino-routes.yaml). It defines one edge-terminated HTTPS Route to the existing `service/trino` port 8080, redirects HTTP to HTTPS, and replaces forwarded headers at the router. The proposed hostname is `trino-bigdata.apps-crc.testing`; confirm the cluster's actual application domain before applying it.

The Route does **not** store passwords or create accounts. Trino must perform authentication. The optional files below supply that configuration. Do not expose the default username-only API as if it were password-protected.

## 3. Optional password profile — configuration change and restart

This section changes the coordinator's pod template, creates Secrets and restarts it. It is separate from the data exercises. Finish active queries and keep Airflow DAGs idle before proceeding. Enabling server password authentication also changes API access: the original unauthenticated HTTP CLI commands and Airflow client will no longer work unchanged.

Use this profile after the base/Airflow exercises, or first migrate every caller to HTTPS with credential handling and a trusted CA. A browser login is not automatically inherited by Airflow, JDBC, metrics scrapers or notebook clients. Do not enable insecure HTTP password authentication to keep older clients working.

Review these local files:

| File | Purpose |
|---|---|
| [trino-auth-config.yaml](trino-auth-config.yaml) | Password-file authenticator, forwarded HTTPS and internal-secret settings |
| [trino-ui-auth-patch.yaml](trino-ui-auth-patch.yaml) | Strategic merge patch for the existing coordinator |
| [trino-worker-auth-patch.yaml](trino-worker-auth-patch.yaml) | Matching internal-secret setup for the optional workers |
| [trino-routes.yaml](trino-routes.yaml) | HTTPS browser/API endpoint |

The coordinator patch copies the image's current configuration/catalog files into a writable runtime directory, changes only authentication-related properties there, and launches Trino. It retains existing pod mounts, image and database/storage Secret references. Verify the current image uses `/etc/trino` and `/usr/lib/trino/bin/launcher` before applying it. The prepared patch targets container name `trino`.

```bash
cd ~/openshift/08-OpenShift-Trino-Iceberg-Ecommerce
oc exec -n bigdata trino-0 -- test -r /etc/trino/config.properties
oc exec -n bigdata trino-0 -- test -x /usr/lib/trino/bin/launcher
oc rollout history statefulset/trino -n bigdata
```

Record the pre-change revision for rollback. If an optional worker is running, scale it to zero after queries finish before changing the shared-secret profile. The worker and coordinator must use the same internal secret.

## 4. Create the password and shared-secret files privately

Use username **team** and the disposable exercise password **team1234** at the prompts below. This creates a separate Trino password-file account; it does not authenticate against MySQL. The actual password file stores a hash, and the Route contains no password. Use a different password outside this isolated exercise environment.

This procedure needs the existing `htpasswd` utility. Check it first; if absent, stop this optional profile rather than installing a package automatically:

```bash
command -v htpasswd
```

In the host terminal, create protected files outside the course source directory:

```bash
umask 077
mkdir -p "$HOME/.local/state"
TRINO_AUTH_DIR=$(mktemp -d "$HOME/.local/state/trino-ui.XXXXXX")
htpasswd -B -C 10 -c "$TRINO_AUTH_DIR/password.db" team
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > "$TRINO_AUTH_DIR/shared-secret"
```

`htpasswd` prompts twice and writes a bcrypt hash. The shared secret is random and redirected to a private file. Do not display either file, turn on shell tracing or put these files in course assets. Keep the directory for this setup session; the variable is used in the next commands.

Check whether these named Secrets already exist without reading their contents:

```bash
oc get secret -n bigdata trino-ui-passwords trino-internal-auth --ignore-not-found
```

If either exists, stop and review its ownership/rotation plan. Do not silently replace a shared secret used by running nodes. For a new setup, create them without printing their values:

```bash
oc create secret generic trino-ui-passwords -n bigdata --from-file=password.db="$TRINO_AUTH_DIR/password.db"
oc create secret generic trino-internal-auth -n bigdata --from-file=shared-secret="$TRINO_AUTH_DIR/shared-secret"
```

## 5. Apply the reviewed configuration and Route

These commands perform the optional configuration change and rolling restart. They are not part of a read-only inspection:

```bash
oc apply --dry-run=server -f trino-auth-config.yaml
oc apply -f trino-auth-config.yaml
oc patch statefulset trino -n bigdata --type=strategic --patch-file trino-ui-auth-patch.yaml
oc rollout status statefulset/trino -n bigdata --timeout=600s
```

If the optional worker definition exists, apply its matching patch while it remains at zero replicas:

```bash
oc patch statefulset trino-worker -n bigdata --type=strategic --patch-file trino-worker-auth-patch.yaml
```

Do not run that worker command if the optional workload has not been created. After the coordinator is ready, start only the required worker count and verify node discovery through the authenticated CLI.

Finally expose the endpoint:

```bash
oc apply --dry-run=server -f trino-routes.yaml
oc apply -f trino-routes.yaml
oc get route trino -n bigdata
```

Confirm the Route is admitted. In the Linux desktop browser, open `https://trino-bigdata.apps-crc.testing/ui/`. Use username **team** and password **team1234**. Use the cluster/router CA trusted by the desktop. A hostname/DNS/certificate error must be resolved against the configured application domain and CA; do not treat a disabled certificate check as successful verification.

## 6. Verify actual authentication

Check that:

1. Correct credentials allow a browser login.
2. A wrong password is rejected.
3. An unauthenticated HTTPS SQL API request cannot execute a query.
4. HTTP redirects to HTTPS.
5. A query submitted by the authenticated CLI appears in the UI.

The CLI already installed in the Trino pod can connect through the Route only if that pod can resolve the Route hostname and trusts its CA. Supply the approved CA file with `--truststore-path` when required; do not add `--insecure` as a default:

```bash
oc exec -it -n bigdata trino-0 -- trino --server https://trino-bigdata.apps-crc.testing --user team --password
```

This prompts privately. Do not put a password in command arguments. Route DNS and CA trust inside pods can differ from the host desktop; resolve those prerequisites before using this CLI path. The prepared authentication files are reviewed templates, not evidence that the live deployment has been secured.

## 7. Return to the base profile

Finish queries first. Remove only the exercise Route so the endpoint is no longer exposed before restoring username-only access:

```bash
oc delete route trino -n bigdata
```

Use the pre-change rollout revision recorded in step 3. If the authentication patch is the only subsequent pod-template change, `oc rollout undo statefulset/trino -n bigdata` returns to the previous template. Otherwise select the recorded revision explicitly with `--to-revision`; do not undo unrelated changes.

If an optional worker was patched, scale it to zero and restore its matching prior template before bringing it back with the base coordinator. Confirm the loopback CLI works again and existing Airflow callers use the base profile. Only remove the authentication ConfigMap/Secrets after confirming no workload still references them. Keep private files out of shared reports.

## References

[Trino 476 password-file authentication](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/security/password-file.md), [TLS termination](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/security/tls.md), [internal shared secret](https://github.com/trinodb/trino/blob/476/docs/src/main/sphinx/security/internal-communication.md), and [OpenShift edge Routes](https://docs.redhat.com/en/documentation/openshift_container_platform/4.14/html/networking/configuring-routes). Route TLS and Trino account authentication solve separate parts of the access path.

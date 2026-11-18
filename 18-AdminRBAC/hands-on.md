# Hands-on: OKD users and RBAC with oc and YAML

Read [introduction-rbac.md](introduction-rbac.md). Run commands from a normal
Linux terminal. **No Python helper is required.** `oc` is the OpenShift CLI:
it handles standard Kubernetes resources plus OKD resources such as OAuth,
User, Identity and Project.

## 1. Preserve a cluster-administrator session

```bash
cd ~/openshift/18-AdminRBAC
command -v oc htpasswd
export ADMIN_KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"
export KUBECONFIG="$ADMIN_KUBECONFIG"
oc whoami
oc auth can-i '*' '*' --all-namespaces
oc get co authentication
```

The permission check must say `yes`. Use this original cluster-administrator
account for setup and cleanup. The new `admin` account will have project-level
administration only. If `htpasswd` is missing on Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y apache2-utils
```

Check that all exercise names are unused:

```bash
oc get users admin dev ops --ignore-not-found
oc get identities rbac-training:admin rbac-training:dev rbac-training:ops --ignore-not-found
oc get namespace rbac-demo --ignore-not-found
oc -n openshift-config get secret rbac-training-htpasswd --ignore-not-found
oc get oauth cluster -o jsonpath='{range .spec.identityProviders[*]}{.name}{"\n"}{end}'
```

The first four commands must return no matching objects. `rbac-training` must
not appear in the provider list. **Stop on any collision**; do not overwrite a
pre-existing account or project. Create a private directory and configuration
backup; if the directory already exists, finish the previous exercise first:

```bash
mkdir -m 700 .rbac-state
oc get oauth cluster -o yaml > .rbac-state/oauth-before.yaml
oc get oauth cluster -o jsonpath='{range .spec.identityProviders[*]}{.name}{"\n"}{end}' > .rbac-state/providers-before.txt
chmod 600 .rbac-state/oauth-before.yaml
export API_URL="$(oc config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
printf '%s\n' "$API_URL"
```

Do not share the backup or blindly apply it over another administrator's later
changes. Keep this terminal in the current directory throughout the exercise.

## 2. Create authentication credentials

Choose passwords interactively when prompted. No fixed passwords are supplied:

```bash
htpasswd -c -B .rbac-state/users.htpasswd admin
htpasswd -B .rbac-state/users.htpasswd dev
htpasswd -B .rbac-state/users.htpasswd ops
chmod 600 .rbac-state/users.htpasswd
```

`-B` creates bcrypt hashes. Use `-c` **only on the first command**; it replaces
the file. Authentication entries do not assign any RBAC permissions.

Generate the Secret YAML with `oc`, then apply it:

```bash
oc -n openshift-config create secret generic rbac-training-htpasswd \
  --from-file=htpasswd=.rbac-state/users.htpasswd \
  --dry-run=client -o yaml > .rbac-state/htpasswd-secret.yaml
chmod 600 .rbac-state/htpasswd-secret.yaml
oc apply -f .rbac-state/htpasswd-secret.yaml
```

## 3. Add the identity provider

```bash
oc edit oauth cluster
```

Under `spec.identityProviders`, **append** this item. Preserve every existing
provider. If the list is absent, create it under `spec`:

```yaml
- name: rbac-training
  mappingMethod: claim
  type: HTPasswd
  htpasswd:
    fileData:
      name: rbac-training-htpasswd
```

For context, the containing structure looks like this:

```yaml
spec:
  identityProviders:
    # Preserve existing entries here.
    - name: rbac-training
      mappingMethod: claim
      type: HTPasswd
      htpasswd:
        fileData:
          name: rbac-training-htpasswd
```

This is an addition, not a replacement OAuth manifest. Save and exit the editor:

```bash
oc get co authentication
oc -n openshift-authentication get pods
oc -n openshift-authentication rollout status deployment/oauth-openshift --timeout=300s
```

Reconciliation can take several minutes. A rollout command issued immediately
can still describe the previous rollout. Confirm the provider appears in a
refreshed portal login page and retry authentication after reconciliation.
With `claim`, successful login automatically creates the OKD User and Identity;
creating a User object separately would not create a password.

## 4. Apply the project, Roles and RoleBindings

```bash
oc apply -f manifests/01-project.yaml
oc apply -f manifests/02-roles.yaml
oc apply -f manifests/03-rolebindings.yaml
oc apply -f manifests/04-demo.yaml
oc -n rbac-demo rollout status deployment/rbac-hello --timeout=180s
oc -n rbac-demo get roles,rolebindings,pods
```

| YAML file | Resources |
|---|---|
| [01-project.yaml](manifests/01-project.yaml) | Namespace and sample ConfigMap |
| [02-roles.yaml](manifests/02-roles.yaml) | `app-developer` and `app-operator` Roles |
| [03-rolebindings.yaml](manifests/03-rolebindings.yaml) | Bindings for `admin`, `dev`, `ops` |
| [04-demo.yaml](manifests/04-demo.yaml) | Small Deployment that produces pod logs |

The image `docker.io/library/busybox:1.37` must be cached or pullable. Inspect the
role rules and bindings directly:

```bash
cat manifests/02-roles.yaml
cat manifests/03-rolebindings.yaml
oc -n rbac-demo describe role app-developer
oc -n rbac-demo describe role app-operator
oc -n rbac-demo describe rolebinding project-admin
```

The administrator binding uses a built-in ClusterRole, but only in this project:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: project-admin
  namespace: rbac-demo
subjects:
- kind: User
  name: admin
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: admin
  apiGroup: rbac.authorization.k8s.io
```

The same supplied file binds `dev` to `app-developer` and `ops` to `app-operator`.
Both custom Roles grant `get` for this project's Namespace and Project objects,
because the portal needs those reads in addition to pod access.

## 5. Log in with separate kubeconfigs

These commands prompt for the passwords chosen in step 2:

```bash
oc --kubeconfig=.rbac-state/admin.kubeconfig login "$API_URL" -u admin --insecure-skip-tls-verify=true
oc --kubeconfig=.rbac-state/dev.kubeconfig login "$API_URL" -u dev --insecure-skip-tls-verify=true
oc --kubeconfig=.rbac-state/ops.kubeconfig login "$API_URL" -u ops --insecure-skip-tls-verify=true
oc --kubeconfig=.rbac-state/admin.kubeconfig whoami
oc --kubeconfig=.rbac-state/dev.kubeconfig whoami
oc --kubeconfig=.rbac-state/ops.kubeconfig whoami
```

The insecure TLS option is for self-signed local clusters; use the trusted
cluster CA when available. The separate files protect the original admin
session from context changes. Do not share them.

## 6. Verify developer access

```bash
oc --kubeconfig=.rbac-state/dev.kubeconfig get project rbac-demo
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo get pods
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo logs deployment/rbac-hello --tail=3
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo create configmap dev-note --from-literal=message='Created by dev'
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo scale deployment/rbac-hello --replicas=2
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo rollout status deployment/rbac-hello
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo scale deployment/rbac-hello --replicas=1
oc --kubeconfig=.rbac-state/dev.kubeconfig auth can-i create pods/exec -n rbac-demo
oc --kubeconfig=.rbac-state/dev.kubeconfig -n rbac-demo get secrets
oc --kubeconfig=.rbac-state/dev.kubeconfig get nodes
oc --kubeconfig=.rbac-state/dev.kubeconfig -n default get pods
```

ConfigMap creation and scaling succeed; exec permission says `yes`. The final
three reads are Forbidden. Run expected-denial commands individually rather
than under `set -e`. Pod creation is a trusted developer capability: it can
potentially expose namespace Secrets through mounts, despite denied direct reads.

## 7. Verify operator access

```bash
oc --kubeconfig=.rbac-state/ops.kubeconfig get namespace rbac-demo
oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo get pods
oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo logs deployment/rbac-hello --tail=3
oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo create configmap ops-note --from-literal=message=denied
oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo scale deployment/rbac-hello --replicas=2
oc --kubeconfig=.rbac-state/ops.kubeconfig auth can-i create pods/exec -n rbac-demo
```

Reads succeed. ConfigMap creation and scaling are Forbidden; exec says `no`.
Restart a managed pod through deletion:

```bash
POD="$(oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo get pods -l app=rbac-hello -o jsonpath='{.items[0].metadata.name}')"
oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo delete pod "$POD"
oc --kubeconfig=.rbac-state/ops.kubeconfig -n rbac-demo get pods -w
```

The Deployment creates a replacement. Ctrl+C stops the watch, not the workload.
An unmanaged standalone pod would not automatically return after deletion.

## 8. Verify project administrator access

```bash
oc --kubeconfig=.rbac-state/admin.kubeconfig auth can-i create roles.rbac.authorization.k8s.io -n rbac-demo
oc --kubeconfig=.rbac-state/admin.kubeconfig -n rbac-demo get roles,rolebindings
oc --kubeconfig=.rbac-state/admin.kubeconfig auth can-i get secrets -n rbac-demo
oc --kubeconfig=.rbac-state/admin.kubeconfig get nodes
```

Namespace administration is allowed; cluster Nodes are Forbidden. RBAC
escalation checks still prevent granting permissions beyond this account's
authority. Check the separate inherited project-creation policy:

```bash
oc --kubeconfig=.rbac-state/dev.kubeconfig auth can-i create projectrequests.project.openshift.io
```

A `yes` can come from the existing `self-provisioners` binding. This exercise
does not change that shared policy or create any additional projects.

## 9. Use the portal

Discover its address as the original cluster administrator:

```bash
oc --kubeconfig="$ADMIN_KUBECONFIG" -n openshift-console get route console -o jsonpath='{.spec.host}{"\n"}'
```

1. Open the returned HTTPS address in a browser with working cluster DNS.
2. Use a private session and select identity provider **rbac-training**.
3. Log in as `admin` with its chosen password. Click **Skip tour** if shown.
4. Choose `rbac-demo`; open **Workloads → Pods** and a pod's **Logs** tab.
5. Log out and repeat as `dev`: Deployment editing/scaling and pod terminal
   access are permitted in the project; direct Secret reads are not.
6. Log out and repeat as `ops`: pod/log reads and pod deletion are permitted;
   Deployment editing/scaling and pod terminal access are denied.

Confirm the active username in the user menu. Private windows can share cookies;
log out or close the private session between accounts. Menu labels vary by
release. Switching console perspectives does not grant permissions; the API
enforces access even if an unauthorized action is hidden rather than shown.

Portal evidence: [admin](evidence/admin-portal.png), [dev](evidence/dev-portal.png),
[ops](evidence/ops-portal.png). The first-login tour appears in these captures.

## 10. Remove the provider before deleting users

```bash
export KUBECONFIG="$ADMIN_KUBECONFIG"
oc whoami
oc edit oauth cluster
```

Remove **only** the `rbac-training` item from `spec.identityProviders`; preserve
other providers and settings. Monitor the authentication operator:

```bash
oc get co authentication
oc -n openshift-authentication rollout status deployment/oauth-openshift --timeout=300s
```

Refresh a private portal login page and confirm that `rbac-training` is gone.
Attempt a fresh login using a new kubeconfig and the previously working password:

```bash
oc --kubeconfig=.rbac-state/rejected.kubeconfig login "$API_URL" -u admin --insecure-skip-tls-verify=true
```

Expect Unauthorized/HTTP 401. If login still succeeds, wait and retry. Do not
continue until authentication is available and the credentials are rejected:
an old OAuth pod could otherwise recreate a deleted User/Identity. A connection
error alone is not proof of revocation.

## 11. Revoke tokens and remove the exercise resources

The initial collision checks must have established that these usernames belong
only to this exercise. As the original cluster administrator:

```bash
for RESOURCE in oauthaccesstokens oauthauthorizetokens oauthclientauthorizations; do
  oc get "$RESOURCE" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.userName}{"\n"}{end}' |
    awk '$2 == "admin" || $2 == "dev" || $2 == "ops" {print $1}' |
    while IFS= read -r OBJECT; do
      oc delete "$RESOURCE" "$OBJECT"
    done
done

oc delete identity rbac-training:admin rbac-training:dev rbac-training:ops --ignore-not-found
oc delete user admin dev ops --ignore-not-found
oc -n openshift-config delete secret rbac-training-htpasswd --ignore-not-found
oc delete namespace rbac-demo --ignore-not-found --wait=true --timeout=180s
```

Namespace deletion removes its Deployment, pods, ConfigMaps, Roles and
RoleBindings. Deleting a User alone is not credential revocation. Normal audit
history is retained.

## 12. Verify cleanup and remove local files

```bash
oc get users admin dev ops --ignore-not-found
oc get identities rbac-training:admin rbac-training:dev rbac-training:ops --ignore-not-found
oc get namespace rbac-demo --ignore-not-found
oc -n openshift-config get secret rbac-training-htpasswd --ignore-not-found
oc get oauth cluster -o jsonpath='{range .spec.identityProviders[*]}{.name}{"\n"}{end}' > .rbac-state/providers-after.txt
diff .rbac-state/providers-before.txt .rbac-state/providers-after.txt
oc get co authentication
```

No exercise resources should remain. The provider-name comparison should have
no differences unless another administrator changed providers concurrently;
review such changes instead of overwriting them. Verify old tokens are rejected:

```bash
oc --kubeconfig=.rbac-state/admin.kubeconfig whoami
oc --kubeconfig=.rbac-state/dev.kubeconfig whoami
oc --kubeconfig=.rbac-state/ops.kubeconfig whoami
```

All three should return Unauthorized. Close the account browser sessions and,
with the original administrator context still selected, remove only local
exercise files:

```bash
rm -f -- .rbac-state/*.kubeconfig .rbac-state/users.htpasswd \
  .rbac-state/htpasswd-secret.yaml .rbac-state/oauth-before.yaml \
  .rbac-state/providers-before.txt .rbac-state/providers-after.txt
rmdir .rbac-state
```

If `rmdir` reports remaining files, inspect them. Do not recursively delete an
unknown directory. The original administrator kubeconfig is not removed.

## Validation evidence

The YAML and permissions were verified using actual CLI and portal logins,
allowed/denied actions, pod replacement and complete cleanup. This document
exposes the individual commands instead of requiring a custom helper. Sanitized
outcomes: [CLI](evidence/cli-tests.json), [portal](evidence/portal-tests.json),
[cleanup](evidence/cleanup-tests.json).

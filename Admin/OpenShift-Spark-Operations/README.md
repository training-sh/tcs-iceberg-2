# Spark operations on OpenShift / OKD

One workshop, 210 minutes. Use a terminal and browser inside the Linux VM. The three notebooks run on the existing Jupyter Python kernel and Spark standalone cluster hosted on OKD.

| Segment | Minutes | Deliverable |
|---|---:|---|
| Environment checks and access | 20 | Verified context, workload inventory, notebook files |
| [Part 1: Run and inspect](01-run-and-inspect.md) | 45 | Exact data assertions and live application inspection |
| [Part 2: Storage and history](02-storage-and-history.md) | 45 | SeaweedFS, Polaris, history and log evidence |
| Break | 10 | |
| [Part 3: Workers and recovery](03-workers-and-recovery.md) | 45 | Worker lifecycle, recovery and restoration |
| Troubleshooting and review | 45 | Resolve discrepancies and compare evidence |
| Total | 210 | |

Read [VALIDATION.md](VALIDATION.md) for the precise execution boundary. Scaling and failure steps are instructions for a dedicated exercise environment; they were not performed during reference verification. Do not treat a passing normal workload as proof of recovery under failure.

## Discover the environment first

Do not run a startup wrapper or reapply manifests. Locate the installed CLI and choose an existing kubeconfig explicitly. These examples fit the inspected CRC installation; use your actual paths if different.

```bash
command -v oc
ls "$HOME/.crc/bin/oc/oc"
export PATH="$HOME/.crc/bin/oc:$PATH"
# Choose an existing configuration. Do not overwrite it or copy another host's config.
ls -l "$HOME/.kube/config" "$HOME/openshift/.state/admin.kubeconfig" "$HOME/.crc/machines/crc/kubeconfig"
export KUBECONFIG="$HOME/.crc/machines/crc/kubeconfig"
oc config current-context
oc whoami
oc get nodes
export NS=bigdata
oc -n "$NS" get deployment,statefulset,pods,svc,pvc
oc -n "$NS" get events --sort-by=.lastTimestamp
oc -n "$NS" auth can-i get pods
oc -n "$NS" auth can-i create pods/exec
oc -n "$NS" auth can-i create pods/portforward
```

A missing path in `ls` is diagnostic, not a reason to create a cluster. Stop if the API is unavailable, credentials are invalid, or the expected resources are missing. Record the difference before proceeding. Inspect real names and ports instead of substituting arbitrary resources.

```bash
oc -n "$NS" get pod spark-master-0 -o jsonpath='{.spec.containers[*].name}{"\n"}'
oc -n "$NS" get svc spark-master spark-worker seaweedfs polaris -o wide
oc -n "$NS" get sts spark-worker -o jsonpath='{.spec.replicas}{"\n"}'
oc -n "$NS" get pods -o wide
oc -n "$NS" get resourcequota,limitrange
oc adm top nodes
oc adm top pods -n "$NS"
```

Metrics require the existing monitoring stack and appropriate permissions. Their absence does not prevent `oc logs`, events or Spark execution. One OKD node can host several Spark workers; adding Spark workers does not add physical capacity or OKD nodes.

## Configuration and notebook placement

`config.json` holds non-secret endpoints and maps credential names to the existing Jupyter environment. The notebooks retrieve credential values using that mapping; no credential literal belongs in the JSON or notebook. Existing Kubernetes Secrets should supply the environment. Inspect Secret references without printing their values:

```bash
oc -n "$NS" get sts spark-master -o jsonpath='{range .spec.template.spec.containers[?(@.name=="jupyter")].env[*]}{.name}{" <- "}{.valueFrom.secretKeyRef.name}{"/"}{.valueFrom.secretKeyRef.key}{"\n"}{end}'
oc -n "$NS" exec spark-master-0 -c jupyter -- python3 -c 'import os; keys=["AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","POLARIS_CLIENT_ID","POLARIS_CLIENT_SECRET"]; print({k:bool(os.getenv(k)) for k in keys})'
```

Expect all four presence checks to be `True`. If names differ, update only the mapping in the local JSON. If values are absent, have the environment owner correct the existing Secret wiring before proceeding. Changing a Secret does not update an already-running process's environment. Never print the full environment, Secret data, SparkConf, authentication response or configuration files containing secrets.

Copy this folder to the VM, then place it on the notebook PVC with direct `oc` commands. The host filesystem is not automatically mounted in Jupyter.

```bash
cd ~/openshift
oc -n "$NS" exec spark-master-0 -c jupyter -- mkdir -p /workspace/user_notebooks/spark-operations-workshop
oc -n "$NS" cp ./spark-operations-workshop/. spark-master-0:/workspace/user_notebooks/spark-operations-workshop -c jupyter
```

Open the folder in Jupyter so `config.json` is beside the notebooks. Use a fresh kernel for each notebook and stop the preceding Spark session. Each notebook generates a random `ops_...` ID, writes a run record beside itself, and uses a unique SeaweedFS prefix. Spark event logs use the existing shared history prefix. Part 2 creates and then purges its own Polaris table and namespace.

For a verified hands-on log-viewing walkthrough, use [Grafana and Loki](04-grafana-loki.md) within Part 2 and the troubleshooting block. It covers start/stop commands, forwarding, Explore, LogQL, dashboards and comparison with `oc logs`.

## Service ports and OpenShift routes

Routes provide stable browser hostnames through the existing OpenShift router. They do not start services. The following ports were read from the live Services, rather than inferred from old manifests.

| Endpoint | Existing Service | Service port name | Port | Route use |
|---|---|---|---:|---|
| Jupyter | spark-master | jupyter | 8888 | UI; existing Jupyter authentication still applies |
| Spark master UI | spark-master | master-ui | 8080 | Master status |
| Spark History Server | spark-master | history-ui | 18080 | Completed applications |
| Live Spark driver UI | spark-master | driver-ui | 4040 | Only while a notebook SparkContext is alive |
| Spark worker UI | spark-worker | worker-ui | 8081 | Use the per-worker Service below |
| Grafana | grafana | http | 3000 | Login and dashboards |
| Loki | loki | http | 3100 | API and readiness; no standalone dashboard |
| SeaweedFS S3 | seaweedfs | s3 | 8333 | S3-compatible API |
| SeaweedFS filer | seaweedfs | filer | 8888 | Filer HTTP interface |
| SeaweedFS admin | seaweedfs | admin | 23646 | Admin interface |
| Polaris catalog | polaris | api | 8181 | REST catalog API under /api/catalog |
| Polaris management | polaris | management | 8182 | Readiness under /q/health/ready |
| Alloy | alloy | http | 12345 | Collector diagnostics |
| Spark master RPC | spark-master | master | 7077 | Internal Spark protocol; no HTTP route |
| SeaweedFS master / volume | seaweedfs | master / volume | 9333 / 9340 | Internal storage endpoints; no route supplied |
| SeaweedFS gRPC | seaweedfs | master-grpc / volume-grpc / filer-grpc | 19333 / 19340 / 18888 | Internal endpoints; no route supplied |

The notebooks continue to use `spark://spark-master:7077` and internal storage/catalog URLs. Browser routes do not replace Spark RPC, driver/block-manager connections or internal storage traffic.

### Confirm the account and existing resources

Grafana API authentication was verified with **team / team1234**. Its existing Secret references also match those values. The route adds no login layer: these are Grafana credentials, not credentials automatically shared by Jupyter, Polaris, S3 or Spark UIs. Notebooks continue retrieving their API credentials from the configured environment.

```bash
export NS=bigdata
oc -n "$NS" get svc spark-master spark-worker grafana loki seaweedfs polaris alloy
oc -n "$NS" get routes
oc get ingress.config.openshift.io cluster -o jsonpath='{.spec.domain}{"\n"}'
```

The inspected ingress domain is `apps-crc.testing`; do not hard-code it for other clones. The YAML omits `spec.host`, letting the router generate names for the current ingress domain. After applying, discover actual hosts with `oc get routes`.

The existing `seaweedfs-s3` route targets the **filer** port 8888 despite its name. These examples leave it unchanged and use distinct `ops-...` names with explicit port mappings.

### Create the main route YAML from the terminal

The checked-in [routes.yaml](routes.yaml) contains seven routes and one per-worker Service. To recreate that exact file, paste the following Bash block. A quoted heredoc writes literal YAML without expanding shell variables; it is easier to copy than a multiline echo command.

```bash
cat > routes.yaml <<'YAML'
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-jupyter
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: spark-master
  port:
    targetPort: jupyter
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-spark-master
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: spark-master
  port:
    targetPort: master-ui
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-spark-history
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: spark-master
  port:
    targetPort: history-ui
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-spark-driver
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: spark-master
  port:
    targetPort: driver-ui
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: v1
kind: Service
metadata:
  name: ops-spark-worker-0
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
spec:
  selector:
    statefulset.kubernetes.io/pod-name: spark-worker-0
  ports:
  - name: worker-ui
    port: 8081
    targetPort: worker-ui
    protocol: TCP
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-spark-worker-0
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: ops-spark-worker-0
  port:
    targetPort: worker-ui
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-grafana
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: grafana
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-loki
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: loki
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
YAML
```

Each Route uses HTTPS edge termination with HTTP redirected to HTTPS. The router's existing default certificate is used; no certificate or deployment configuration is replaced. Trust the lab ingress CA on the browser/client. Routes themselves do not add authentication. In this private lab, the Spark status pages and the existing Loki API have no additional route login; anyone able to reach those route hosts can access their exposed functions.

The worker Service selects `spark-worker-0` by its StatefulSet pod-name label. This keeps executor log links on that worker when more workers exist. A route to the original shared `spark-worker` Service could otherwise send successive requests to different workers. For another worker, copy that Service/Route pair and change both object names and the pod-name selector to the corresponding worker ordinal.



### Validate and apply using oc

Run these commands only when you intend to create the routes in your own lab. The supplied YAML was server-dry-run validated during preparation; it has not been applied to the reference cluster.

```bash
oc apply --dry-run=client -f routes.yaml
oc apply --dry-run=server -f routes.yaml
oc apply -f routes.yaml
oc -n "$NS" get routes -l app.kubernetes.io/part-of=spark-operations-workshop
oc -n "$NS" describe route ops-grafana
oc -n "$NS" get endpoints ops-spark-worker-0
```




For those who has not done hands on for creating seaweed fs route only

```
cat > routes-seweedfs.yaml <<'YAML'
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-seaweed-admin
  namespace: bigdata
spec:
  to:
    kind: Service
    name: seaweedfs
  port:
    targetPort: admin
  wildcardPolicy: None
YAML

```

```
oc apply -f routes-seweedfs.yaml
```

```
oc -n bigdata get route ops-seaweed-admin \
  -o jsonpath='http://{.spec.host}{"\n"}'
```


Expect a route admission condition of `Admitted=True` and a ready worker endpoint. A Route may be admitted even when its backend has no ready endpoint. Check both.

```bash
GRAFANA_HOST=$(oc -n "$NS" get route ops-grafana -o jsonpath='{.spec.host}')
HISTORY_HOST=$(oc -n "$NS" get route ops-spark-history -o jsonpath='{.spec.host}')
LOKI_HOST=$(oc -n "$NS" get route ops-loki -o jsonpath='{.spec.host}')
printf 'Grafana: https://%s/\nHistory: https://%s/\nLoki: https://%s/ready\n' "$GRAFANA_HOST" "$HISTORY_HOST" "$LOKI_HOST"
getent hosts "$GRAFANA_HOST"
curl -fsS "https://$GRAFANA_HOST/api/health"
curl -fsS "https://$LOKI_HOST/ready"
```

If curl cannot verify the lab certificate, configure its CA trust. For a one-time reachability diagnostic without credentials, `curl -kI "https://$GRAFANA_HOST/"` distinguishes certificate trust from network reachability; it does not validate the certificate.

Open the returned Grafana URL and sign in with team / team1234. Use the returned Jupyter, master, history and worker hostnames from `oc get routes`; no per-UI port-forward terminal is needed once router access and DNS work. Existing port-forward instructions remain a fallback.

### Router reachability is separate from Tailscale SSH

Being able to SSH to the VM over Tailscale does not establish a route to the nested CRC ingress. The browser must resolve each route hostname to the reachable ingress address and connect to its HTTPS port. Start in the VM browser, where CRC DNS is normally configured. An existing admitted route was tested separately during preparation; see VALIDATION for its result. Do not map the route hosts to the Tailscale VM IP unless that host actually forwards 443 to the CRC router.

For diagnosis, inspect `getent hosts HOST`, `oc -n openshift-ingress get svc,pods` and `oc -n bigdata describe route ROUTE_NAME`. A certificate error, DNS failure, 503 from an unready backend and application authentication failure are different checks.

### Spark UI behavior behind a route

The live-driver route targets 4040. Run one kernel at a time and confirm `spark.sparkContext.uiWebUrl`; a driver that chooses 4041 is not served by this 4040 mapping. Stop the old SparkContext and restart the kernel to free 4040. A stopped context correctly leaves no live driver UI; completed applications belong in History Server.

Separate hostnames serve each UI at its root path, avoiding path-prefix rewrites. Master-page links can still advertise internal worker/driver addresses because a Route does not rewrite HTML links. Open the corresponding worker/driver route directly. If a deployment needs automatic proxy-aware link generation, review the documented Spark UI reverse-proxy settings before changing it; no Spark daemon configuration was modified here.

### Optional API and diagnostics routes

[routes-apis.yaml](routes-apis.yaml) provides six additional routes. These expose API/admin/diagnostic endpoints, including unauthenticated interfaces in the existing lab configuration. Apply only the endpoints you intend to use on your lab network. The S3 route points to 8333; the filer route points to 8888. A browser opening the S3 root may receive an authentication error rather than a bucket dashboard.

```bash
cat > routes-apis.yaml <<'YAML'
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-seaweed-s3
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: seaweedfs
  port:
    targetPort: s3
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-seaweed-filer
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: seaweedfs
  port:
    targetPort: filer
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-seaweed-admin
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: seaweedfs
  port:
    targetPort: admin
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-polaris-api
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: polaris
  port:
    targetPort: api
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-polaris-health
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: polaris
  port:
    targetPort: management
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ops-alloy
  namespace: bigdata
  labels:
    app.kubernetes.io/part-of: spark-operations-workshop
  annotations:
    haproxy.router.openshift.io/timeout: 300s
spec:
  to:
    kind: Service
    name: alloy
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
  wildcardPolicy: None
YAML
oc apply --dry-run=server -f routes-apis.yaml
# Apply only when these additional endpoints are required.
oc apply -f routes-apis.yaml
oc -n "$NS" get routes -l app.kubernetes.io/part-of=spark-operations-workshop
```

Polaris OAuth/catalog calls still require the appropriate API credentials; a readiness endpoint is not a login page. Keep the notebooks on internal Polaris and SeaweedFS endpoints. Any external S3 client must use the actual routed HTTPS hostname and path-style addressing with the proper S3 credentials; route creation does not change the server's identity configuration.

### Remove only the supplied route resources

```bash
oc delete -f routes.yaml
# Only if the optional API routes were applied:
oc delete -f routes-apis.yaml
```

These files contain only workshop Routes and the per-worker UI Service. Deleting them does not stop Grafana, Spark or storage services and does not delete PVCs. They do not overwrite the pre-existing Jupyter or SeaweedFS routes.

Route configuration reference: [OpenShift route configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/networking/configuring-routes). Spark proxy settings: [Spark configuration](https://spark.apache.org/docs/3.5.6/configuration.html).

## Troubleshooting and review: 45 minutes

Spend 15 minutes checking context, readiness, storage and credentials; 15 minutes matching an application ID across the driver, master, executor logs and history; and 15 minutes resolving one observed discrepancy and confirming replica restoration.

- `Forbidden`: use `oc auth can-i` for the failed operation; do not grant broad access as a workaround.
- `Pending`: inspect `oc describe pod`, events, quotas, node capacity and PVC binding.
- Authentication failure: verify environment presence, endpoint and catalog warehouse; do not paste secrets into outputs.
- Job waits indefinitely: inspect worker registration and available executor memory/cores in the master UI. Existing applications may hold the only worker.
- Wrong Spark master or UI port: stop the old session and restart the notebook kernel. A port conflict can move the driver UI to 4041 or above.
- Empty history: confirm event logging before creating SparkContext, inspect the event path and history logs, and stop the application normally. Wait for the existing history refresh interval.
- Port busy: choose a free local port. Existing managed forwards may already own the familiar ports.
- `oc logs --previous` unavailable: there is no retained prior container instance. Deleted pods and rotated logs require previously configured centralized collection.

Retain run IDs and application IDs. Review executed notebook outputs before sharing them. Temporary data is retained unless the explicit cleanup in Part 3 is run; existing history retention applies independently.

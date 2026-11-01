# Grafana and Loki: collect, search and compare Spark logs

Use this as the logging section of Part 2 and, if needed, the troubleshooting block. Allow 15?20 minutes. It uses the existing installed services; no installer, startup wrapper, new manifest or additional script is required.

## 1. Inspect and start the existing services

```bash
export NS=bigdata
oc -n "$NS" get sts grafana loki alloy
oc -n "$NS" get svc grafana loki
oc -n "$NS" get pvc
# Record current counts before changing them.
oc -n "$NS" get sts grafana loki alloy -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas
oc -n "$NS" scale sts/loki sts/alloy sts/grafana --replicas=1
oc -n "$NS" rollout status sts/loki --timeout=180s
oc -n "$NS" rollout status sts/alloy --timeout=180s
oc -n "$NS" rollout status sts/grafana --timeout=180s
oc -n "$NS" get pods -l 'app in (grafana,loki,alloy)'
```

Expect Loki and Alloy to be Ready, and all Grafana pod containers Ready. In the verified environment Grafana is `2/2` because its pod includes a metrics proxy. Loki stores indexed logs; Alloy reads existing project container logs and sends them to Loki; Grafana queries Loki. Starting Grafana alone does not start collection.

For stable hostname access, the [README route section](README.md#service-ports-and-openshift-routes) includes route YAML, a copyable Bash heredoc, and oc validation/apply steps. Grafana authentication is verified as **team / team1234**. Routes remain unapplied on the reference cluster.

## 2. Open Grafana using direct oc forwarding

Keep this command open in a separate VM terminal:

```bash
oc -n bigdata port-forward --address=127.0.0.1 svc/grafana 23000:3000
```

Open http://127.0.0.1:23000/ in the VM browser and sign in using the configured Grafana account. Existing Secret references can be inspected without exposing values:

```bash
oc -n "$NS" get sts grafana -o jsonpath='{range .spec.template.spec.containers[?(@.name=="grafana")].env[*]}{.name}{" <- "}{.valueFrom.secretKeyRef.name}{"/"}{.valueFrom.secretKeyRef.key}{"\n"}{end}'
```

The inspected installation references `lab-credentials` keys `database-user` and `database-password`. Use the configured account supplied for your VM; do not paste credentials into notebooks or runbooks.

In another terminal, check Grafana's unauthenticated health endpoint:

```bash
curl -fsS http://127.0.0.1:23000/api/health
```

Expect HTTP success and `database: ok`. Under Connections / Data sources, open Loki and run its connection check. The verified result is `Data source successfully connected`.

## 3. Find a Spark application's logs in Explore

Run Part 1's notebook if no recent application exists. Retain its printed application ID. In Grafana, open Explore, select the Loki datasource and set the time range to Last 1 hour. Use the code editor for these LogQL expressions:

```logql
{namespace="bigdata",container="spark-master"}
```

Narrow to the application ID printed by your notebook:

```logql
{namespace="bigdata",container="spark-master"} |= "YOUR_APPLICATION_ID"
```

Replace `YOUR_APPLICATION_ID` with the full `app-...` value. Expected messages include registration, scheduling and removal/unregistration after `spark.stop()`. Expand a returned line and inspect the namespace, pod and container labels.

Compare worker and history activity:

```logql
{namespace="bigdata",container="spark-worker"}
```

```logql
{namespace="bigdata",container="spark-history"}
```

Search for errors without assuming every match is a new application failure:

```logql
{namespace="bigdata"} |~ "(?i)error|exception|failed"
```

Use the time range, pod and application ID to explain each result. A currently stopped service will not emit new logs. There can be a short collection delay after an application finishes.

## 4. Compare Grafana with oc logs

```bash
oc -n "$NS" logs spark-master-0 -c spark-master --since=1h --tail=100
oc -n "$NS" logs spark-worker-0 -c spark-worker --since=1h --tail=100
oc -n "$NS" logs spark-master-0 -c spark-history --since=1h --tail=60
oc -n "$NS" logs alloy-0 --tail=40
oc -n "$NS" logs loki-0 --tail=40
```

Match one Spark line by application ID and message in both Grafana and `oc logs`. This demonstrates collection of real container stdout/stderr rather than only an empty dashboard.

The verified query through Grafana returned seven master-container lines for the Part 1 application. Application IDs differ on every run, so reproduce the check with your own ID.

## 5. Query Loki directly through oc forwarding

Keep another forwarding terminal open:

```bash
oc -n bigdata port-forward --address=127.0.0.1 svc/loki 23100:3100
```

In a separate terminal:

```bash
curl -fsS http://127.0.0.1:23100/ready
curl -fsS http://127.0.0.1:23100/loki/api/v1/labels | python3 -m json.tool
curl -fsSG http://127.0.0.1:23100/loki/api/v1/query_range   --data-urlencode 'query={namespace="bigdata",container="spark-master"}'   --data-urlencode 'limit=20' | python3 -m json.tool
```

Expect readiness success, labels including namespace/pod/container, and query status `success` with non-empty streams when Spark emitted logs within the default recent time window. Loki is an API; Grafana supplies the interactive log viewer. Stop either manual forwarding command with Ctrl+C when finished; that closes only the local tunnel.

## 6. Open the provisioned dashboards

Under Dashboards, open the existing Training folder:

- Big-data application logs: select a recent time window, project and pod/container filters where available; compare it with Explore.
- Spark monitoring: inspect its panels, but distinguish logs from Prometheus-based metrics.

The installation also contains OpenShift big-data metrics, Trino monitoring and Airflow monitoring dashboards. Their presence does not prove their backing metric series are available.

**Verified limitation:** Loki health and log queries pass, but the Prometheus datasource returns HTTP 503 in this environment. CPU, memory and application-metric panels can therefore show errors or no data. Starting Grafana/Loki/Alloy does not resume or repair the native monitoring stack. No native monitoring configuration was changed for this logging exercise.

## 7. Understand which logs are collected

| Evidence | Available in the current Loki collection? | How to inspect |
|---|---|---|
| Spark master/worker/history container stdout/stderr | Yes | Grafana Explore or oc logs |
| Notebook Python driver log file | No automatic file ingestion | Part 1's explicit log file and notebook outputs |
| Executor stdout/stderr files under /opt/spark/work | No automatic file ingestion | Worker UI or oc exec, as shown in Part 2 |
| Spark jobs/stages/tasks | Event history, separate from Loki | Spark History Server |
| API-server container and kubelet logs | Outside this project collector's scope | Authorized direct oc commands in Part 2 |
| Kubernetes events | Not automatically ingested by this collector | oc get events and oc describe pod |

A line in a Spark daemon log is not the complete driver's or executor's application log. Keep the matching application ID when comparing these sources.

## 8. Stop, resume and restart explicitly

These lifecycle examples are provided for the exercise; they were not used to perform a persistence/failure test. The verified services have been left running as requested. Before stopping them, record counts and consider any other active log users.

```bash
# Pause new collection; previously stored logs remain queryable.
oc -n "$NS" scale sts/alloy --replicas=0
oc -n "$NS" wait --for=delete pod/alloy-0 --timeout=180s
# Stop the viewer and log storage while retaining their PVCs.
oc -n "$NS" scale sts/grafana sts/loki --replicas=0
# Resume the existing services.
oc -n "$NS" scale sts/loki sts/alloy sts/grafana --replicas=1
oc -n "$NS" rollout status sts/loki --timeout=180s
oc -n "$NS" rollout status sts/alloy --timeout=180s
oc -n "$NS" rollout status sts/grafana --timeout=180s
```

To restart one service without deleting its PVC:

```bash
oc -n "$NS" rollout restart sts/alloy
oc -n "$NS" rollout status sts/alloy --timeout=180s
```

Pausing collection may lose logs that rotate or disappear before collection resumes. PVC retention is not a backup. Existing Loki retention is finite; inspect its installed configuration when changing the exercise timeframe. Restore your recorded replica counts if the exercise requires its original service state.

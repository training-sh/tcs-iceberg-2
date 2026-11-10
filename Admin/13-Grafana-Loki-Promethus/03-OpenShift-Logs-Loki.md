# OpenShift logs, Alloy and Loki

OpenShift exposes application stdout/stderr through `oc logs`. Logs rotate, and deleted pod logs may become unavailable. Centralized logging stores a separate copy for searching across pods and restarts within retention.

Alloy reads pod logs in `bigdata`, attaches labels and sends them to Loki. Loki stores labeled streams; Grafana searches them using LogQL. See [Loki concepts](https://grafana.com/docs/loki/latest/get-started/).

## Inspect container logs

```bash
oc -n bigdata get pods
oc -n bigdata logs statefulset/loki --tail=50
oc -n bigdata logs statefulset/alloy --tail=50
oc -n bigdata logs grafana-0 -c grafana --tail=50
oc -n bigdata get events --sort-by=.metadata.creationTimestamp
```

Substitute an actual application pod and container:

```bash
POD_NAME=replace-with-pod-name
CONTAINER_NAME=replace-with-container-name
oc -n bigdata logs "$POD_NAME" -c "$CONTAINER_NAME" --tail=100 --timestamps
oc -n bigdata logs "$POD_NAME" -c "$CONTAINER_NAME" --previous --tail=100
```

`--previous` reads the previous terminated container instance in that same pod when available. It does not retrieve arbitrary deleted pods. Use `-f` to follow logs and Ctrl+C to stop following.

## Search Loki

Follow the README to start services. Open Grafana **Explore**, choose **Loki**, select code mode and the last 15 minutes:

```logql
{namespace="bigdata"}
```

```logql
{namespace="bigdata",container="namenode"}
```

```logql
{namespace="bigdata"} |~ "(?i)error|exception|failed"
```

Discover actual pod/container values using the label browser. `|=` matches literal text; `|~` matches a regular expression. Count matching entries over five-minute windows:

```logql
sum(count_over_time({namespace="bigdata"} |~ "(?i)error|exception|failed" [5m]))
```

## Generate a log marker

Use an image already running in the namespace. The temporary pod writes a message and sleeps without altering application data:

```bash
LOG_IMAGE=$(oc -n bigdata get statefulset grafana -o jsonpath='{.spec.template.spec.containers[?(@.name=="native-metrics-proxy")].image}')
oc -n bigdata run observability-log-demo --restart=Never --image="$LOG_IMAGE" \
  --command -- /bin/sh -c 'echo "observability-demo: sample application log"; sleep 300'
oc -n bigdata wait --for=condition=Ready pod/observability-log-demo --timeout=120s
oc -n bigdata logs observability-log-demo
```

Allow collection time, then query:

```logql
{namespace="bigdata"} |= "observability-demo: sample application log"
```

Check the forwarded API and remove the temporary pod:

```bash
curl -fsS -G http://127.0.0.1:13100/loki/api/v1/query_range \
  --data-urlencode 'query={namespace="bigdata"} |= "observability-demo: sample application log"' \
  --data-urlencode 'since=15m' --data-urlencode 'limit=20'
oc -n bigdata delete pod observability-log-demo
```

Stored logs remain searchable until retention removes them. Loki retention is configured as 24 hours. PVCs preserve data across pod recreation but are not backups. Pausing Alloy stops collection; rotated or deleted logs during that pause may be lost.

Internal application files and Spark event history are separate from standard container logs. The configured stack does not collect cluster-wide infrastructure, host journals or audit logs. OpenShift cluster logging, if installed, is a separate deployment; inspect `oc get pods -n openshift-logging`. Its absence does not prevent `oc logs` from working.

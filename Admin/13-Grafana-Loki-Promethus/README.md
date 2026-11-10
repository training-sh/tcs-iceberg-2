# Grafana, Loki and Prometheus on OpenShift

Run these Bash commands in the Ubuntu VM terminal. Use `~/openshift` as the base and the browser on the VM to open portals. This tutorial follows the existing `observability/` deployment.

## 1. Check the cluster and namespaces

```bash
cd ~/openshift
export PATH="$HOME/.crc/bin/oc:$PATH"
crc status
oc whoami
oc project bigdata
oc get co monitoring
oc -n openshift-monitoring get pods
oc -n openshift-user-workload-monitoring get pods
oc -n bigdata get statefulset/grafana statefulset/loki statefulset/alloy deployment/bigdata-metrics
oc -n bigdata get svc grafana prometheus loki
oc -n bigdata get pvc
```

If CRC is stopped, use `bash ~/openshift/start-lab.sh` and wait for the API. If login has expired, use the prepared OpenShift login procedure; `crc console --credentials` displays CRC login details locally.

| Namespace | Components and purpose |
|---|---|
| `openshift-monitoring` | Platform Prometheus, Cluster Monitoring Operator, Thanos, Alertmanager and exporters |
| `openshift-user-workload-monitoring` | User-workload Prometheus and controllers for application metric scraping |
| `bigdata` | Grafana, Loki, Alloy, application metrics exporter and project-scoped metrics proxy |

The `bigdata/prometheus` Service is a native Prometheus query API proxy inside the Grafana pod. Its root displays JSON information. Grafana and OpenShift **Observe → Metrics** provide interactive metrics interfaces.

## 2. Start the existing optional services

These commands start application observability without restarting CRC:

```bash
cd ~/openshift
if [ -f "$HOME/openshift/.state/observability/pause.json" ]; then
  bash observability/monitoring-control.sh start
fi
oc -n bigdata scale statefulset/loki statefulset/alloy statefulset/grafana --replicas=1
oc -n bigdata scale deployment/bigdata-metrics --replicas=1
oc -n bigdata rollout status statefulset/loki --timeout=600s
oc -n bigdata rollout status statefulset/alloy --timeout=600s
oc -n bigdata rollout status statefulset/grafana --timeout=600s
oc -n bigdata rollout status deployment/bigdata-metrics --timeout=600s
oc -n bigdata get pods -o wide
```

Grafana has two containers: its UI and the metrics proxy. Both must be ready. Leave native monitoring under operator management. If resources are **NotFound**, see [initial setup](06-Operations.md); that procedure can restart CRC and belongs outside an active session.

## 3. Port forwarding

Run each command in a separate VM terminal tab and keep it running:

```bash
# Terminal 1
oc -n bigdata port-forward --address 127.0.0.1 svc/grafana 13000:3000
```

```bash
# Terminal 2
oc -n bigdata port-forward --address 127.0.0.1 svc/prometheus 19090:9090
```

```bash
# Terminal 3
oc -n bigdata port-forward --address 127.0.0.1 svc/loki 13100:3100
```

| Component | VM browser URL | Expected result |
|---|---|---|
| Grafana | `http://127.0.0.1:13000` | Login and dashboards |
| Prometheus proxy | `http://127.0.0.1:19090` | Query API information |
| Loki | `http://127.0.0.1:13100/ready` | Readiness; search logs through Grafana |

If a port is occupied, test its URL first: `bigdata-uis.service` may already provide forwarding. Inspect `ss -ltnp` or choose a free local port such as `13001:3000`. Ctrl+C stops a forward. Restart forwarding after its selected pod is recreated.

```bash
curl -fsS http://127.0.0.1:13000/api/health
curl -fsS -G http://127.0.0.1:19090/api/v1/query --data-urlencode 'query=up{namespace="bigdata"}'
curl -fsS http://127.0.0.1:13100/ready
```

Sign in to Grafana with the configured lab account. Initial credentials come from Secret `lab-credentials`, keys `database-user` and `database-password`. A password changed later in Grafana is retained in its database.

## 4. Create HTTP routes

Routes expose the existing Services through the OpenShift ingress router without a running port-forward terminal. These routes use HTTP with no TLS section. Loki and the metrics proxy have no browser login; use these entry points only within the private lab network.

Create the complete `metrics-logs.yaml` with `cat`, then apply it:

```bash
mkdir -p ~/openshift/13-Grafana-Loki-Promethus
cd ~/openshift/13-Grafana-Loki-Promethus
cat > metrics-logs.yaml <<'EOF'
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: grafana-http
  namespace: bigdata
spec:
  to:
    kind: Service
    name: grafana
  port:
    targetPort: http
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: prometheus-api-http
  namespace: bigdata
spec:
  to:
    kind: Service
    name: prometheus
  port:
    targetPort: http
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: loki-http
  namespace: bigdata
spec:
  to:
    kind: Service
    name: loki
  port:
    targetPort: http
EOF
oc apply --dry-run=server -f metrics-logs.yaml
oc apply -f metrics-logs.yaml
oc -n bigdata get routes grafana-http prometheus-api-http loki-http
for route in grafana-http prometheus-api-http loki-http; do
  host=$(oc -n bigdata get route "$route" -o jsonpath='{.spec.host}')
  echo "$route: http://$host"
done
```

Open the printed Grafana URL. Use the API paths for the other two routes:

```bash
METRICS_HOST=$(oc -n bigdata get route prometheus-api-http -o jsonpath='{.spec.host}')
LOKI_HOST=$(oc -n bigdata get route loki-http -o jsonpath='{.spec.host}')
curl -fsS -G "http://$METRICS_HOST/api/v1/query" --data-urlencode 'query=up{namespace="bigdata"}'
curl -fsS "http://$LOKI_HOST/ready"
oc -n bigdata describe route grafana-http
```

The router assigns hostnames because `spec.host` is omitted. Check admission in `describe route`. The browser must resolve these names and reach CRC ingress. Tailscale connectivity to the outer VM does not automatically configure CRC DNS or routing on another computer. Use the VM browser with its prepared DNS configuration.

## 5. Continue the tutorial

| Guide | Topics |
|---|---|
| [Architecture and telemetry](01-Architecture-Telemetry.md) | Logs, metrics, traces and data paths |
| [Prometheus](02-Prometheus.md) | OpenShift metrics, scraping, ServiceMonitors and PromQL |
| [OpenShift logs and Loki](03-OpenShift-Logs-Loki.md) | Native logs, Alloy, LogQL and a log exercise |
| [Grafana](04-Grafana.md) | Datasources, Explore and panels |
| [OpenShift Telemetry](05-OpenShift-Telemetry.md) | Remote health reporting and local observability |
| [Operations](06-Operations.md) | Initial setup, troubleshooting and pause/resume |

Resource names and ports follow the existing [observability definitions](../observability/README.md). Confirm live readiness using these commands on the VM.

# Expose the observability services with OpenShift Routes

From the lesson directory, run these commands with an OpenShift session that can manage Routes in `bigdata`. The manifest connects the OpenShift router to existing Services.

## Check the current routes

```bash
oc -n bigdata get svc grafana prometheus loki
oc -n bigdata get routes
```

If the required routes already exist, use their current locations. If you only need the Prometheus or Loki query UI, use **Observe → Metrics** in OpenShift or **Explore** in Grafana. Grafana uses the internal Services for its data sources.

## Apply the routes if needed

Apply [routes-grafana-promethus-loki.yaml](routes-grafana-promethus-loki.yaml) when direct ingress access to all three Services is needed. Use private lab ingress for this manifest. The Prometheus proxy and Loki endpoints are reachable without a browser login. Edge TLS encrypts the connection to the router. Applying the manifest creates missing routes and reconciles routes with the same names to HTTPS with HTTP redirects.

```bash
oc apply --dry-run=server -f routes-grafana-promethus-loki.yaml
oc apply -f routes-grafana-promethus-loki.yaml
oc -n bigdata get route ops-grafana prometheus-api-http loki-http
```

## Get the URLs and test access

```bash
for route in ops-grafana prometheus-api-http loki-http; do
  host=$(oc -n bigdata get route "$route" -o jsonpath='{.spec.host}')
  printf '%s: https://%s\n' "$route" "$host"
done
```

| Route | What to open |
| --- | --- |
| `ops-grafana` | The base HTTPS URL for the Grafana login and dashboards |
| `prometheus-api-http` | The base HTTPS URL for API information, or `/api/v1/query` for PromQL requests |
| `loki-http` | The HTTPS URL ending in `/ready` for a readiness check |

Use the assigned route hostnames from a browser or terminal that can resolve them, reach OpenShift ingress and trust its certificate. To verify the APIs:

```bash
prom_host=$(oc -n bigdata get route prometheus-api-http -o jsonpath='{.spec.host}')
loki_host=$(oc -n bigdata get route loki-http -o jsonpath='{.spec.host}')
curl -fsSG "https://$prom_host/api/v1/query" \
  --data-urlencode 'query=up{namespace="bigdata",service="bigdata-metrics"}'
curl -fsS "https://$loki_host/ready"
```

Expect JSON with `status: success` from Prometheus and `ready` from Loki. If a route returns HTTP 503, check its admission and the backing Service endpoints.

```bash
oc -n bigdata describe route ops-grafana
oc -n bigdata get endpointslices
```

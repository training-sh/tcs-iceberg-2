# References

- [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- [Trino Iceberg connector](https://trino.io/docs/current/connector/iceberg.html)
- [Apache Polaris and Trino](https://polaris.incubator.apache.org/guides/trino/)
- [Prometheus scrape configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Grafana configuration](https://grafana.com/docs/grafana/latest/setup-grafana/configure-grafana/)
- [Loki HTTP API](https://grafana.com/docs/loki/latest/reference/loki-http-api/)

Use the supplied image versions and configuration together. The manifests include Trino's required scrape user header and disable Grafana's background plugin preinstallation, keeping the supplied dashboard reproducible.

# Platform prerequisites

The exercise uses an existing Kubernetes/OpenShift namespace named `bigdata` with:

- Ready Spark master and workers, SeaweedFS, Polaris, MySQL and Trino.
- Polaris catalog `training`, configured for `s3://warehouse` and permitted to create the exercise namespaces and tables.
- PVC `spark-notebooks` and service account `bigdata-workloads` compatible with the supplied manifest.
- The Spark image pinned in `spark-job-template.json`, containing the Iceberg, S3A and MySQL JDBC connectors and the `submit` entrypoint.
- Secret `lab-credentials` with the six key names referenced in the manifest. Credential values do not belong in the repository.
- Existing MySQL user `team` and the existing administrative credential used by `prepare-mysql.sh`.
- Python 3, Bash, `flock`, `oc` and the permissions checked by `preflight.py`.
- For optional automation: healthy Airflow 3 and service account `airflow-runner` permitted to create/get Jobs.

Publish this directory's contents as the exercise repository. Attach `movielens-classroom.zip` to its release, retaining the top-level `movielens-classroom` directory. Generated logs and datasets are excluded from the package.

Run one pipeline at a time. The fixed bucket, namespaces, database, volume path and DAG are shared by executions against the same namespace.

# OpenShift getting started

Read these command guides first and run selected blocks in the Linux VM terminal:

1. [01 - CRC commands](../00-Introduction/01-CRC-Commands.md): VM lifecycle, configuration, shell environment, and cluster checks.
2. [02 - OpenShift oc commands](../00-Introduction/02-OC-Commands.md): projects, workloads, logs, networking, storage, and troubleshooting.

The guides include command comments and identify changes and deletion operations. Follow [installation](../00-Introduction/00-Installation.md) and [Bash configuration](../00-bashrc.md) for `.bashrc` and cloned-VM user-session recovery.

## Lesson index

Read these Markdown guides in order and run commands one at a time, checking each result before continuing. Run heredocs and commands continued with `\` as complete units:

1. [10-hdfs-openshift.md](10-hdfs-openshift.md) — pods, containers, Services, PVCs, HDFS commands and local UIs.
2. [11-yarn-openshift.md](11-yarn-openshift.md) — YARN lifecycle, MapReduce word count, Pi and application status.
3. [12-spark-master-openshift.md](12-spark-master-openshift.md) — Spark master, workers, scaling, logs and UIs.
4. [13-spark-submit-openshift.md](13-spark-submit-openshift.md) — submit PySpark word count and write results to HDFS.
5. [14-hive-openshift.md](14-hive-openshift.md) — external Hive table, Beeline, Spark SQL and shared metadata.
6. [15-seaweedfs.md](15-seaweedfs.md) — S3 buckets and objects, uploads, downloads, container shells, admin UI and temporary demo cleanup.
7. [16-polaris.md](16-polaris.md) — create a temporary S3-backed Polaris catalog and Iceberg table, inspect manifests and snapshots, then clean up.

Each step explains its purpose before showing a command. Run the fenced Bash commands in the VM terminal because the in-cluster Jupyter container does not include the `oc` administration client. Browser links use only `127.0.0.1`.

In a new VM Bash terminal, run `okd-env` once before starting a lesson. It loads the cluster credentials and selects `bigdata`. If the cluster is stopped, run `okd-start`. Reload `source ~/.bashrc` only if the helpers are unavailable or you have just changed `.bashrc`.

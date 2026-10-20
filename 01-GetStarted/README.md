# OpenShift getting started

Read these command guides first and run selected blocks in the Linux VM terminal:

1. [01 - CRC commands](../00-Introduction/01-CRC-Commands.md): VM lifecycle, configuration, shell environment, and cluster checks.
2. [02 - OpenShift oc commands](../00-Introduction/02-OC-Commands.md): projects, workloads, logs, networking, storage, and troubleshooting.

The guides include command comments and identify changes and deletion operations. Follow [installation](../00-Introduction/00-Installation.md) and [Bash configuration](../00-bashrc.md) for `.bashrc` and cloned-VM user-session recovery.

## Lesson index

Read these Markdown guides and run their Bash blocks in order:

1. [10-hdfs-openshift.md](10-hdfs-openshift.md) — pods, containers, Services, PVCs, HDFS commands and local UIs.
2. [11-yarn-openshift.md](11-yarn-openshift.md) — YARN lifecycle, MapReduce word count, Pi and application status.
3. [12-spark-master-openshift.md](12-spark-master-openshift.md) — Spark master, workers, scaling, logs and UIs.
4. [13-spark-submit-openshift.md](13-spark-submit-openshift.md) — submit PySpark word count and write results to HDFS.
5. [14-hive-openshift.md](14-hive-openshift.md) — external Hive table, Beeline, Spark SQL and shared metadata.

Copy the fenced Bash blocks into the VM terminal because the in-cluster Jupyter container does not include the `oc` administration client. Browser links use only `127.0.0.1`.

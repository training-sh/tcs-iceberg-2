# OpenShift getting started

Run these notebooks in order:

1. `10-hdfs-openshift.ipynb` — pods, containers, Services, PVCs, HDFS commands and local UIs.
2. `11-yarn-openshift.ipynb` — YARN lifecycle, MapReduce word count, Pi and application status.
3. `12-spark-master-openshift.ipynb` — Spark master, workers, scaling, logs and UIs.
4. `13-spark-submit-openshift.ipynb` — submit PySpark word count and write results to HDFS.
5. `14-hive-openshift.ipynb` — external Hive table, Beeline, Spark SQL and shared metadata.

Shell cells are tagged `vm-terminal`. Copy these command blocks into the VM terminal because the in-cluster Jupyter container does not include the `oc` administration client. Browser links use only `127.0.0.1`.

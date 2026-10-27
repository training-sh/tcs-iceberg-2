# Changes and repairs

Prepared 26 October 2026. No image builds, storage deletion, HDFS formatting or complete deployment replacement were performed.

## Notebook corrections

- Replaced localhost/placeholder cluster endpoints with OpenShift Service names and set the driver callback address to the master pod IP.
- Limited these one-worker lessons to one executor core and 512 MiB executor memory. Validation kernels use 512 MiB driver heap.
- Reused the classroom Polaris client, `training` catalog and SeaweedFS `warehouse` bucket; isolated all example namespaces and paths.
- Corrected `rollback_to_timestamp`: the cutoff must be later than the desired snapshot's commit timestamp. The example uses initial snapshot time plus one millisecond. For exact snapshot selection, prefer snapshot-ID procedures.
- Loaded only Iceberg's SQL extension in the comprehensive versions. The Delta-wrapped parser in the initial adaptation caused `Cannot parse order: parser is not an Iceberg ExtendedParser` during sorted compaction. These notebooks do not exercise Delta.
- Added final logical-row assertions, HDFS registration/safe-mode preflight, and an empty-namespace guard before comprehensive Run All.
- Adapted optional checkpoints and import paths to the selected storage. Streaming/file import are disabled in distributed student defaults; acceptance runs explicitly enable them. Purge/expiration remain disabled.
- Added Hadoop's `fs.s3.impl` mapping to `S3AFileSystem` in the S3 notebook. Normal Iceberg reads/writes use S3FileIO, but orphan-file dry-run uses Hadoop directory listing and otherwise fails on Polaris's `s3://` locations. Existing S3A endpoint/credentials apply to that listing too.

## Applied manifest correction: newer VM only

Host: `100.112.190.74`. Changed only `statefulset/namenode` container `namenode` arguments:

```json
["namenode", "-Ddfs.namenode.datanode.registration.ip-hostname-check=false"]
```

Applied using `../repaired/repair.py --fix hdfs --apply`, staged at `/tmp/course06_hdfs_repair.py` on that VM. Server-side dry-run preceded mutation; original live resource was saved at `/tmp/.state/repair-backups/20261026-233430-564697/hdfs-before.json`. The NameNode rolled successfully. The DataNode then registered, submitted a 456-block report and safe mode cleared. This relaxes reverse-hostname registration validation in the isolated single-DataNode classroom cluster; it is not a general production recommendation. Images, replicas, PVCs and all existing files were preserved. No equivalent manifest change was applied to `100.106.221.9` because its HDFS was already working.

To inspect or undo this one template revision, use `oc -n bigdata rollout history statefulset/namenode`, then inspect the selected revision before `oc -n bigdata rollout undo statefulset/namenode --to-revision=REVISION`. Undo would restore the earlier registration behavior. Do not force safe mode off or delete volumes.

The original NameNode definition was also retained locally at `C:\Course\DataEng\baseline-review-20261026\course06-first\namenode-100.112.190.74-before.json`, independent of the VM's temporary backup. The VM's older `~/openshift/hadoop-hive.yaml` can overwrite the live arguments when reapplied. Keep using the recorded repair until source consolidation is complete; do not reapply old manifests during a lesson.

See VALIDATION.md for notebook acceptance results and remaining limits. Passing registration is not the same as certifying all cluster functionality or restart recovery.

## Hive schema safeguard retained

The HDFS test reproduced a Hive Metastore positional-type validation failure when moving `email` between existing columns. A proposed shared-metastore configuration change was rejected by automatic approval review because it would disable incompatible-schema validation for all tables and restart the service. **That change was not applied.** The HDFS notebook now retains the field at the end and explicitly documents this limitation; it still exercises rename, compatible promotion, nested addition, and final-field drop/re-add. The Polaris notebook tests column reordering too.

References: [Apache Iceberg Hive catalog limitation](https://apache.googlesource.com/iceberg/+/HEAD/docs/docs/spark-ddl.md) and [Apache Hive configuration property](https://hive.apache.org/docs/latest/user/configuration-properties/#hivemetastoredisallowincompatiblecoltypechanges). These explain the server-side positional validation; the two VMs' observed behavior is recorded separately.

# Execution validation

Testing began 26 October 2026 and continued into 27 October (Asia/Calcutta). This report describes the two representative VMs, not all student clones. Notebook generation and syntax checks are separate from the actual Jupyter execution recorded below.

## Current acceptance results

| Notebook | 100.106.221.9 | 100.112.190.74 |
|---|---|---|
| Comprehensive Hive/HDFS | PASS | PASS after NameNode registration repair |
| Comprehensive Polaris/SeaweedFS S3 | PASS | PASS |
| Short side-by-side customer example | PASS | PASS |

All six final notebook/VM combinations completed successfully. Earlier failed attempts are retained in the local evidence directory and are not counted as acceptance. The HDFS schema-reordering limitation below remains explicit; a successful adapted notebook does not claim that unsupported operation works.

## What the comprehensive pass covers

The actual 78-cell notebooks were executed with 36 Python/SQL cells, in fresh Jupyter kernels in the existing `spark-master-0` pod, submitting to the standalone worker. Acceptance builds use fresh namespaces; distributed notebook defaults use `course06_s3`/`course06_hdfs` and leave optional flags off.

Covered: create/insert/update/delete/MERGE, metadata, snapshot/timestamp reads, logical snapshot differences, snapshot/time recovery, tags/branches/fast-forward/cherry-pick, staged WAP, supported schema evolution, partition/spec evolution, sort/distribution settings, WriterV2 overwrites, CTAS/RTAS, MOR/delete files, append scans, changelog updates, compaction, orphan-file **dry-run**, scan planning, and isolation properties. Final assertions verify customer IDs `[1,2,4,5,6,7]`, four events and nineteen MOR rows.

Acceptance runs additionally enable the isolated bounded streaming and Parquet import examples. The saved HDFS outputs show actual streamed rows and imported rows `(1, legacy)` and `(2, archive)`. No snapshot expiration or purge was executed. The two-session concurrency exercise, migration/registration templates, other engines and format-v3 recipes were not executed.

## Intentional differences / limits

- HDFS column reordering is omitted because the shared Hive Metastore positional-type safeguard rejects it. The notebook explains the limitation; rename, supported promotion, nested addition and final-field drop/re-add remain tested. Polaris tests reordering as well. The safeguard was not disabled.
- Existing `training` Polaris catalog and `warehouse` bucket are reused; creating the original notebook's `olist` catalog/bucket and assigning new roles are not part of these acceptance runs.
- HDFS event logging is disabled in that notebook's Spark session, making its data exercise independent of SeaweedFS event storage.
- Full CRC stop/start after the NameNode correction has not been tested. The changed NameNode pod did roll successfully and the DataNode registered afterward.
- HDFS reports existing under-replicated blocks on these one-DataNode labs. No missing/corrupt blocks were observed in the recorded registration checks; these tests do not certify historical dataset integrity.
- No image was rebuilt; no PVC, student table or existing file was deleted. Only the recorded `.74` NameNode command setting changed. All test namespaces and checkpoints are retained.

## Evidence and reproducibility

Local maintainer evidence is under `C:\Course\DataEng\baseline-review-20261026\`:

| Final result | Evidence subdirectory | Namespace |
|---|---|---|
| .9 HDFS | `course06-final/100.106.221.9` | `c06_20261026_181029_hdfs` |
| .74 HDFS | `course06-final/100.112.190.74` | `c06_20261026_181132_hdfs` |
| .9 S3 | `course06-s3-final/100.106.221.9` | `c06_20261026_181552_s3` |
| .74 S3 | `course06-s3-final/100.112.190.74` | `c06_20261027_025050_s3` |

Short-example executed notebooks and summaries are in `course06-short/<VM-IP>/`. Their source code is the same clean 19-cell notebook, with a fresh run ID supplied through the kernel environment.

Large executed outputs are saved separately from the clean source notebooks. Two evidence transfers initially lost SSH after `NOTEBOOK_PASS`/exit 0; their completed 78-cell notebooks were subsequently retrieved through SFTP and had no error outputs. The executed code cells were compared with the current generator; only namespace/optional-flag substitutions and explanatory markdown vary.

The remote acceptance tooling is retained outside the course repository along with the execution evidence. It uses fresh isolated namespaces and records actual outputs; no host credentials are stored in this repository. See CHANGES.md for failed-test corrections and the exact manifest repair.

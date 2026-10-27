# Collected classroom fixes

All concrete infrastructure patches prepared in this session are here: **three Kubernetes strategic-merge patches**, plus the inspection/updater and verifier. Authoring tests and forwarding helper copies are kept outside the course repository. No VM was changed by collecting these files.

| Problem | Patch/helper | Observed state / validation |
|---|---|---|
| DataNode rejected by NameNode hostname validation | `hdfs-registration.patch.yaml` / `repair.py --fix hdfs` | Applied and HDFS notebooks passed on `.74`. `.9` HDFS worked without it. Other student clones not checked. |
| Reducer shuffle cannot reach port 13562 | `yarn-shuffle.patch.yaml` / `repair.py --fix shuffle` | Missing on `.9`; present on `.74`, whose saved word-count job succeeded. We have not applied this patch or rerun YARN word count on `.9`. |
| Trino points to host-local rather than in-cluster Hive Metastore | `trino-hive-endpoint.patch.yaml` / `repair.py --fix trino` | Wrong endpoint reproduced on `.9`; correct live endpoint and successful Hive listing on `.74`. Patch not applied to `.9`. Spark notebook Hive access uses its own direct Service configuration and does not require this Trino patch. |
| Old host UI service binds to obsolete Tailscale IP | Manual port-forward commands below | Foreground alternative, not a systemd repair. Installed old service is unchanged. Reuse existing working forwards. |

The NameNode setting relaxes registration validation for the isolated classroom profile; do not deploy it blindly to production. See [the exact applied change and backup](../CHANGES.md) and [notebook results](../VALIDATION.md).

## 1. Inspect from the Linux VM

Run `okd-env` (or `okd-start` first if stopped), save notebooks, and finish jobs. Change to the course repository root.

```bash
python3 06-Polaris-Iceberg/patches/repair.py --fix hdfs --fix shuffle --fix trino
```

This is plan-only. It reads current resources and skips already-correct settings. An HDFS proposal alone does not prove that the VM has the registration failure; confirm `hdfs dfsadmin -report` and DataNode logs first. Do not assume all 40+ clones need every change.

## 2. Apply only the needed correction

Example for a confirmed HDFS registration failure:

```bash
python3 06-Polaris-Iceberg/patches/repair.py --fix hdfs --apply
```

For confirmed older-group shuffle/Trino problems:

```bash
python3 06-Polaris-Iceberg/patches/repair.py --fix shuffle --fix trino --apply
```

The updater validates all requested patches with API dry-run first, preserves unrelated settings, saves originals in `patches/.state/repair-backups`, waits for changed StatefulSets to roll, and stops on failure. It does not rebuild images or delete/resize PVCs. A repeat run skips corrected settings. NameNode/Trino changes interrupt those services; shuffle-port changes need no restart. This preparation/patch logic has six offline tests; the complete multi-fix flow is not certified on every clone.

## 3. Verify prerequisites and actual exercises

```bash
python3 06-Polaris-Iceberg/patches/verify.py
```

Then run the relevant notebook and YARN word count using fresh output paths. Rollout/readiness and metadata listings alone are insufficient. See the main folder's README for HDFS directory preparation and notebook execution. Full CRC restart recovery after repair remains untested.

## 4. UI alternative

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18888:8888
```

Keep the terminal open; use `http://127.0.0.1:18888/lab` in the VM browser. An existing forward may already occupy a port; reuse it rather than killing unrelated processes. This does not change, stop or replace the old systemd service. No sudo is required. See [MovieLens access instructions](../MovieLens.md) for SeaweedFS port mappings.

## Raw YAML use for administrators

These are sparse patches: **do not run `oc apply -f patches/`**. Prefer the updater for no-op detection, backup and argument preservation. The corresponding raw commands are:

```bash
oc -n bigdata patch statefulset/namenode --type=strategic --patch-file 06-Polaris-Iceberg/patches/hdfs-registration.patch.yaml
oc -n bigdata patch service/nodemanager --type=strategic --patch-file 06-Polaris-Iceberg/patches/yarn-shuffle.patch.yaml
oc -n bigdata patch statefulset/trino --type=strategic --patch-file 06-Polaris-Iceberg/patches/trino-hive-endpoint.patch.yaml
```

These raw commands have no backup step. The HDFS YAML replaces the complete `args` list and is specific to the inspected entrypoint; the updater preserves extra existing arguments. Do not paste all three commands unless all corrections are intended.

## Other discrepancies, not additional infrastructure patches

- Notebook timestamp rollback, parser-extension order and Hadoop S3 mapping are corrected in the notebook builders; no cluster patch is needed. HDFS column reordering remains explicitly omitted because the shared Hive safeguard stays enabled.
- The rejected proposal to disable Hive's incompatible-schema safeguard was **not applied and is not included**.
- Spark importer tag mismatch, missing notebook source paths in the old deploy script, HiveServer2 defaults, multiple manifest families, image drift and a permanent systemd replacement remain installation/source consolidation work. Do not mistake this collection for a full fresh-install deployment or claim those issues have been patched.
- The original `repaired/` directory is retained. This folder is a self-contained snapshot for this lesson; avoid editing the two copies independently. Before distributing future updates, regenerate the copied helpers from the authoritative implementation or choose one location as canonical.

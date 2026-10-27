# Iceberg on OpenShift: Polaris/S3 and Hive/HDFS

This folder adapts both supplied notebooks to the existing classroom OpenShift images. Run from a cloned course repository on the Linux VM, then use Jupyter **inside `spark-master-0`**, not a Windows/local Python kernel.

Start with the [Polaris introduction](01_polaris_introduction.md); its diagrams are in `assets/`.

| Notebook | Catalog and storage |
|---|---|
| `06-Polaris-Iceberg.ipynb` | Short side-by-side customer example: Polaris/S3 and Hive/HDFS |
| `Iceberg-Comprehensive-S3-Polaris.ipynb` | Comprehensive Iceberg exercises using Polaris REST and SeaweedFS S3 |
| `Iceberg-Comprehensive-HDFS-Hive.ipynb` | Same comprehensive exercises using Hive Metastore and HDFS |
| [MovieLens-OpenShift.ipynb](MovieLens-OpenShift.ipynb) | Bronze CSV to silver/gold Iceberg; follow the [MovieLens guide](MovieLens.md) |

Read `VALIDATION.md` for actual per-VM results, tested optional features, and any narrow manifest correction. A notebook being generated or a pod being Ready does not establish that its exercises pass.

All prepared infrastructure corrections and their updater are collected in [patches/README.md](patches/README.md). Inspect the current VM first; the patches are not full manifests for a recursive `oc apply`.

## 1. Load the cluster and inspect services (VM Bash terminal)

```bash
source ~/.bashrc
okd-env
```

If CRC is stopped, run `okd-start`, wait for completion, and rerun `okd-env`. Then inspect the existing workloads:

```bash
oc -n bigdata get pods -l 'app in (namenode,datanode,hive-metastore,seaweedfs,polaris,postgres,mysql,spark-master,spark-worker)' -o wide
```

The Spark master must be `3/3`, worker `1/1`, and required data services Ready. YARN and HiveServer2 are **not required**. Do not apply all YAML files or rebuild images to launch these notebooks.

```bash
oc -n bigdata rollout status statefulset/spark-master --timeout=300s
oc -n bigdata rollout status statefulset/spark-worker --timeout=300s
```

## 2. Verify HDFS registration before HDFS notebooks

```bash
oc -n bigdata exec namenode-0 -- hdfs dfsadmin -report
```

Expect **one live DataNode**, nonzero capacity, and no `Safe mode is ON`. If not, the HDFS cells must stop; the S3-only notebook can still run. Do not force safe mode off, format HDFS or delete storage. See the separately recorded repair in `VALIDATION.md` and [patch instructions](patches/README.md) if applicable.

Prepare a dedicated new parent for the `spark` user. This changes only this example's directory, not `/training`, the Hive warehouse or existing student directories:

```bash
oc -n bigdata exec namenode-0 -- hdfs dfs -mkdir -p /training/06-polaris-iceberg
oc -n bigdata exec namenode-0 -- hdfs dfs -chown spark /training/06-polaris-iceberg
```

## 3. Copy the notebooks into persistent Jupyter storage

Run from the course repository root:

```bash
oc -n bigdata cp ./06-Polaris-Iceberg spark-master-0:/workspace/ -c jupyter
```

The notebook files persist on `spark-notebooks`. Copying source does not reset any database/table, and kernel restarts do not reset tables either.

## 4. Open Jupyter from the VM browser

In a separate VM terminal, run `okd-env`, then keep this command running:

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18888:8888
```

Open `http://127.0.0.1:18888/lab` **inside the VM**, and use the existing classroom Jupyter token (`team1234` unless changed). If port 18888 is already forwarded by the host service, reuse it. No Tailscale address belongs in the notebook. Laptop access requires a tunnel to the VM; localhost in a laptop browser is the laptop itself.

## 5. Execute one notebook at a time

The lab has one worker core. Start a fresh Python kernel, run cells in order, and stop Spark or shut down that kernel before starting the next notebook. Do not run multiple Spark sessions concurrently on this small lab.

- The short notebook creates a unique namespace per session; table cells MERGE the same three rows on rerun.
- Comprehensive variants use isolated fixed namespaces `iceberg.course06_s3` and `iceberg.course06_hdfs`. A full run expects an empty namespace and stops if tables already exist. For another full run, regenerate with another namespace (below), rather than deleting earlier results. Individual append/branch/schema cells are not generally safe to repeat.
- Streaming and file import are disabled by default. Their optional flags can be enabled after the core exercises succeed. Expiration and purge remain commented; orphan review is dry-run only. All writes/maintenance in the notebook target its isolated tables.
- The alias `iceberg` means Polaris in the S3 notebook and Hive in the HDFS notebook. It is a Spark alias, not a separate server.
- The HDFS variant disables Spark event logging for its session so it does not depend on S3 for History Server event files.

## 6. Expected core results

The short notebook reads Alice/Bob/Carol back from both tables and shows physical file paths. S3 paths start with `s3://`/`s3a://`; HDFS paths start with `hdfs://`.

The comprehensive notebooks cover CRUD/MERGE, metadata, time travel, rollback, tags/branches/WAP, schema/partition evolution, WriterV2/CTAS/RTAS, MOR, append scans/changelog, compaction and dry-run maintenance. Final assertions check customer IDs `[1, 2, 4, 5, 6, 7]`, four events and nineteen MOR rows. Concurrency/migration recipes require separate environments and are not demonstrated merely by Run All.

## Differences from the supplied notebooks

| Original assumption | OpenShift replacement |
|---|---|
| `spark://localhost:7077` / `your-spark-host` | `spark://spark-master:7077` |
| `thrift://localhost:9083` | `thrift://hive-metastore:9083` |
| `hdfs://localhost:9000` | `hdfs://namenode:9000` |
| S3 localhost port 9001 | In-cluster `http://seaweedfs:8333` |
| Polaris root credentials | Existing client credentials from container environment |
| New `olist` bucket/catalog | Reuse existing `warehouse` bucket and Polaris `training` catalog; isolated namespaces |
| Shared `iceberg.demo` tables | Dedicated namespace for each storage version/test run |
| Both original `hive_catalog`/`iceberg` aliases described as different catalogs | Both were Iceberg SparkCatalog configurations backed by the same metastore; only one is needed here |

The existing image already supplies the runtime JARs. There are no `pip install`, Maven package resolution or image builds in these lessons. Runtime/Scala/JAR versions must still match when changing images later.

## Repeat an exercise

For another comprehensive run, save a notebook copy and consistently replace its namespace (`course06_s3` or `course06_hdfs`) with a fresh name, including its associated storage paths. Start a fresh kernel before running the copy. Keep the earlier tables rather than deleting them to reset an exercise.

The short notebook and MovieLens notebook generate a fresh run identifier per kernel session. Authoring builders, source templates and remote validation tools are kept outside this course directory; the notebooks run without them.

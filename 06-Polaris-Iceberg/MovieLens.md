# MovieLens on OpenShift

Open [MovieLens-OpenShift.ipynb](MovieLens-OpenShift.ipynb) in the existing Jupyter container. The notebook is stored with the Polaris/Iceberg examples.

See [MovieLens-VALIDATION.md](MovieLens-VALIDATION.md) for execution results and browser checks. This lesson needs Spark, Polaris, PostgreSQL and SeaweedFS; **HDFS, YARN, HiveServer2 and Trino are not required**.

## 1. Check the existing workloads (Linux VM terminal)

```bash
source ~/.bashrc
okd-env
oc -n bigdata get pods -l 'app in (spark-master,spark-worker,polaris,postgres,seaweedfs)' -o wide
```

If CRC is stopped, run `okd-start`, wait for completion, and rerun `okd-env`. Expect `spark-master-0` at `3/3`, the worker at `1/1`, and the data services Ready. Do not rebuild images or apply the complete old manifest directories for this lesson.

## 2. Open SeaweedFS web pages

In another VM terminal after `okd-env`, run:

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/seaweedfs 19002:23646 19333:9333 18889:8888 19001:8333
```

Keep it open. This command does not modify Kubernetes or systemd. Reuse working existing forwards rather than starting duplicate listeners; omit occupied mappings when only some ports need forwarding.

| Interface | Open inside that VM's browser |
|---|---|
| Admin login | `http://127.0.0.1:19002/` |
| Filer / bucket browser | `http://127.0.0.1:18889/buckets/warehouse/` |
| Master UI | `http://127.0.0.1:19333/` |
| S3 API (not a web dashboard) | `http://127.0.0.1:19001/` |

Admin credentials are `team` / `team1234` unless changed. The volume service root is **not** a dashboard; use the filer or admin UI to inspect data.

These addresses bind to loopback: open them on the Linux desktop or use an SSH tunnel. Replace `SERVER_ADDRESS` with the system's reachable address:

```bash
ssh -N -L 19002:127.0.0.1:19002 -L 18889:127.0.0.1:18889 dev@SERVER_ADDRESS
```

When opening more than one installation simultaneously, choose different local ports for each tunnel, for example `29002:127.0.0.1:19002` and `28889:127.0.0.1:18889`. Keep the forwarding helper and SSH tunnel running. The interface URLs are listed above.

## 3. Copy and open the notebook

From the course repository root in the VM:

```bash
oc -n bigdata cp ./06-Polaris-Iceberg spark-master-0:/workspace/ -c jupyter
```

Open Jupyter using its existing forward, or in another VM terminal run:

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/spark-master 18888:8888
```

Open `http://127.0.0.1:18888/lab` in the VM browser and use the lab token (`team1234` unless changed). If a working forward already occupies 18888, reuse it. Open `06-Polaris-Iceberg/MovieLens-OpenShift.ipynb`, start a fresh Python kernel, and run cells in order. Run only one Spark notebook at a time on the single-worker lab.

## 4. Bronze input modes

Default `DATA_MODE='download'` prepares the real [GroupLens MovieLens small dataset](https://grouplens.org/datasets/movielens/) in the existing `warehouse` bucket. Read its [usage terms](https://files.grouplens.org/datasets/movielens/ml-latest-small-README.html); the original dataset README is retained beside bronze. Dataset files are not bundled in Git.

- Official archive: `https://files.grouplens.org/datasets/movielens/ml-latest-small.zip`.
- Tested SHA-256: `696d65a3dfceac7c45750ad32df2c259311949efec81f0f144fdfb91ebc9e436`.
- Bronze: `s3a://warehouse/movielens/bronze/ml-latest-small/`.
- Input: 9,742 movies and 100,836 ratings. The archive is about 1 MB; no Maven or Python packages are downloaded.

Existing identical bronze is reused after a byte-level check. Different existing bronze causes a clear error; it is never silently overwritten. If GroupLens replaces this development archive, inspect the new release before updating the checksum and expected counts.

For your own already-uploaded CSVs, change `DATA_MODE` to `'existing'` and `BRONZE` to the prefix containing `movies/movies.csv` and `ratings/ratings.csv`. The small-dataset count/oracle assertions apply only to download mode. Existing mode still verifies nonempty CSVs, table write/read counts and gold predicates.

If the Jupyter container cannot download HTTPS, do not disable certificate checks. Download on the VM with its trusted Python installation, then stage the archive into the notebook container:

```bash
python3 -c "import urllib.request; urllib.request.urlretrieve('https://files.grouplens.org/datasets/movielens/ml-latest-small.zip','/tmp/ml-latest-small.zip')"
oc -n bigdata cp /tmp/ml-latest-small.zip spark-master-0:/workspace/ml-latest-small.zip -c jupyter
```

Before the data preparation cell, set `os.environ['MOVIELENS_ARCHIVE']='/workspace/ml-latest-small.zip'`. The same SHA-256 check still applies. Default HTTPS downloads succeeded from the notebook containers during acceptance.

## 5. Silver, gold and validation

Each kernel creates isolated namespaces such as `polaris.movielens_..._silver` and `polaris.movielens_..._gold` inside Polaris's existing **`training` catalog**. `polaris` is the Spark alias; `training` is a catalog name, not an S3 path. Iceberg's physical table locations are selected by that catalog, separately from the bronze prefix.

Silver uses explicit schemas and deterministic duplicate rules. Movie IDs choose lexical title/genres; conflicting copies of a rating event choose the highest rating for the same user/movie/timestamp key. Adapt that explicit teaching policy for another ingestion requirement.

Gold retains movies with at least 100 ratings and an unrounded average of at least 4.0. The notebook compares Spark's result with a separate Python calculation from the source CSVs, then checks actual Iceberg snapshots and S3 data-file paths. `createOrReplace()` affects only the current run's isolated silver/gold tables. Bronze remains unchanged. Tables and snapshots are retained; the final cell stops Spark.

## Changes from Docker/Compose

- `localhost`/container-host Spark endpoints -> OpenShift Service names plus the driver pod IP.
- `root:s3cr3t` and absent `test_catalog` -> existing container-provided client credentials and Polaris `training`.
- Missing `datalake` CSVs -> checksummed real input preparation, or configurable existing data.
- Maven Iceberg 1.9.2 resolution -> already-installed Iceberg 1.10.0 runtime in Spark 3.5.9; no duplicate JAR downloads.
- Java 17 assumption -> use the existing tested image's Java runtime (Java 11).
- Shared `silver`/`gold` tables -> unique run namespaces, preserving existing work.
- Nondeterministic `dropDuplicates` -> explicit duplicate policy and gold result assertions.

Port-forwarding does not change images, manifests, Secrets, PVCs or system services. Restart the command after reboot or a forwarding failure.

Authoring and validation tools are kept outside this course directory. Run the notebook directly in Jupyter.

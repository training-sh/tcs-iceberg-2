# MovieLens classroom: Spark, SeaweedFS, Iceberg and MySQL

Follow the numbered steps in order. Use the supplied files unchanged. You do not need to write code, create notebooks, or solve configuration problems.

The exercise is a self-contained download. Extract or clone it into any directory and follow the numbered commands.

```text
MovieLens CSV files
    -> SeaweedFS S3 Bronze
    -> Spark -> Silver Iceberg tables in Polaris
    -> Spark -> Gold Iceberg analytics
    -> Spark JDBC -> MySQL reporting tables
```

Each of the four Python stage files is independent. It starts its own Spark session, reads persisted input, writes its output and stops. The runner submits the stage to the existing Spark master; it contains no transformation logic.

## Before you begin

Use a terminal with Python 3, Git, Bash, `flock` and an authenticated `oc` command. The prepared namespace `bigdata` provides Spark, SeaweedFS, Polaris catalog `training`, MySQL and Trino. Optional Airflow steps require healthy Airflow 3. The supplied preflight checks these prerequisites without changing them.

Run one pipeline at a time. Do not run the command-line and Airflow pipelines concurrently.

## Step 1: Download and open the exercise


Download this file, on step 1, you need to map the files based on extracted directory .

https://github.com/training-sh/tcs-iceberg-2/blob/main/data/ml-latest-small%20(3).zip


Download `movielens-classroom.zip` from the exercise repository and save it in `~/Downloads`. Extract and open it:

```bash
mkdir -p "$HOME/training"
python3 -m zipfile -e "$HOME/Downloads/movielens-classroom.zip" "$HOME/training"
cd "$HOME/training/movielens-classroom"
export PATH="$HOME/.crc/bin/oc:$PATH"
ls
```

Expected files include `README.md`, `download-data.py`, `spark-job-template.json`, four numbered Python files and the supplied shell scripts. If you already cloned the repository, open that exercise directory instead. No specific parent directory is required.

Keep this terminal open and run the following commands in order.

## Step 2: Check the supplied lab

```bash
python3 preflight.py
```

Expected final lines:

```text
SPARK_CAPACITY_PASS
PREFLIGHT_PASS
```

This checks service readiness, the existing credential references, the expected Spark image, permissions, the PVC and free worker capacity. It changes nothing. If it fails, stop and report the output. Do not reinstall packages or change the cluster.

## Step 3: Download MovieLens small

```bash
python3 download-data.py
ls -lh "$HOME/data/movielens-small"
```

The supplied script downloads the MovieLens small archive from GroupLens, verifies its checksum and places these files in **`~/data/movielens-small`**:

```text
movies.csv
ratings.csv
tags.csv
links.csv
README.txt
```

Expected final marker: `DATASET_READY`. A matching dataset already in this directory is verified and reused. No other Downloads directory or previous exercise is required. The dataset contains **9,742 movies and 100,836 ratings**. Keep its original `README.txt` with the files; its usage and attribution terms apply.

## Step 4: Prepare the lesson's MySQL database

```bash
bash prepare-mysql.sh
```

Expected output:

```text
Prepared movielens_classroom_s01 and scoped permissions for the existing team user.
```

This runs the supplied `00_prepare_mysql.sql`: it creates `movielens_classroom_s01` and grants the existing `team` account the permissions required only for this lesson's database. The script uses the root credential already inside the existing MySQL pod, without printing it. Subsequent Spark Jobs use the application credential from the existing Secret, not root. This setup can be repeated.

## Step 5: Copy the supplied files into the cluster

```bash
bash publish.sh
```

Expected final line:

```text
Published source and scripts. No Spark jobs have been started.
```

The script copies the four numbered programs from the exercise directory and the five files from `~/data/movielens-small` to `/workspace/movielens-classroom` on the shared Kubernetes volume. The short-lived Spark drivers read these copied files; Airflow coordinates their execution. Do not run `publish.sh` while a lesson Job is active.

## Step 6: Upload Bronze to SeaweedFS S3

```bash
python3 run-stage.py 01
```

Expected markers: `BUCKET_CREATED` or `BUCKET_REUSED`, five `BRONZE_FILE_PASS` lines, `UPLOAD_PASS`, and `STAGE_PASS 01`.

The independently runnable file is `01_upload_bronze.py`. It creates `movielens-classroom-raw` if absent, checks/reuses the existing `warehouse` bucket, and uploads the original files plus a SHA-256 manifest:

```text
s3://movielens-classroom-raw/ml-latest-small/movies.csv
s3://movielens-classroom-raw/ml-latest-small/ratings.csv
s3://movielens-classroom-raw/ml-latest-small/tags.csv
s3://movielens-classroom-raw/ml-latest-small/links.csv
s3://movielens-classroom-raw/ml-latest-small/README.txt
s3://movielens-classroom-raw/ml-latest-small/manifest.json
```

Existing raw files must match their source hashes and are reused. Different contents cause failure instead of being overwritten. Bronze contains the original CSVs; it is not an Iceberg table. The installed Java S3 client is used, so no Python S3 package is needed.

## Step 7: Convert Bronze to Silver Iceberg

```bash
python3 run-stage.py 02
```

Expected markers:

```text
SILVER_TABLE_PASS polaris.movielens_classroom_s01_silver.movies 9742
SILVER_TABLE_PASS polaris.movielens_classroom_s01_silver.ratings 100836
SILVER_PASS
STAGE_PASS 02 ...
```

Read the supplied `02_bronze_to_silver.py`. It reads explicit CSV schemas, checks required values and rating/movie references, deterministically handles duplicate keys, trims titles, extracts a release year when present and adds UTC rating timestamp/date columns. Invalid input fails the stage rather than silently disappearing.

It creates namespace `movielens_classroom_s01_silver` in the existing Polaris `training` catalog and writes Iceberg movies and ratings tables under:

```text
s3://warehouse/iceberg/movielens_classroom_s01_silver/
```

A bucket stores objects. Polaris is the catalog service that resolves Iceberg metadata. A namespace groups tables within the catalog. This step creates a namespace, not another catalog or catalog server.

## Step 8: Build Gold analytics

```bash
python3 run-stage.py 03
```

Expected output includes:

```text
GOLD_TABLE_PASS polaris.movielens_classroom_s01_gold.movie_stats 9742
GOLD_TABLE_PASS polaris.movielens_classroom_s01_gold.genre_stats 20
GOLD_TABLE_PASS polaris.movielens_classroom_s01_gold.daily_ratings 4110
GOLD_PASS ratings=100836
STAGE_PASS 03 ...
```

`03_silver_to_gold.py` reads the persisted Silver tables. It creates namespace `movielens_classroom_s01_gold` and these Iceberg reports:

| Report | Contents |
|---|---|
| `movie_stats` | Every movie, including unrated movies; rating count, average, distinct users, release year and genres |
| `genre_stats` | Rating count, rated movie count and average per genre |
| `daily_ratings` | UTC date, rating count, active users and average |

Movie and daily rating counts must each total 100,836. Movies can have multiple genres, so their ratings contribute once to each genre; adding genre totals does not produce the total number of source ratings.

## Step 9: Publish Gold to MySQL

```bash
python3 run-stage.py 04
```

Expected: three `MYSQL_STAGING_PASS` lines, three `MYSQL_TABLE_PASS` lines, `MYSQL_PASS`, then `STAGE_PASS 04`.

`04_gold_to_mysql.py` reads the persisted Gold tables, writes separate MySQL staging tables using one JDBC writer partition and reads them back to compare counts and values. It then publishes all three tables with one `RENAME TABLE` statement. Existing reports remain available until the new staging tables pass validation. The results are:

```text
movielens_classroom_s01.movie_stats      9742 rows
movielens_classroom_s01.genre_stats        20 rows
movielens_classroom_s01.daily_ratings    4110 rows
```

## Step 10: Verify the complete flow

```bash
python3 verify.py
```

Expected:

```text
REFERENCE_PASS iceberg_polaris.movielens_classroom_s01_gold ...
REFERENCE_PASS mysql.movielens_classroom_s01 ...
END_TO_END_REFERENCE_PASS
```

This independent checker computes reference results from the original CSVs using Python's standard library. Through Trino it checks Silver counts, every movie's rating count/average/distinct users, every daily count and every genre count in both Iceberg and MySQL. Movie averages allow Gold's rounding to six decimal places. It uses the existing Jupyter container to reach service DNS; the command-line pipeline and verification do not depend on Airflow.

For SQL inspection, `verify-trino.sql` contains the exact queries for the existing Trino UI/CLI. Spark names the catalog `polaris`; Trino names the same catalog `iceberg_polaris`.

To inspect MySQL directly:

```bash
oc exec -it -n bigdata mysql-0 -- mysql -u team -p movielens_classroom_s01
```

Enter the lab password at the prompt. Paste the supplied queries from `verify-mysql.sql`. Do not put the password in the command.

## Step 11: Run the same stages automatically

After completing the individual stages, rerun them serially with:

```bash
bash run-all.sh
python3 verify.py
```

`run-all.sh` stops at the first failure. It takes a command-line lock to prevent overlapping copies of itself. A single `run-stage.py` command remains available when teaching one stage at a time. The lock does not coordinate with other users' manual submissions or Airflow.

## Step 12: Optional Airflow automation

Complete steps 1-10 first. Ensure the command-line pipeline has finished.

```bash
python3 preflight.py --airflow
bash publish-airflow.sh
python3 run-airflow.py
python3 verify.py
```

The optional preflight allows up to one minute for fresh component heartbeats. It stops if Airflow remains unhealthy; it does not restart or reconfigure services.

Expected: the script waits for discovery, triggers `classroom_movielens_s01`, prints a successful run with four successful tasks, and pauses the DAG again. New files can take up to five minutes to be discovered. The Airflow UI shows:

```text
upload_bronze -> bronze_to_silver -> silver_to_gold -> gold_to_mysql
```

The supplied `airflow_movielens.py` launches the same four independent files as serial Spark driver Jobs. The supplied JSON manifest is copied alongside the DAG. Each execution path uses the manifest supplied with this exercise.

The DAG is manual, initially paused, has no catchup or retries, one active run and one active task. XCom contains only stage/Job identifiers. Airflow logs show orchestration; Spark computation logs belong to the corresponding Job.

## Submission and logging details

`run-stage.py` loads the supplied `spark-job-template.json`, substitutes the selected file and creates a bounded driver Job. Its `spark-submit` targets `spark://spark-master:7077`. Each stage uses one worker core, a 512 MiB executor, a 512 MiB driver heap and two shuffle partitions. Driver limit: 1 CPU / 1536 MiB. Jobs have a 15-minute deadline, zero retries and a one-hour completed-Job TTL. No service is scaled.

The manifest contains Secret references, never credential values. It references only the existing notebook PVC and has no dependency on a previous lesson's ConfigMap. No Python helper file is imported by the stage scripts.

```bash
oc get jobs -n bigdata -l app=movielens-classroom
```

Command-line runs print their Job name and save full logs under this clone's `logs/` directory. To inspect a Job, use its printed name:

```bash
oc logs -n bigdata job/PRINTED_JOB_NAME
```

The literal `PRINTED_JOB_NAME` is replaced by the name displayed by the runner. Job expiry does not remove the saved logs or persisted data.

## Reruns and classroom checkpoints

Reruns reuse matching raw files, replace snapshots in this lesson's Iceberg namespaces, and replace only this lesson's MySQL reports. Iceberg commits are atomic per table, not across the whole pipeline. Run serially; if a stage fails, stop and report the printed log location. After the prerequisite is corrected, repeat the failed stage before continuing. A failed MySQL attempt may leave uniquely named staging tables for inspection.

Do not delete the raw bucket, metadata files or course database to repeat a demonstration. Do not compare Iceberg snapshot IDs across runs; the reference checker verifies logical results.

The future Hive/HDFS exercise will have its own files and walkthrough. This exercise does not enable or modify Hive/HDFS.

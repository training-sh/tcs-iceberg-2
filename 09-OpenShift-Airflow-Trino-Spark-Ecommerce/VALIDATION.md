# Validate and publish the Airflow ecommerce lessons

Open a terminal in this exercise directory. Keep the course DAGs and their Spark Jobs idle during publication.

## Check supplied files

```bash
python3 -B -m unittest discover -s tests -v
bash -n publish-course.sh
```

The tests check the bounded Trino client, Job construction and failure handling, manual DAG graphs, matching introduction heredocs, documentation links and diagrams, and simulated publication. They make no cluster calls. Publication is simulated with an `oc` recorder and exercised twice to check source ordering and repeatability.

## Publish to Kubernetes

```bash
export PATH="$HOME/.crc/bin/oc:$PATH"
bash publish-course.sh
```

This copies six helper modules, the SQL query, the Spark script and two DAG entrypoints into the existing pods. Supporting files are copied before DAG entrypoints. It does not trigger runs, create Spark Jobs, restart services or change cluster configuration. Missing source files cause it to stop before any cluster call.

The source directory can be anywhere. The script resolves its own directory, so it does not depend on a particular parent directory or the `EXERCISE_DIR` variable.

## Check actual discovery

```bash
oc exec -n bigdata airflow-0 -c airflow -- airflow dags list-import-errors
oc exec -n bigdata airflow-0 -c airflow -- airflow dags list
```

New files can take up to five minutes to appear. Expect these four DAGs with no course import errors:

```text
course_00_hello_trino
course_s01_01_trino_checks
course_s01_02_spark_report
course_s01_03_end_to_end
```

The suffix comes from `dags/course_airflow_ecomm/settings.py`. Existing pause state is preserved on republication; newly created DAGs start paused.

## Run the read-only introduction

In Airflow, unpause `course_00_hello_trino` and trigger it once. Expect successful `begin`, `query_trino` and `finish` tasks, with `HELLO_TRINO_QUERY_PASS: nations=25` in the query task log. Pause it after the demonstration.

This verifies real parsing, scheduling, task execution and Trino connectivity without modifying business tables or submitting Spark Jobs.

## Run the advanced lessons separately

Lessons 01–03 require the preceding ecommerce dataset: eight accepted lines, five orders, four report groups and 225.00 total revenue. Follow their documented checks and execute one DAG at a time. Publication and introduction success do not certify that dataset or the advanced Spark pipeline. See `PREREQUISITE-CHECK.md` before continuing.

## Verified results

The restored eleven-test suite passed on Linux with no skips. Publication copied all ten files, and their deployed contents matched the supplied sources by checksum. All four course DAGs were discovered without course import errors. The introduction completed successfully with three successful tasks and the expected 25-nation result, then was paused again.

Publication was also checked from an independent exercise directory, including a path containing spaces. The tests verify required in-exercise files without requiring sibling course directories. Advanced business-data prerequisites remain separate from these restoration checks.

The supplied `prepare-ecommerce-data.py` command was subsequently checked against an initial Iceberg seed with a missing MySQL source. It prepared matching source data and refreshed Silver/Gold to eight completed lines, five orders, four report groups and 225.00 revenue. A serial replay verifies stable counts without duplicate source rows.

After preparation, the real `course_s01_02_spark_report` run succeeded: `prepare`, `run_spark_report` and `verify_with_trino` all passed, and the driver Job completed. This verifies lesson 02 in addition to the introduction. Lesson 03 still has its own explicit execution steps.

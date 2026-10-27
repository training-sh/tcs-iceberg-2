# S3 Data Lake with SeaweedFS

SeaweedFS provides S3-compatible object storage for raw files and Iceberg table data. Use the admin console to inspect services, the filer to browse buckets and files, and the S3 API for application access.

The same instructions apply on each OpenShift installation. Commands run in a Linux Bash terminal.

## 1. Connect to OpenShift

```bash
source ~/.bashrc
okd-env
```

If the cluster is stopped, start it and wait for completion:

```bash
okd-start
```

Check the SeaweedFS pod and Service:

```bash
oc -n bigdata get pods -l app=seaweedfs
oc -n bigdata get service seaweedfs
```

The pod should show `1/1` under `READY` and `Running` under `STATUS`.

```bash
oc -n bigdata rollout status statefulset/seaweedfs --timeout=300s
```

## 2. Open the web interfaces

From the course repository root, run:

```bash
bash 05-S3-DataLake/forward-seaweedfs.sh
```

Keep the terminal open. The helper starts forwards for unused ports and leaves existing listeners unchanged. If a port is already listening, verify its page before reusing it.

Open these addresses in a browser on the same Linux desktop:

| Interface | Address | Purpose |
|---|---|---|
| Admin console | [http://127.0.0.1:19002/](http://127.0.0.1:19002/) | Sign in and inspect SeaweedFS services |
| Bucket browser | [http://127.0.0.1:18889/buckets/](http://127.0.0.1:18889/buckets/) | Browse buckets and object paths |
| Warehouse bucket | [http://127.0.0.1:18889/buckets/warehouse/](http://127.0.0.1:18889/buckets/warehouse/) | Inspect data stored in `warehouse` |
| Master console | [http://127.0.0.1:19333/](http://127.0.0.1:19333/) | Inspect volume-server registration and capacity |
| S3 API | `http://127.0.0.1:19001` | Endpoint for AWS CLI and other S3 clients |

The S3 API is not a web dashboard. Use the admin console or bucket browser for web access.

### Admin sign-in

| Field | Value |
|---|---|
| Username | `team` |
| Password | `team1234` |

Use the configured credentials if these values have been changed. After signing in, the admin page opens at `/admin`.

## 3. Browse files

Open the warehouse bucket, then navigate through its folders. A folder path in the filer corresponds to an object prefix in S3:

| S3 location | Filer location |
|---|---|
| `s3://warehouse/` | `/buckets/warehouse/` |
| `s3://warehouse/movielens/` | `/buckets/warehouse/movielens/` |
| `s3://warehouse/iceberg/` | `/buckets/warehouse/iceberg/` |

Folders appear after data is written. The MovieLens exercise prepares its bronze files under `warehouse/movielens/bronze/ml-latest-small/`. An object can be opened through the filer using its complete path, for example:

```text
http://127.0.0.1:18889/buckets/warehouse/movielens/bronze/ml-latest-small/movies/movies.csv
```

Use the browser to inspect or download files. Avoid editing or deleting Iceberg `metadata`, manifest, data or delete files directly: the catalog and snapshots reference those files. Manage Iceberg tables through Spark SQL or another compatible engine.

## 4. Access the S3 API from the terminal

With AWS CLI available, configure the terminal:

```bash
export AWS_ACCESS_KEY_ID=team
export AWS_SECRET_ACCESS_KEY=team1234
export AWS_DEFAULT_REGION=us-east-1
export AWS_PAGER=""
```

List buckets:

```bash
aws --endpoint-url http://127.0.0.1:19001 s3 ls
```

List object prefixes in the warehouse:

```bash
aws --endpoint-url http://127.0.0.1:19001 s3 ls s3://warehouse/
```

List MovieLens bronze files after that exercise has prepared them:

```bash
aws --endpoint-url http://127.0.0.1:19001 s3 ls s3://warehouse/movielens/bronze/ml-latest-small/ --recursive
```

These commands list existing data without changing it. If `aws` is unavailable, the bucket browser remains available independently.

## 5. Use the correct endpoint for applications

| Client location | S3 endpoint |
|---|---|
| Terminal on the Linux desktop with the forward running | `http://127.0.0.1:19001` |
| Spark/Jupyter container in namespace `bigdata` | `http://seaweedfs:8333` |
| Container in another namespace | `http://seaweedfs.bigdata.svc.cluster.local:8333` |

Spark uses `s3a://warehouse/...` for Hadoop S3A reads. Iceberg S3FileIO can use `s3://warehouse/...`. Enable path-style S3 access and use the configured access key and secret. `localhost` inside a container refers to that container, so it must not replace the SeaweedFS Service name.

Polaris catalogs Iceberg tables; SeaweedFS stores their files. The Polaris catalog name and S3 bucket name are separate settings.

## 6. Open the interfaces from another computer

The forwards bind to `127.0.0.1`. A remote browser therefore needs an SSH tunnel to the Linux system where the forwards are running.

Replace `SERVER_ADDRESS` with its reachable address:

```bash
ssh -N -L 19002:127.0.0.1:19002 -L 18889:127.0.0.1:18889 -L 19333:127.0.0.1:19333 -L 19001:127.0.0.1:19001 dev@SERVER_ADDRESS
```

Keep the tunnel running, then use the same browser URLs on the remote computer. If a local port is occupied, choose a different port on the left side of its mapping. For example, `29002:127.0.0.1:19002` makes the admin console available at `http://127.0.0.1:29002/` on that computer.

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| Browser cannot connect | Keep the forward running; open the URL on the correct computer or establish the SSH tunnel |
| Port already in use | Verify and reuse an existing forward, or choose another local port; do not stop unrelated processes |
| `localhost` fails inside Spark | Use the Service endpoint `http://seaweedfs:8333` |
| Admin login rejected | Use the configured admin credentials and allow the sign-in form to create its session cookie |
| Bucket or object returns 404 | Confirm its name and whether the corresponding exercise has written data |
| S3 root returns XML or an authentication error | This is an API endpoint; use the filer/admin URL for the web interface |
| Volume-service root returns 400 | It is not the bucket dashboard; use the filer or admin console |
| Forward exits after a pod restart | Wait for readiness and run the forwarding helper again |
| `oc` cannot connect | Run `okd-env`; start the cluster with `okd-start` if stopped |

Read service logs when needed:

```bash
oc -n bigdata logs seaweedfs-0 --tail=50
```

Press Ctrl+C in the forwarding terminal when finished. This stops that helper's forward; it does not stop SeaweedFS or delete data. Existing forwards started elsewhere are unaffected.

## Continue

- [SeaweedFS S3 API with AWS CLI](SeaweedFS-S3-API.md)
- [Polaris REST API with SeaweedFS](Polaris-REST-API.md)
- [API exercise results](API-VALIDATION.md)
- [Polaris and Iceberg](../06-Polaris-Iceberg/README.md)
- [MovieLens](../06-Polaris-Iceberg/MovieLens.md)

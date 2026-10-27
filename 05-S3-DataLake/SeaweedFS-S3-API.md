# SeaweedFS S3 API with AWS CLI

This exercise verifies bucket creation, object upload, listing, download and deletion through the OpenShift SeaweedFS Service. It uses a new test bucket and leaves `warehouse` and existing objects unchanged.

## 1. Connect and check the Service

Run in a Linux Bash terminal from the course repository root:

```bash
source ~/.bashrc
okd-env
oc -n bigdata get pods -l app=seaweedfs
oc -n bigdata get service seaweedfs
```

If the cluster is stopped, run `okd-start` and wait for completion. Expect the SeaweedFS pod to be Running and Ready.

Verify the command-line prerequisites:

```bash
command -v curl jq aws python3 cmp
```

## 2. Forward S3 and the web interfaces

In a separate terminal, load cluster access and keep this command running:

```bash
okd-env
bash 05-S3-DataLake/forward-seaweedfs.sh
```

The S3 API is `http://127.0.0.1:19001`; the admin console is `http://127.0.0.1:19002/`. Existing working listeners can be reused. See [web access instructions](README.md) for bucket browsing and remote-browser tunnels.

An unsigned request can establish HTTP reachability, but does not verify S3 credentials:

```bash
curl -i --max-time 15 http://127.0.0.1:19001/
```

An XML authentication error is normal for an unsigned request. Use authenticated commands for the actual test.

## 3. Configure terminal credentials

```bash
export AWS_ACCESS_KEY_ID=team
export AWS_SECRET_ACCESS_KEY=team1234
export AWS_DEFAULT_REGION=us-east-1
export AWS_PAGER=""
export AWS_EC2_METADATA_DISABLED=true
export S3_ENDPOINT=http://127.0.0.1:19001
```

Use the installation's configured credentials if changed. Do not print the secret key.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls
```

## 4. Create an isolated bucket and test object

The executable walkthrough performs the operations below and saves the responses in a private local state directory:

```bash
bash 05-S3-DataLake/test-seaweedfs-s3.sh create
```

It generates names such as:

```text
Bucket: test-polaris-demo-<random-id>
Object: test-polaris-demo_object_<random-id>.txt
```

S3 bucket names use hyphens rather than underscores. The script stops if the bucket already exists; it never adopts an existing bucket.

The test performs:

1. List buckets with authenticated S3 access.
2. Create the new bucket.
3. Create a local text file.
4. Upload it with `s3api put-object`.
5. Inspect it with `head-object` and `list-objects-v2`.
6. Download it with `get-object` and compare it byte-for-byte using `cmp`.
7. Read it through `s3 cp ... -` and compare again.

Successful output includes:

```text
SEAWEEDFS_S3_CREATE_UPLOAD_LIST_DOWNLOAD_PASS
STATE_FILE=/path/to/private/state.json
```

The state file contains resource names and the local endpoint, not credentials. Keep its exact path for inspection and cleanup.

## 5. Inspect the same test manually

Set `STATE_FILE` to the path printed above, then load the guarded names:

```bash
source 05-S3-DataLake/demo-common.sh
load_state "$STATE_FILE"
OBJECT=$(jq -er '.key' "$STATE_FILE")
```

Inspect the bucket and object:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/"
aws --endpoint-url "$S3_ENDPOINT" s3api head-object --bucket "$BUCKET" --key "$OBJECT"
aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$BUCKET/$OBJECT" -
```

The final command should print the test text. The saved files also allow a direct comparison:

```bash
cmp "$STATE_DIR/input.txt" "$STATE_DIR/download.txt"
```

No output from `cmp` means the files are identical.

## 6. Endpoint selection

| Where the client runs | Endpoint |
|---|---|
| Linux terminal with the forward running | `http://127.0.0.1:19001` |
| Container in namespace `bigdata` | `http://seaweedfs:8333` |
| Container in another namespace | `http://seaweedfs.bigdata.svc.cluster.local:8333` |

Do not use Docker network inspection or Docker port mappings in this deployment. Inside a container, `localhost` refers to that container.

## 7. Delete the test object and bucket

Run cleanup only for the state file created by this exercise:

```bash
bash 05-S3-DataLake/test-seaweedfs-s3.sh cleanup "$STATE_FILE"
```

Cleanup checks the recorded bucket name, random ID, endpoint and object key. It refuses to delete a bucket containing unexpected objects. It deletes the test object, verifies an empty bucket, deletes that bucket, and verifies its absence. It does not use `--force`.

The underlying AWS CLI deletion operations are:

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api delete-object --bucket "$BUCKET" --key "$OBJECT"
aws --endpoint-url "$S3_ENDPOINT" s3api delete-bucket --bucket "$BUCKET"
```

Prefer the cleanup script because it performs ownership and empty-bucket checks before these commands. Do not substitute `warehouse` or a bucket referenced by an existing Polaris catalog. The [Polaris REST exercise](Polaris-REST-API.md) creates its own separate bucket.

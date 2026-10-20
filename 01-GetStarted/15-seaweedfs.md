# SeaweedFS: S3-compatible object storage

Use the Linux VM terminal for these commands. Run each step and inspect its result before continuing. The course deployment combines the SeaweedFS master, volume server, filer, S3 gateway, and admin UI in one mini-mode pod. This lesson uses only the S3-compatible API for bucket and object operations.

A bucket contains objects. Each object has a key, such as `input/hello.txt`; the slash separates a prefix in the key rather than creating a filesystem directory. The sample bucket is temporary and is deleted at the end. Never use `warehouse` or another application's bucket for these exercises.

## 1. Initialize the VM terminal

Load cluster access and select `bigdata`. Complete [Bash configuration](../00-bashrc.md) first. If the cluster is stopped, run `okd-start` instead.

```bash
okd-env
```

## 2. Find the pod, container, and storage

List the SeaweedFS pod. Confirm that `seaweedfs-0` is `Running` and `READY` is `1/1`.

```bash
oc -n bigdata get pods -l app=seaweedfs -o wide
```

Inspect the StatefulSet that manages the pod's stable name.

```bash
oc -n bigdata get statefulset seaweedfs
```

Check that its persistent storage claim is `Bound`. This storage contains existing application data as well as lesson data; do not delete it.

```bash
oc -n bigdata get pvc seaweedfs-data
```

Show the container name used with `exec -c` and `logs -c`.

```bash
oc -n bigdata get pod seaweedfs-0 -o jsonpath='{.spec.containers[*].name}{"\n"}'
```

Read recent logs to check startup or authentication errors.

```bash
oc -n bigdata logs seaweedfs-0 -c seaweedfs --tail=40
```

## 3. Inspect Services and ports

Show the Service's cluster address and exposed ports.

```bash
oc -n bigdata get service seaweedfs -o wide
```

Inspect named ports and the pod endpoints behind the Service.

```bash
oc -n bigdata describe service seaweedfs
```

The in-cluster S3 endpoint is `http://seaweedfs.bigdata.svc.cluster.local:8333`. A `ClusterIP` Service is internal to the cluster; use port-forwarding from the VM.

| Interface | Service port | VM port in this lesson | Access |
|---|---:|---:|---|
| S3-compatible API | 8333 | 19001 | Access key `team`, secret key `team1234` |
| Admin web UI | 23646 | 19002 | Username `team`, password `team1234` |
| Master web UI | 9333 | 19333 | No login configured in this lab |
| Filer web UI | 8888 | 18889 | No login configured in this lab |
| Volume HTTP | 9340 | Not forwarded here | Internal storage interface |

The Service also publishes gRPC ports `19333` (master), `19340` (volume), and `18888` (filer). These are not browser UI ports. The VM forward `19333:9333` below targets the master **HTTP** port.

## 4. Open a container shell

The deployed SeaweedFS image has `sh`, but no Bash or AWS CLI. Open its supported shell to inspect the container; do not install packages or modify `/data` for this lesson.

```bash
oc -n bigdata exec -it seaweedfs-0 -c seaweedfs -- sh
```

Inside the container, print the SeaweedFS version.

```bash
weed version
```

Return to the VM terminal before running `oc` or AWS CLI commands.

```bash
exit
```

For an `exec -- bash` example, use the existing Jupyter container, which has Bash. This opens a different pod, not the SeaweedFS server. The S3 exercises below run on the VM, where AWS CLI is installed.

```bash
oc -n bigdata exec -it spark-master-0 -c jupyter -- bash
```

Exit that Bash shell to return to the VM.

```bash
exit
```

## 5. Forward the S3 API to the VM

Open **terminal A** in the VM and run `okd-env`. Start this forward and leave it running throughout the S3 exercises. `127.0.0.1` restricts the listener to the VM.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/seaweedfs 19001:8333
```

Wait for `Forwarding from 127.0.0.1:19001 -> 8333`. The local S3 endpoint is now `http://127.0.0.1:19001`. It is an API endpoint, not an interactive bucket browser; unsigned browser requests can return an S3 XML authentication error.

## 6. Open the admin and web UIs

### Option A: manual port-forward

In a separate **terminal B**, run `okd-env`, then forward the three web interfaces. Keep terminal A's S3 forward running.

```bash
oc -n bigdata port-forward --address=127.0.0.1 service/seaweedfs 19002:23646 19333:9333 18889:8888
```

Open these links in the browser **inside the VM**, for example through your RDP desktop:

| Browser UI | URL | Username | Password |
|---|---|---|---|
| SeaweedFS admin | [http://127.0.0.1:19002](http://127.0.0.1:19002) | `team` | `team1234` |
| Master topology | [http://127.0.0.1:19333](http://127.0.0.1:19333) | None | None |
| Filer browser | [http://127.0.0.1:18889](http://127.0.0.1:18889) | None | None |

Use the admin UI to inspect buckets, users, and storage status. The filer is a lower-level view of storage; perform this lesson's object changes through S3 commands. The admin login and S3 keys happen to have the same values in this classroom deployment, but serve different authentication interfaces.

### Option B: use the existing expose-uis helper

The helper creates port-forwards itself. If you already started option A, press **Ctrl+C in terminal B** first to free its three ports. Keep terminal A running: the helper exposes web UIs and does not forward the S3 API on `19001`.

Change to the reference deployment directory on this VM. The helper belongs to `openshift/workspace`, not this lesson directory.

```bash
cd "$HOME/openshift"
```

Check for `kubectl`, which this helper invokes even though the lesson uses `oc`.

```bash
command -v kubectl
```

If it is missing, expose the installed OpenShift client under its supported `kubectl` command name. Create this user-local link once, only when `kubectl` is absent; `okd-env` must already have made `oc` available.

```bash
ln -s "$(command -v oc)" "$HOME/.local/bin/kubectl"
```

Inspect which SeaweedFS UIs are ready. Pass the current `oc` context explicitly because older helper copies default to a context named `bigdata`, which may not exist. `--list` does not open any ports.

```bash
python3 workspace/expose-uis.py --context "$(oc config current-context)" --only seaweed-admin seaweed-master seaweed-filer --list
```

Start only the SeaweedFS web forwards. The URLs and login details are the same as in option A. Open the displayed URLs in the VM browser. Press **Q or Esc** to stop this helper; it ignores Ctrl+C.

```bash
python3 workspace/expose-uis.py --context "$(oc config current-context)" --only seaweed-admin seaweed-master seaweed-filer
```

## 7. Configure the VM S3 client

Use **terminal C** on the VM for the remaining commands. Keep this terminal open so its variables remain available. Confirm AWS CLI is installed; the training VM has AWS CLI v2.

```bash
aws --version
```

Set the endpoint to terminal A's forward. Every AWS command below includes this endpoint so it targets SeaweedFS.

```bash
export S3_ENDPOINT=http://127.0.0.1:19001
```

Set the classroom S3 access key. This is an API key, not a Linux username.

```bash
export AWS_ACCESS_KEY_ID=team
```

Set its S3 secret key.

```bash
export AWS_SECRET_ACCESS_KEY=team1234
```

Use the lab region for signing requests.

```bash
export AWS_DEFAULT_REGION=us-east-1
```

Disable the AWS CLI output pager so results print directly in this terminal.

```bash
export AWS_PAGER=""
```

Use a temporary local directory for this exercise's files. The next steps use an isolated AWS configuration file rather than changing your normal AWS profile.

```bash
DEMO_DIR=$(mktemp -d /tmp/seaweed-cli-demo.XXXXXX)
```

Point the CLI at that temporary configuration file for this terminal.

```bash
export AWS_CONFIG_FILE="$DEMO_DIR/aws-config"
```

Use path-style addressing: the bucket goes in the URL path, which works with this local endpoint.

```bash
aws configure set default.s3.addressing_style path
```

List existing buckets to confirm signed access. Existing buckets such as `warehouse` belong to applications; leave them untouched.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls
```

## 8. Create and inspect a temporary bucket

Choose a unique demo name. Keep this `BUCKET` value for the whole lesson; the bucket is disposable and must not be used by later lessons or applications.

```bash
BUCKET="cli-temp-demo-bucket-$(date +%Y%m%d%H%M%S)-$RANDOM"
```

Print the name so you can find it in the admin UI. If bucket creation below reports that it already exists, choose a new name; do not reuse someone else's bucket.

```bash
printf '%s\n' "$BUCKET"
```

Create the bucket. Continue only when creation succeeds.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 mb "s3://$BUCKET"
```

List buckets again and locate your demo bucket.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls
```

Check that the bucket exists and is accessible. `head-bucket` normally prints nothing on success.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api head-bucket --bucket "$BUCKET"
```

List the new bucket. An empty bucket produces no object rows.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/"
```

## 9. Upload and list objects

Create a small local text file on the VM.

```bash
printf 'hello seaweedfs\nhello s3\n' > "$DEMO_DIR/hello.txt"
```

Read the local file before uploading it.

```bash
cat "$DEMO_DIR/hello.txt"
```

Upload it as the object key `input/hello.txt`. Uploading again to this key replaces its current contents.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 cp "$DEMO_DIR/hello.txt" "s3://$BUCKET/input/hello.txt"
```

List the top level. `PRE input/` represents a shared key prefix.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/"
```

List every object with readable sizes and a total object count.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/" --recursive --human-readable --summarize
```

Use the S3 API command to list objects under the `input/` prefix as JSON.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api list-objects-v2 --bucket "$BUCKET" --prefix input/
```

Inspect object metadata without downloading its body. Check `ContentLength`, `ContentType`, `ETag`, and `LastModified`. An ETag is not always a file MD5 checksum.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api head-object --bucket "$BUCKET" --key input/hello.txt
```

## 10. Read, download, and verify

Print an S3 object's text to the terminal. S3 has no filesystem `cat`; the final `-` streams the downloaded object to standard output.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$BUCKET/input/hello.txt" -
```

Download the object to a new local filename.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$BUCKET/input/hello.txt" "$DEMO_DIR/downloaded.txt"
```

Read the downloaded file with the VM's `cat` command.

```bash
cat "$DEMO_DIR/downloaded.txt"
```

Compare the source and download byte for byte. No output means the files match; stop and investigate any difference.

```bash
diff "$DEMO_DIR/hello.txt" "$DEMO_DIR/downloaded.txt"
```

Download with the lower-level `s3api` alternative. This also prints response metadata.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3api get-object --bucket "$BUCKET" --key input/hello.txt "$DEMO_DIR/api-download.txt"
```

## 11. Copy and rename objects

Copy the object to a second key in the same demo bucket.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$BUCKET/input/hello.txt" "s3://$BUCKET/copies/hello-copy.txt"
```

Move that copy to another key. S3 renaming is a copy followed by deletion of the source key; it is not an atomic filesystem rename. The original `input/hello.txt` remains.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 mv "s3://$BUCKET/copies/hello-copy.txt" "s3://$BUCKET/copies/hello-renamed.txt"
```

List objects under `copies/` and confirm the new key.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/copies/"
```

## 12. Upload and download multiple files

Create a local input directory.

```bash
mkdir -p "$DEMO_DIR/upload"
```

Create the first sample file.

```bash
printf 'red blue red\n' > "$DEMO_DIR/upload/colors.txt"
```

Create the second sample file.

```bash
printf 'one two\n' > "$DEMO_DIR/upload/numbers.txt"
```

Preview the synchronization. `--dryrun` prints planned uploads without writing objects.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 sync "$DEMO_DIR/upload/" "s3://$BUCKET/batch/" --dryrun
```

Upload new or changed files under `batch/`. This command does not use `--delete`.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 sync "$DEMO_DIR/upload/" "s3://$BUCKET/batch/"
```

Download the whole prefix to a new local directory.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 cp "s3://$BUCKET/batch/" "$DEMO_DIR/batch-download/" --recursive
```

Compare both directories to verify the round trip. No output means their contents match.

```bash
diff -r "$DEMO_DIR/upload" "$DEMO_DIR/batch-download"
```

## 13. Open a temporary signed object URL

Generate a URL valid for five minutes. It grants temporary access to this demo object without entering S3 keys in the browser. Keep terminal A's forward running.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 presign "s3://$BUCKET/input/hello.txt" --expires-in 300
```

Copy the returned URL into the **VM browser**. Its hostname is `127.0.0.1`, so it refers to this VM; it will not reach the VM from a different computer. The admin UI uses its separate `team` / `team1234` login, while this signed URL needs no login prompt.

## 14. Delete only this lesson's temporary objects and bucket

These deletion commands are intentional for the disposable bucket you created in section 8. Do not substitute `warehouse` or any existing application bucket. Keep the same terminal and verify the bucket name before proceeding.

```bash
printf 'Temporary bucket to delete: %s\n' "$BUCKET"
```

Delete only the renamed copy to demonstrate removal of one object.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 rm "s3://$BUCKET/copies/hello-renamed.txt"
```

Preview the remaining object deletions and confirm that every path belongs to your `cli-temp-demo-bucket-...` bucket.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 rm "s3://$BUCKET/" --recursive --dryrun
```

Delete the remaining demo objects. This affects all keys in this temporary bucket, not other buckets.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 rm "s3://$BUCKET/" --recursive
```

Check that no objects remain. Expect no object rows.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://$BUCKET/" --recursive
```

Remove the empty bucket. Without `--force`, this refuses to remove a bucket that still contains objects.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 rb "s3://$BUCKET"
```

List buckets again. Your temporary bucket should be absent; pre-existing buckets should remain.

```bash
aws --endpoint-url "$S3_ENDPOINT" s3 ls
```

The local files remain under the printed temporary directory for inspection; they are not stored in the course workspace.

```bash
printf 'Local demo files: %s\n' "$DEMO_DIR"
```

Stop the manual port-forwards with Ctrl+C in their terminals, or stop `expose-uis.py` with Q/Esc. Close terminal C to discard its temporary client environment. Start a new terminal for later work so it does not retain this AWS configuration.

## 15. Troubleshoot access

If the endpoint refuses connections, confirm terminal A is still forwarding `19001:8333`. Inspect Service endpoints for ready pod addresses.

```bash
oc -n bigdata get endpointslice -l kubernetes.io/service-name=seaweedfs -o wide
```

If the pod is not ready, inspect its events before changing anything.

```bash
oc -n bigdata describe pod seaweedfs-0
```

For `AccessDenied` or signature errors, check the endpoint, `team` / `team1234` API credentials, and `us-east-1` region in terminal C. For `Address already in use`, stop the previous forward or UI helper rather than starting a second copy on the same VM port. For `bash: not found` inside SeaweedFS, use `sh` as shown above.

If `okd-env` says the cluster is stopped even though `crc status` reports `OKD: Running`, update the helper from [Bash configuration](../00-bashrc.md). Its status check must accept both `OpenShift: Running` and `OKD: Running`.

Command references: [AWS CLI S3 operations](https://docs.aws.amazon.com/cli/latest/userguide/cli-services-s3-commands.html), [object metadata](https://docs.aws.amazon.com/cli/latest/reference/s3api/head-object.html), and [SeaweedFS](https://github.com/seaweedfs/seaweedfs).

## Watch Kubernetes logs

`oc logs` is the Kubernetes equivalent of `docker logs`. Run follow commands in a separate VM terminal after `okd-env`. Press Ctrl+C to stop following; this does not stop the workload. A scaled-to-zero workload has no current pod logs.

Follow SeaweedFS logs while running S3 commands.

```bash
oc -n bigdata logs -f seaweedfs-0 -c seaweedfs --tail=50 --timestamps
```

Read storage messages from the last ten minutes.

```bash
oc -n bigdata logs seaweedfs-0 -c seaweedfs --since=10m --timestamps
```

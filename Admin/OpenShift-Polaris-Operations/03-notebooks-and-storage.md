# 03: PySpark with the same principals and SeaweedFS

Run sections 00?02 first. Keep credentials outside committed course source. The notebook configuration is private and generated from this run's principal response files plus the existing S3 Secret.

## Generate private configuration

Continue in the same working Bash terminal:

```bash
export S3_ACCESS_KEY=$(oc -n "$NS" get secret lab-credentials -o jsonpath='{.data.s3-access-key}' | base64 --decode)
export S3_SECRET_KEY=$(oc -n "$NS" get secret lab-credentials -o jsonpath='{.data.s3-secret-key}' | base64 --decode)
python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ['STATE'])
# Private configuration for comparing the four roles.
# Keep this file private: it contains all four identities.
principals = {role:json.loads((p/(role+'.json')).read_text())['credentials']
              for role in ['admin','developer','ops','viewer']}
source = json.loads((p/'training-source.json').read_text())
source = source.get('catalog',source)
endpoint = source['storageConfigInfo'].get('endpointInternal') or source['storageConfigInfo']['endpoint']
cfg = {'catalog':os.environ['CATALOG'], 'run_id':os.environ['RUN_ID'],
       'polaris_uri':'http://polaris:8181/api/catalog',
       'spark_master':'spark://spark-master:7077',
       's3_endpoint':endpoint, 'bucket':'warehouse',
       's3_access_key':os.environ['S3_ACCESS_KEY'], 's3_secret_key':os.environ['S3_SECRET_KEY'],
       'principals':principals}
(p/'private-lab.json').write_text(json.dumps(cfg,indent=2))
print('Private notebook configuration created; credential values not displayed.')
PY
printf '%s
' "$RUN_ID" > .local-state/last-run
```

This private file contains all four identities and S3 credentials. Use it only for the role comparison. Ops uses curl metadata calls without S3 credentials. Anyone who can read this file can switch identities.

## Copy only the required files to the existing notebook PVC

```bash
oc -n "$NS" exec spark-master-0 -c jupyter -- mkdir -p /workspace/user_notebooks/OpenShift-Polaris-Operations
oc -n "$NS" cp ./01-developer-orders.ipynb spark-master-0:/workspace/user_notebooks/OpenShift-Polaris-Operations/01-developer-orders.ipynb -c jupyter
oc -n "$NS" cp ./02-viewer-and-denied-writes.ipynb spark-master-0:/workspace/user_notebooks/OpenShift-Polaris-Operations/02-viewer-and-denied-writes.ipynb -c jupyter
oc -n "$NS" cp "$STATE/private-lab.json" spark-master-0:/workspace/user_notebooks/OpenShift-Polaris-Operations/private-lab.json -c jupyter
oc -n "$NS" exec spark-master-0 -c jupyter -- chmod 600 /workspace/user_notebooks/OpenShift-Polaris-Operations/private-lab.json
```

Use an existing Jupyter session or forward it in another terminal:

```bash
oc -n bigdata port-forward --address=127.0.0.1 pod/spark-master-0 28888:8888
```

Open http://127.0.0.1:28888/lab in the VM browser. Use a fresh Python kernel for each notebook and run them in order.

## Notebook 1: developer records and storage

`01-developer-orders.ipynb` authenticates as the new developer. It appends four records to the curl-created table, updates one amount, creates a second table and a second namespace, checks exact rows and a total of 420, and checks physical Iceberg Parquet and metadata objects in SeaweedFS. It also creates an independent Parquet round-trip under this run's S3 prefix.

The notebook refuses to append if the target table already contains records. Repeating the data-writing exercise requires a fresh run, or a deliberate review/reset of only the run's own tables. Do not add an unconditional overwrite to make assertions pass.

## Notebook 2: viewer read and denied writes

`02-viewer-and-denied-writes.ipynb` authenticates as viewer in a separate kernel. It reads the exact four updated records and total 420. It attempts a table-property change and a namespace creation, verifies an authorization denial rather than a generic error, and verifies the protected property was not changed. Metadata-only denied writes avoid deliberately creating uncommitted data files in the shared S3 bucket.

These checks demonstrate Polaris denying catalog commits. Direct S3 access remains governed by the shared S3 account, as described in README.

## Troubleshooting

- HTTP 401: obtain a fresh role token; verify realm and credential response file without printing it.
- HTTP 403: inspect the role chain and grant documents. Do not switch to bootstrap in a notebook to hide the failure.
- HTTP 409: stale catalog entity version, table UUID/commit conflict, or existing resource; inspect which one.
- S3 access denied: catalog authorization and S3 authentication are separate; verify endpoint and existing Secret mapping.
- Worker unavailable: inspect `oc get pods`, the Spark master UI and worker logs. Do not change replica counts to bypass preflight.
- A prior Spark session is reused: stop it and restart the notebook kernel so the new role's configuration takes effect.
- No records visible: complete notebook 1 before notebook 2. Curl metadata creation alone does not insert rows.

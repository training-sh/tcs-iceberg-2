# API exercise results

Both API exercises were executed successfully on both representative OpenShift installations. Each used independently generated resources; existing catalogs, the warehouse bucket and application tables were unchanged.

## SeaweedFS S3 API

| Check | Result |
|---|---|
| Authenticated bucket listing | Passed |
| Create isolated demo bucket | Passed |
| Upload object | Passed |
| Head and list object | Passed |
| Download and compare bytes | Passed |
| Copy object to standard output and compare | Passed |
| Delete object, verify empty bucket | Passed |
| Delete bucket and verify absence | Passed |

## Polaris REST API

| Check | Result |
|---|---|
| Readiness and OAuth token | Passed |
| Catalog create/list/describe | Passed |
| Iceberg REST configuration discovery | Passed |
| Namespace create/list/describe | Passed |
| Table create/list/load and schema | Passed |
| Locate actual metadata JSON in SeaweedFS | Passed |
| Download metadata and compare UUID, format and schema ID | Passed |
| Delete table registration and verify HTTP 404 | Passed |
| Delete namespace and verify HTTP 404 | Passed |
| Delete catalog and verify HTTP 404 | Passed |
| Delete only demo bucket objects and bucket | Passed |

Catalog creation returned HTTP 201. Namespace and table creation returned HTTP 200. Successful catalog-entry deletions returned HTTP 204. The empty table had an actual metadata JSON object in S3, schema ID 0 and no snapshots; creating it did not write table rows, data manifests or a data-bearing snapshot.

The initial request to delete with `purgeRequested=true` returned HTTP 403 under the configured principal. The tested cleanup uses `purgeRequested=false` and separately removes physical objects from the dedicated test bucket after all catalog entries are gone. No new privileges were granted to bypass the policy.

All resources created by the acceptance runs were cleaned up. Private request/response state and local execution evidence were retained separately. OAuth tokens and host access credentials are not included in the course material; the guides show only the configured demo account defaults.

Missing Polaris localhost forwards were opened with the helper; existing forwarding processes were preserved. No image, manifest, Secret, PVC or installed system service was changed. These API results do not substitute for the Spark row-write/read exercises in the Iceberg notebooks.

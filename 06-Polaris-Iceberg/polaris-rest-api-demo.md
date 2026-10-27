# Testing Apache Polaris REST API with SeaweedFS

This walkthrough tests an Apache Polaris installation entirely from the Linux command line using `curl` and `jq`.

The Polaris catalog will use **SeaweedFS S3-compatible object storage** instead of local `FILE` storage.

We will:

1. Verify SeaweedFS S3 storage
2. Check Polaris health
3. Obtain an OAuth access token
4. Create `test_catalog`
5. List and describe catalogs
6. Create `test_database` as an Iceberg namespace
7. List and describe namespaces
8. Create `test_table`
9. List and describe tables
10. Delete the table, namespace, and catalog

The test hierarchy will be:

```text
test_catalog
└── test_database
    └── test_table
        ├── id   BIGINT
        └── name STRING
```

The physical Iceberg metadata will be stored under:

```text
s3://polaris-test/
```

> `test_database` is called a **namespace** in the Iceberg REST API.

---

# Environment

The local environment used by this example is:

```text
Polaris REST API:        http://localhost:18181
Polaris Health API:      http://localhost:18182

SeaweedFS S3 Host API:   http://localhost:19001
SeaweedFS Docker API:    http://seaweedfs:8333

S3 Access Key:           team
S3 Secret Key:           team1234
S3 Region:               us-east-1

S3 Bucket:               polaris-test
```

Both Polaris and SeaweedFS should be connected to:

```text
dataeng-network
```

---

# 1. Install Required Command-Line Tools

```bash
sudo apt update
sudo apt install -y curl wget jq awscli
```

Verify:

```bash
curl --version
jq --version
aws --version
```

---

# 2. Configure SeaweedFS S3 Credentials

Set the credentials:

```bash
export AWS_ACCESS_KEY_ID=team
export AWS_SECRET_ACCESS_KEY=team1234
export AWS_DEFAULT_REGION=us-east-1
```

Verify the non-secret settings:

```bash
echo "$AWS_ACCESS_KEY_ID"
echo "$AWS_DEFAULT_REGION"
```

Expected:

```text
team
us-east-1
```

---

# 3. Verify SeaweedFS S3

Check the S3 endpoint:

```bash
curl -i http://localhost:19001/
```

A response similar to this is expected:

```text
HTTP/1.1 403 Forbidden
Content-Type: application/xml
Server: SeaweedFS
```

The `403` is expected because this direct `curl` request does not contain S3 authentication.

Now test authenticated access:

```bash
aws --endpoint-url http://localhost:19001 s3 ls
```

---

# 4. Create the Polaris S3 Bucket

Create the bucket if it does not already exist:

```bash
aws --endpoint-url http://localhost:19001 \
  s3 mb s3://polaris-test
```

If the bucket already exists, this step can be skipped.

Verify:

```bash
aws --endpoint-url http://localhost:19001 s3 ls
```

The output should contain:

```text
polaris-test
```

---

# 5. Test Writing to SeaweedFS

Create a test file:

```bash
echo "SeaweedFS S3 test" > /tmp/seaweed-test.txt
```

Upload it:

```bash
aws --endpoint-url http://localhost:19001 \
  s3 cp /tmp/seaweed-test.txt s3://polaris-test/test.txt
```

List the bucket:

```bash
aws --endpoint-url http://localhost:19001 \
  s3 ls s3://polaris-test/
```

Remove the test object:

```bash
aws --endpoint-url http://localhost:19001 \
  s3 rm s3://polaris-test/test.txt
```

The bucket itself should remain because Polaris will use it.

---

# 6. Verify the Docker Network

Check the containers attached to `dataeng-network`:

```bash
docker network inspect dataeng-network \
  --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}'
```

The output should include:

```text
seaweedfs
```

and the Polaris container.

From the Linux host, SeaweedFS is accessed using:

```text
http://localhost:19001
```

From the Polaris container, SeaweedFS is accessed using:

```text
http://seaweedfs:8333
```

> Do not use `localhost:19001` as the Polaris internal endpoint. Inside the Polaris container, `localhost` refers to Polaris itself.

---

# Polaris Configuration Requirement

Because this SeaweedFS configuration uses static S3 credentials, the Polaris container must also have access to:

```text
AWS_ACCESS_KEY_ID=team
AWS_SECRET_ACCESS_KEY=team1234
AWS_REGION=us-east-1
```

For example, the Polaris Docker Compose service should contain:

```yaml
environment:
  AWS_ACCESS_KEY_ID: team
  AWS_SECRET_ACCESS_KEY: team1234
  AWS_REGION: us-east-1
```

After changing the Polaris Docker Compose configuration, recreate the Polaris container.

Verify the variables inside the Polaris container with:

```bash
docker exec <polaris-container-name> \
  env | grep '^AWS_'
```

Expected:

```text
AWS_ACCESS_KEY_ID=team
AWS_SECRET_ACCESS_KEY=team1234
AWS_REGION=us-east-1
```

---

# Polaris REST API

# 7. Set Polaris URL

```bash
export POLARIS_URL="http://localhost:18181"
```

Verify:

```bash
echo "$POLARIS_URL"
```

Expected:

```text
http://localhost:18181
```

---

# 8. Check Polaris Health

Polaris exposes its health service on port `18182`.

```bash
curl -s http://localhost:18182/q/health | jq
```

A healthy Polaris server should report:

```json
{
  "status": "UP"
}
```

Additional health information may also be present.

---

# Authentication

# 9. Obtain an OAuth Access Token

The Polaris instance was bootstrapped with:

```text
Client ID:     team
Client Secret: team1234
```

Obtain an access token:

```bash
export POLARIS_TOKEN=$(curl -s \
  "$POLARIS_URL/api/catalog/v1/oauth/tokens" \
  --user team:team1234 \
  -d 'grant_type=client_credentials' \
  -d 'scope=PRINCIPAL_ROLE:ALL' \
  | jq -r '.access_token')
```

Verify that a token was obtained:

```bash
echo "$POLARIS_TOKEN"
```

A long token string should be displayed.

A safer validation is:

```bash
test -n "$POLARIS_TOKEN" && \
  test "$POLARIS_TOKEN" != "null" && \
  echo "Polaris token obtained successfully"
```

---

# Catalog Operations

# 10. Create `test_catalog`

The catalog will use:

```text
Storage Type:          S3
Base Location:         s3://polaris-test/
External Endpoint:     http://localhost:19001
Internal Endpoint:     http://seaweedfs:8333
Region:                us-east-1
Path Style Access:     true
STS Available:         false
```

The distinction between the two endpoints is important:

```text
Linux host / clients
        |
        v
http://localhost:19001
        |
        v
SeaweedFS S3


Polaris container
        |
        v
http://seaweedfs:8333
        |
        v
SeaweedFS S3
```

Create the catalog:

```bash
curl -s \
  -X POST "$POLARIS_URL/api/management/v1/catalogs" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "catalog": {
      "type": "INTERNAL",
      "name": "test_catalog",
      "properties": {
        "default-base-location": "s3://polaris-test/"
      },
      "storageConfigInfo": {
        "storageType": "S3",
        "allowedLocations": [
          "s3://polaris-test/"
        ],
        "endpoint": "http://localhost:19001",
        "endpointInternal": "http://seaweedfs:8333",
        "region": "us-east-1",
        "pathStyleAccess": true,
        "stsUnavailable": true
      }
    }
  }' | jq
```

> `endpoint` is the endpoint returned for clients running on the Linux host.
>
> `endpointInternal` is the endpoint Polaris itself uses from inside Docker.
>
> `pathStyleAccess: true` is important for S3-compatible storage.
>
> `stsUnavailable: true` tells Polaris not to attempt AWS STS credential vending against SeaweedFS.

---

# 11. List Catalogs

```bash
curl -s \
  "$POLARIS_URL/api/management/v1/catalogs" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

`test_catalog` should appear.

---

# 12. Describe `test_catalog`

```bash
curl -s \
  "$POLARIS_URL/api/management/v1/catalogs/test_catalog" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

The response should show an S3 storage configuration similar to:

```text
storageType       = S3
endpoint          = http://localhost:19001
endpointInternal  = http://seaweedfs:8333
region            = us-east-1
pathStyleAccess   = true
stsUnavailable    = true
```

---

# Namespace / Database Operations

An Iceberg **namespace** is similar to a database or schema in SQL systems.

For this test:

```text
Iceberg namespace = test_database
```

---

# 13. Create `test_database`

```bash
curl -s \
  -X POST \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": [
      "test_database"
    ],
    "properties": {}
  }' | jq
```

---

# 14. List Databases / Namespaces

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

Expected hierarchy:

```text
test_catalog
└── test_database
```

---

# 15. Describe `test_database`

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

---

# Iceberg Table Operations

# 16. Create `test_table`

Create a simple Iceberg table containing:

```text
id    BIGINT NOT NULL
name  STRING
```

Run:

```bash
curl -s \
  -X POST \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_table",
    "schema": {
      "type": "struct",
      "schema-id": 0,
      "fields": [
        {
          "id": 1,
          "name": "id",
          "required": true,
          "type": "long"
        },
        {
          "id": 2,
          "name": "name",
          "required": false,
          "type": "string"
        }
      ]
    }
  }' | jq
```

The logical hierarchy is now:

```text
test_catalog
└── test_database
    └── test_table
        ├── id
        └── name
```

---

# 17. List Tables

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

`test_table` should appear.

---

# 18. Describe / Load `test_table`

Retrieve the Iceberg table metadata:

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables/test_table" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

Display only the table schemas:

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables/test_table" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq '.metadata.schemas'
```

Display the current schema ID:

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables/test_table" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq '.metadata["current-schema-id"]'
```

---

# Verify Iceberg Metadata in SeaweedFS

# 19. Inspect the S3 Bucket

After the table has been created, inspect the bucket:

```bash
aws --endpoint-url http://localhost:19001 \
  s3 ls s3://polaris-test/ \
  --recursive
```

Iceberg metadata objects should now be visible under the catalog storage location.

This is an important verification because it demonstrates the complete path:

```text
Polaris REST API
        |
        v
Iceberg Catalog
        |
        v
SeaweedFS S3 API
        |
        v
s3://polaris-test/
        |
        v
Iceberg metadata
```

---

# Verify Everything

# 20. List Catalogs

```bash
curl -s \
  "$POLARIS_URL/api/management/v1/catalogs" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

---

# 21. List Namespaces

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

---

# 22. List Tables

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

At this point the logical structure should be:

```text
Polaris
└── test_catalog
    └── test_database
        └── test_table
```

The physical metadata is stored in:

```text
SeaweedFS
└── polaris-test
    └── Iceberg metadata
```

---

# Delete Test Objects

Objects should be deleted from the bottom of the hierarchy upward:

```text
Table
  ↓
Namespace
  ↓
Catalog
```

---

# 23. Delete `test_table`

```bash
curl -s \
  -X DELETE \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables/test_table" \
  -H "Authorization: Bearer $POLARIS_TOKEN"
```

Verify:

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database/tables" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

---

# 24. Delete `test_database`

```bash
curl -s \
  -X DELETE \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces/test_database" \
  -H "Authorization: Bearer $POLARIS_TOKEN"
```

Verify:

```bash
curl -s \
  "$POLARIS_URL/api/catalog/v1/test_catalog/namespaces" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

---

# 25. Delete `test_catalog`

Catalogs are managed through the Polaris Management API:

```bash
curl -s \
  -X DELETE \
  "$POLARIS_URL/api/management/v1/catalogs/test_catalog" \
  -H "Authorization: Bearer $POLARIS_TOKEN"
```

Verify:

```bash
curl -s \
  "$POLARIS_URL/api/management/v1/catalogs" \
  -H "Authorization: Bearer $POLARIS_TOKEN" \
  | jq
```

`test_catalog` should no longer appear.

---

# 26. Inspect SeaweedFS After Cleanup

```bash
aws --endpoint-url http://localhost:19001 \
  s3 ls s3://polaris-test/ \
  --recursive
```

The S3 bucket itself can remain available for future Polaris testing.

---

# REST API Summary

| Operation | API | Method |
|---|---|---|
| Health check | `/q/health` on port `18182` | `GET` |
| Obtain token | `/api/catalog/v1/oauth/tokens` | `POST` |
| Create catalog | `/api/management/v1/catalogs` | `POST` |
| List catalogs | `/api/management/v1/catalogs` | `GET` |
| Describe catalog | `/api/management/v1/catalogs/test_catalog` | `GET` |
| Create namespace | `/api/catalog/v1/test_catalog/namespaces` | `POST` |
| List namespaces | `/api/catalog/v1/test_catalog/namespaces` | `GET` |
| Describe namespace | `/api/catalog/v1/test_catalog/namespaces/test_database` | `GET` |
| Create table | `/api/catalog/v1/test_catalog/namespaces/test_database/tables` | `POST` |
| List tables | `/api/catalog/v1/test_catalog/namespaces/test_database/tables` | `GET` |
| Load table | `/api/catalog/v1/test_catalog/namespaces/test_database/tables/test_table` | `GET` |
| Delete table | `/api/catalog/v1/test_catalog/namespaces/test_database/tables/test_table` | `DELETE` |
| Delete namespace | `/api/catalog/v1/test_catalog/namespaces/test_database` | `DELETE` |
| Delete catalog | `/api/management/v1/catalogs/test_catalog` | `DELETE` |

---

# Architecture Summary

```text
                    Linux Host
                        |
          +-------------+-------------+
          |                           |
          v                           v
 localhost:18181                 localhost:19001
   Polaris API                  SeaweedFS S3
          |                           ^
          |                           |
          |                    Docker port mapping
          |                           |
          v                           |
    Polaris Container                 |
          |                           |
          | http://seaweedfs:8333     |
          +---------------------------+
                        |
                        v
                 SeaweedFS Container
                        |
                        v
                 s3://polaris-test/
                        |
                        v
                  Iceberg Metadata
```

The important storage configuration is:

```text
storageType       = S3
default location  = s3://polaris-test/
endpoint          = http://localhost:19001
endpointInternal  = http://seaweedfs:8333
region            = us-east-1
pathStyleAccess   = true
stsUnavailable    = true
```

This replaces the earlier `FILE` configuration that failed with:

```text
Unsupported storage type: FILE
```

and uses the already tested SeaweedFS S3-compatible storage instead.

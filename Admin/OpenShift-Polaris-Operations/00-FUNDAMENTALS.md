# Fundamentals: identities, authentication and permissions

Read this chapter before running commands. The main ideas are identity, proof of identity, and permission to perform an action.

## 1. Principal, user and service identity

A **principal** is an identity a system can recognize and make access decisions about. It may represent a person, an application or an automated job.

A **user** usually means a person operating a system. A **service principal** represents software making requests. A person can also run curl using a service principal's credentials.

This exercise creates four Polaris principals named for their intended work: admin, developer, ops and viewer. They authenticate using generated client credentials. Creating them does not create Linux accounts, OpenShift users, Grafana accounts or S3 accounts.

| Term | Meaning here |
|---|---|
| Principal name | Readable name of the Polaris identity |
| Client ID | Identifier used when requesting an OAuth token |
| Client secret | Private credential proving control of that client identity |
| Access token | Temporary bearer credential sent with API requests |
| Realm | The Polaris identity and security context; this exercise uses POLARIS |

The principal name and client ID are different fields. Do not substitute the readable name for the generated client ID. Polaris returns the new client secret during creation or credential rotation; an ordinary principal lookup does not recover it.

## 2. Authentication: proving identity

**Authentication** establishes which identity is making a request.

The client sends its client ID and client secret to the OAuth token endpoint. If accepted, Polaris returns an access token. Later requests send that token in the HTTP Authorization header as `Bearer TOKEN`.

```text
Client ID + client secret
          |
          v
OAuth token endpoint
          |
          v
Access token
          |
          v
Authenticated API request
```

The token has a limited lifetime. Getting a fresh token does not create a new principal or add permissions. Rotating a client secret is a separate operation.

Anyone holding a bearer token can use it while it remains valid. Keep tokens and secrets out of terminal output, screenshots and committed files. The commands save generated credentials in a private local directory.

## 3. Authorization: allowing an action

**Authorization** decides whether an authenticated principal may perform a particular action on a particular object.

A valid token does not automatically permit table creation, data reads or access management. A principal may authenticate successfully and still receive an authorization denial.

| Situation | Interpretation |
|---|---|
| Wrong client credentials | Authentication failed; the token endpoint may return 400 or 401 |
| Missing or expired access token | Authentication is missing or no longer valid |
| Valid token, insufficient privileges | Authorization failed; the exercise checks HTTP 403 |
| Existing resource or stale version | A conflict, commonly HTTP 409; not an authorization test |
| Connection refused or timeout | An access/network/service problem; no permission decision was demonstrated |

The revoke/regrant exercise makes this distinction visible: viewer still obtains a token after its catalog access is removed, but cannot load the table until that access is restored.

## 4. What is being protected?

A permission needs both an action and a target. In this exercise the objects form a hierarchy:

```text
Catalog
  +-- Namespace (database)
        +-- Table
```

- A **catalog** organizes namespaces and defines the storage configuration used by its tables.
- A **namespace** groups tables. It is the Iceberg REST concept used here for a database.
- A **table** has a schema, properties, snapshots and files containing records.

A catalog is not the same thing as an S3 bucket. A bucket stores objects; the catalog tracks the tables and their metadata. Several catalogs can use separate prefixes within one bucket.

**Metadata** describes data: table names, columns, properties, file locations and snapshots. **Table data** means the records in the files. Permission to inspect metadata is distinct from permission to request data credentials or modify records.

## 5. Privileges, roles and grants

A **privilege** names an allowed action. For example, NAMESPACE_CREATE permits namespace creation, TABLE_READ_PROPERTIES permits table metadata inspection, and TABLE_WRITE_DATA permits writing table data through the catalog's authorization checks.

A **role** groups access so it can be assigned and maintained together. A **grant** is an assignment that connects an identity or role to another role, or attaches a privilege to a catalog role for a target object.

Polaris uses two kinds of roles:

| Role type | Purpose |
|---|---|
| Principal role | Groups principals that should receive the same access assignments |
| Catalog role | Holds privileges for one catalog and its protected objects |

The role chain is:

```text
Principal
   -> Principal role
      -> Catalog role
         -> Privilege on a catalog, namespace or table
```

The setup therefore performs three assignments:

1. Assign a principal role to the principal.
2. Assign a catalog role to that principal role.
3. Grant the required object privileges to the catalog role.

Creating a role without connecting the chain does not give the principal useful access. Likewise, assigning an empty catalog role grants no object privileges.

A principal can have several principal roles, and a principal role can receive several catalog roles. When investigating unexpected access, inspect all assignments. Removing one role may not remove a privilege available through another role.

The commands grant privileges at catalog scope to keep the exercise short. Those privileges apply to the relevant objects within the exercise catalog. They do not automatically apply to another catalog. Namespace- and table-level grants allow narrower access when needed.

The token request uses `scope=PRINCIPAL_ROLE:ALL`. This activates the principal roles available to that identity. It does not grant every privilege or turn the principal into an administrator.

## 6. Where do groups fit?

A **group** is a collection of identities managed together. Linux groups, OpenShift groups and identity-provider groups belong to their own identity systems; creating one does not automatically change Polaris permissions.

This exercise does not create a separate group resource. A shared Polaris principal role provides the grouping needed here: assign the same principal role to several principals when they need the same catalog access. External identity-provider integration is a separate setup and is not required for these commands.

## 7. The four identities in this exercise

The names describe intended work; the configured grants provide the actual permissions. Naming an account admin or viewer does not grant anything by itself.

| Principal | Allowed work | Expected restriction |
|---|---|---|
| Admin | Manage the exercise catalog's properties, content and access grants | Cannot inspect the unrelated training catalog or manage realm-wide principals |
| Developer | Create/edit namespaces and tables, insert/update records, and delete content | Cannot grant catalog access to another role |
| Ops | Inspect catalog, namespace and table metadata | Cannot create tables or request delegated data credentials |
| Viewer | Inspect and read existing tables | Cannot create namespaces or change table properties |

The existing **bootstrap administrator** creates the initial principals and catalog. The new **exercise admin** receives access only to that catalog. Keeping these identities separate avoids granting global administration just to demonstrate catalog management.

Developer receives CATALOG_MANAGE_CONTENT, which includes deletion as well as creation and updates. It is suitable for this isolated exercise catalog; it is broader than a write-only production role.

## 8. Polaris permission and S3 permission are separate

A Spark read uses Polaris to locate the table, then reads its files from SeaweedFS. Both catalog access and storage access matter.

```text
Spark -> Polaris: identify the table and check catalog permissions
Spark -> SeaweedFS: access the table files using S3 credentials
```

This installation uses shared S3 credentials and has no working STS credential vending. The viewer notebook uses its Polaris principal plus separately supplied S3 credentials. Ops is demonstrated using metadata API calls without those S3 credentials.

Someone who independently obtains the broad S3 credentials can access files directly. Polaris cannot stop that direct storage request. The private notebook configuration contains all four identities for comparison; possession of that file allows switching identities. It is not a way to isolate separate people sharing the same files.

The ops check deliberately requests delegated data credentials and receives HTTP 403. That proves the Polaris data-privilege check. It does not demonstrate a working STS service or storage isolation.

## 9. Follow the request through the system

Before running a command, identify:

1. Which principal is making the request?
2. Is it using client credentials to obtain a token, or a token to call an API?
3. Which catalog, namespace or table is the target?
4. Which role assignment and privilege should permit the action?
5. Is this a metadata operation, a data operation or an access-management operation?
6. What response would demonstrate success or denial?

Start with [00: Access and authentication](00-access-and-authentication.md). The commands then build the role chain, create objects, check denied actions, and use the same identities in PySpark.

References: [Polaris role-based access control](https://polaris.apache.org/releases/1.8.0/managing-security/access-control/), [Polaris management API](https://github.com/apache/polaris/blob/main/spec/polaris-management-service.yml), [Polaris identity concepts](https://polaris.apache.org/in-dev/unreleased/entities/).

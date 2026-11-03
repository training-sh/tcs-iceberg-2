# class notes

Follow initial 00 authentication notes for getting  token

```
curl -fsS -X POST "http://127.0.0.1:28181/api/management/v1/principals" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
  -H "Polaris-Realm: POLARIS" \
  -H "Content-Type: application/json" \
  -d '{"principal":{"name":"bigdata_admin"},"credentialRotationRequired":false}'
```

```
	
curl -fsS -X POST "http://127.0.0.1:28181/api/management/v1/principal-roles" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
  -H "Polaris-Realm: POLARIS" \
  -H "Content-Type: application/json" \
  -d '{"principalRole":{"name":"bigdata_admin_role"}}'

```

```
curl -fsS -X POST "http://127.0.0.1:28181/api/management/v1/principal-roles" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
  -H "Polaris-Realm: POLARIS" \
  -H "Content-Type: application/json" \
  -d '{"principalRole":{"name":"bigdata_ops_role"}}'
```

A principal can have one or more roles assigned

```
curl -fsS -X PUT "http://127.0.0.1:28181/api/management/v1/principals/bigdata_admin/principal-roles" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
  -H "Polaris-Realm: POLARIS" \
  -H "Content-Type: application/json" \
  -d '{"principalRole":{"name":"bigdata_admin_role"}}'
```

```
  
curl -fsS -X PUT "http://127.0.0.1:28181/api/management/v1/principals/bigdata_admin/principal-roles" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
  -H "Polaris-Realm: POLARIS" \
  -H "Content-Type: application/json" \
  -d '{"principalRole":{"name":"bigdata_ops_role"}}'
```

```

	curl -fsS -X GET "http://127.0.0.1:28181/api/management/v1/principals/bigdata_admin/principal-roles" \
  -H "Authorization: Bearer $BOOTSTRAP_TOKEN" \
  -H "Polaris-Realm: POLARIS"

```
  

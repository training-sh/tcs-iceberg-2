```
oc -n bigdata port-forward --address=127.0.0.1 service/seaweedfs 19001:8333


excercise  https://github.com/training-sh/tcs-iceberg-2/blob/main/06-Polaris-Iceberg/polaris-rest-api-demo.md

instead of test-* catalog, database, table, you may use demo-*, 
instead of polaris-test s3 bucket, create a bucket demo-bucket

when time permit, 
create a route with domain polaris.apps-crc.testing as domain name, whatever name you choose to the REST API
then use this route with your commands/login/authentication/authorization
```

"""Supplied Polaris catalog initialization, executed by its manifest Job."""
import os,requests
BASE='http://polaris:8181'
r=requests.post(BASE+'/api/catalog/v1/oauth/tokens',headers={'Polaris-Realm':'POLARIS'},data={'grant_type':'client_credentials','client_id':os.environ['POLARIS_CLIENT_ID'],'client_secret':os.environ['POLARIS_CLIENT_SECRET'],'scope':'PRINCIPAL_ROLE:ALL'},timeout=30)
r.raise_for_status();headers={'Polaris-Realm':'POLARIS','Authorization':'Bearer '+r.json()['access_token']}
catalog={'name':'training','type':'INTERNAL','properties':{'default-base-location':'s3://warehouse/iceberg'},'storageConfigInfo':{'storageType':'S3','allowedLocations':['s3://warehouse/iceberg'],'region':'us-east-1','endpoint':'http://seaweedfs:8333','endpointInternal':'http://seaweedfs:8333','pathStyleAccess':True,'stsUnavailable':True}}
r=requests.get(BASE+'/api/management/v1/catalogs/training',headers=headers,timeout=30)
if r.status_code==404:
    r=requests.post(BASE+'/api/management/v1/catalogs',headers=headers,json={'catalog':catalog},timeout=30)
r.raise_for_status()
print('POLARIS_CATALOG_READY training s3://warehouse/iceberg',flush=True)

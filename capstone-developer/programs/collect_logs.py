"""Namespace-only pod log collection with per-container timestamp checkpoints."""
import json,os,ssl,time,urllib.request
from urllib.parse import urlencode
from pathlib import Path
BASE='https://kubernetes.default.svc'
TOKEN=Path('/var/run/secrets/kubernetes.io/serviceaccount/token')
CTX=ssl.create_default_context(cafile='/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')
NS=os.environ['POD_NAMESPACE']; positions={}
def get(path):
    req=urllib.request.Request(BASE+path,headers={'Authorization':'Bearer '+TOKEN.read_text().strip()})
    return urllib.request.urlopen(req,context=CTX,timeout=15).read()
while True:
    try:
        pods=json.loads(get('/api/v1/namespaces/'+NS+'/pods'))['items']
        streams=[]
        for pod in pods:
            name=pod['metadata']['name']
            if name.startswith(('log-collector','loki','prometheus','grafana')): continue
            for container in pod['spec']['containers']:
                key=(pod['metadata']['uid'],container['name']); checkpoint=positions.get(key)
                params={'container':container['name'],'timestamps':'true','tailLines':'300'}
                if checkpoint: params['sinceTime']=checkpoint
                else: params['sinceSeconds']='120'
                try: lines=get('/api/v1/namespaces/'+NS+'/pods/'+name+'/log?'+urlencode(params)).decode(errors='replace').splitlines()
                except Exception: continue
                values=[]; newest=checkpoint
                for line in lines:
                    stamp,_,message=line.partition(' ')
                    if checkpoint and stamp<=checkpoint: continue
                    values.append([str(time.time_ns()),message]); newest=stamp
                if values: streams.append({'stream':{'namespace':NS,'pod':name,'container':container['name']},'values':values})
                if newest: positions[key]=newest
        if streams:
            req=urllib.request.Request('http://loki:3100/loki/api/v1/push',json.dumps({'streams':streams}).encode(),{'Content-Type':'application/json'})
            urllib.request.urlopen(req,timeout=15).close()
    except Exception:
        # Re-read a small overlap after delivery failure; duplicates are preferable to silent loss.
        positions.clear(); print('LOG_COLLECTION_RETRY',flush=True)
    time.sleep(15)

#!/usr/bin/env python3
"""Narrow repairs for existing single-node CRC classroom clusters. Default: plan only."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

TARGETS = {'shuffle': ('service', 'nodemanager'), 'trino': ('statefulset', 'trino'),
           'hdfs': ('statefulset', 'namenode')}


def patch_for(fix, obj):
    if fix == 'shuffle':
        ports = obj['spec'].get('ports', [])
        port = next((p for p in ports if p['port'] == 13562 and p.get('protocol', 'TCP') == 'TCP'), None)
        if port and port.get('targetPort', 13562) == 13562:
            return None
        name = port.get('name', 'shuffle') if port else 'shuffle'
        if any(p.get('name') == name and p['port'] != 13562 for p in ports):
            raise ValueError('Conflicting shuffle port name; inspect Service manually')
        return {'spec': {'ports': [{'name': name, 'port': 13562, 'targetPort': 13562, 'protocol': 'TCP'}]}}
    name = 'trino' if fix == 'trino' else 'namenode'
    container = next(c for c in obj['spec']['template']['spec']['containers'] if c['name'] == name)
    if fix == 'trino':
        env = next((e for e in container.get('env', []) if e['name'] == 'HIVE_METASTORE_HOST'), {})
        if env.get('value') in ('hive-metastore', 'hive-metastore.bigdata.svc.cluster.local'):
            return None
        change = {'name': name, 'env': [{'name': 'HIVE_METASTORE_HOST',
                  'value': 'hive-metastore.bigdata.svc.cluster.local', 'valueFrom': None}]}
    elif fix == 'hdfs':
        key = '-Ddfs.namenode.datanode.registration.ip-hostname-check='
        args = container.get('args', [])
        if not args or args[0] != 'namenode':
            raise ValueError('Unexpected NameNode command; inspect entrypoint manually')
        updated = [a for a in args if not a.startswith(key)] + [key + 'false']
        if updated == args:
            return None
        change = {'name': name, 'args': updated}
    else:
        raise ValueError(fix)
    return {'spec': {'template': {'spec': {'containers': [change]}}}}


def oc(*args):
    return subprocess.check_output(['oc', '--request-timeout=30s', '-n', 'bigdata', *args], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fix', choices=list(TARGETS), action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    opts = parser.parse_args()
    server = subprocess.check_output(['oc', 'config', 'view', '--minify', '-o',
                                     'jsonpath={.clusters[0].cluster.server}'], text=True).strip()
    if server != 'https://api.crc.testing:6443':
        raise SystemExit('Expected local CRC API; run okd-env and inspect context')
    print('Context:', subprocess.check_output(['oc', 'config', 'current-context'], text=True).strip())
    plans = []
    for fix in dict.fromkeys(opts.fix):
        kind, name = TARGETS[fix]
        obj = json.loads(oc('get', kind, name, '-o', 'json'))
        patch = patch_for(fix, obj)
        print(fix + ': ' + ('already configured' if patch is None else json.dumps(patch)))
        if patch:
            if kind == 'statefulset' and obj['spec'].get('replicas', 1) != 1:
                raise SystemExit('Start '+name+' using its lesson first; replicas are preserved')
            plans.append((fix, kind, name, obj, patch))
    if not opts.apply or not plans:
        print('No changes made.' if not opts.apply else 'Already configured; no changes needed.')
        return
    for _, kind, name, _, patch in plans:
        oc('patch', kind, name, '--type=strategic', '-p', json.dumps(patch), '--dry-run=server', '-o', 'name')
    backup = Path(__file__).resolve().parent / '.state/repair-backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True, exist_ok=False)
    for fix, kind, name, obj, patch in plans:
        (backup/(fix+'-before.json')).write_text(json.dumps(obj, indent=2))
        patch['metadata'] = {'resourceVersion': obj['metadata']['resourceVersion']}
        print(oc('patch', kind, name, '--type=strategic', '-p', json.dumps(patch)))
        if kind == 'statefulset':
            subprocess.run(['oc', '-n', 'bigdata', 'rollout', 'status', kind+'/'+name,
                            '--timeout=300s'], check=True)
        if patch_for(fix, json.loads(oc('get', kind, name, '-o', 'json'))) is not None:
            raise RuntimeError('Post-update configuration mismatch: '+fix)
    print('Configuration changed. Backups:', backup)
    print('Run verify.py and lesson exercises. Rollout success is not functional acceptance.')


if __name__ == '__main__':
    main()

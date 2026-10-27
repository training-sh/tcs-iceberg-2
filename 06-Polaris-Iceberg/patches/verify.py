#!/usr/bin/env python3
"""Read-only prerequisite checks, not a substitute for lesson execution."""
import subprocess
import sys

CHECKS = {
    'HDFS': ['exec', 'namenode-0', '--', 'hdfs', 'dfsadmin', '-report'],
    'Hive catalog': ['exec', 'trino-0', '--', 'trino', '--server', 'http://localhost:8080',
                     '--user', 'team', '--execute', 'SHOW SCHEMAS FROM iceberg_hive'],
    'Polaris catalog': ['exec', 'trino-0', '--', 'trino', '--server', 'http://localhost:8080',
                        '--user', 'team', '--execute', 'SHOW SCHEMAS FROM iceberg_polaris'],
    'shuffle Service': ['get', 'service', 'nodemanager', '-o',
                        'jsonpath={range .spec.ports[*]}{.port}:{.targetPort} {end}'],
}


def main():
    failed = False
    for name, command in CHECKS.items():
        try:
            p = subprocess.run(['oc', '--request-timeout=20s', '-n', 'bigdata', *command],
                               text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
            ok = p.returncode == 0
            if name == 'HDFS':
                ok = ok and 'Live datanodes (1)' in p.stdout and 'Safe mode is ON' not in p.stdout
            if name == 'shuffle Service':
                ok = ok and '13562:13562' in p.stdout.split()
            print(('PASS ' if ok else 'FAIL ') + name + '\n' + p.stdout)
            failed |= not ok
        except (OSError, subprocess.TimeoutExpired) as e:
            print('FAIL', name, str(e)); failed = True
    print('Run actual lesson data-write/read exercises after these prerequisites pass.')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())

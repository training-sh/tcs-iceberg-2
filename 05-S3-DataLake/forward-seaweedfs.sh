#!/usr/bin/env bash
# Run in a Linux terminal after okd-env. No cluster or system-service changes.
set -euo pipefail
missing=()
for mapping in 19002:23646 19333:9333 18889:8888 19001:8333; do
  host_port=${mapping%%:*}
  if python3 - "$host_port" <<'PY'
import socket,sys
with socket.socket() as s:
    s.settimeout(1)
    sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)
PY
  then
    echo "Port $host_port is already listening; verify/reuse it."
  else
    missing+=("$mapping")
  fi
done
echo 'Browser: admin http://127.0.0.1:19002/ ; filer http://127.0.0.1:18889/buckets/ ; master http://127.0.0.1:19333/'
if ((${#missing[@]})); then
  exec oc -n bigdata port-forward --address=127.0.0.1 service/seaweedfs "${missing[@]}"
else
  echo 'All requested ports already have listeners. This helper started no processes.'
fi

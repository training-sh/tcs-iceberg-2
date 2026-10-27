#!/usr/bin/env bash
set -euo pipefail
missing=()
for mapping in 18181:8181 18182:8182; do
  if python3 - "${mapping%%:*}" <<'PY'
import socket,sys
with socket.socket() as s:
    s.settimeout(1)
    sys.exit(0 if s.connect_ex(('127.0.0.1', int(sys.argv[1]))) == 0 else 1)
PY
  then echo "Port ${mapping%%:*} already has a listener; verify and reuse it."
  else missing+=("$mapping")
  fi
done
echo 'Polaris API http://127.0.0.1:18181 ; readiness http://127.0.0.1:18182/q/health/ready'
if ((${#missing[@]})); then
  exec oc -n bigdata port-forward --address=127.0.0.1 service/polaris "${missing[@]}"
fi

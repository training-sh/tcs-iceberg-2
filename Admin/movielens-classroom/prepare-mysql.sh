#!/usr/bin/env bash
# One-time scoped database setup using the admin credential already in mysql-0.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$HOME/.crc/bin/oc:$PATH"
oc exec -i -n bigdata mysql-0 -- sh -ec 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql -u root' < 00_prepare_mysql.sql
printf '%s\n' 'Prepared movielens_classroom_s01 and scoped permissions for the existing team user.'

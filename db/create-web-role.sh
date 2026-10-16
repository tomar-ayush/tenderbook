#!/usr/bin/env bash
# Run once on the VM. Creates (or, run again, gives a new password to) the read-only login the website uses, checks it
# can read and cannot write, and prints the DATABASE_URL to paste into Vercel.
#
#   bash db/create-web-role.sh
#
# Settings (defaults in brackets): CONTAINER [postgres]  DB [gem]  OWNER [gem]  ROLE [tenderbook_web]
#                                  HOST [this machine's first address]  PORT [5433]
set -euo pipefail
CONTAINER=${CONTAINER:-postgres}
DB=${DB:-gem}
OWNER=${OWNER:-gem}
ROLE=${ROLE:-tenderbook_web}
HOST=${HOST:-$(hostname -I | awk '{print $1}')}
PORT=${PORT:-5433}
PW=$(openssl rand -hex 24)

as_owner() { sudo docker exec -i "$CONTAINER" psql -X -v ON_ERROR_STOP=1 -U "$OWNER" -d "$DB" "$@"; }
as_web() { sudo docker exec -i -e PGPASSWORD="$PW" "$CONTAINER" psql -X -h 127.0.0.1 -U "$ROLE" -d "$DB" "$@"; }

if [ "$(as_owner -tAc 'SHOW ssl')" != "on" ]; then
  echo "WARNING: TLS (ssl) is off in this Postgres, so the password and data would cross the internet unencrypted."
  echo "         Turn ssl on first, or stop here (Ctrl+C). Continuing in 10 s."
  sleep 10
fi

as_owner -q -v role="$ROLE" -v pw="$PW" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'role') WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'role') \gexec
ALTER ROLE :"role" WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 20 PASSWORD :'pw';
ALTER ROLE :"role" SET default_transaction_read_only = on;
ALTER ROLE :"role" SET statement_timeout = '15s';
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM :"role";
GRANT USAGE ON SCHEMA public TO :"role";
GRANT SELECT ON company, company_summary, participation, tender, buyer_org, stg_contract TO :"role";
SQL

echo "can read:   $(as_web -tAc 'SELECT count(*) FROM company') companies"
if as_web -tAc 'DELETE FROM company WHERE false' >/dev/null 2>&1; then
  echo "ERROR: the login could write; do not use it"; exit 1
fi
echo "cannot write: confirmed"
echo
echo "Paste this into Vercel (Project, Settings, Environment Variables) as DATABASE_URL:"
echo "postgresql://$ROLE:$PW@$HOST:$PORT/$DB?sslmode=require"
echo
echo "Running this script again makes a new password; the old URL stops working."

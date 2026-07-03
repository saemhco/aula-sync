#!/bin/bash
set -euo pipefail

echo "Starting SQL Server..."
/opt/mssql/bin/sqlservr &
SQL_PID=$!

/usr/local/bin/restore-db.sh

echo "SQL Server ready."
wait "$SQL_PID"

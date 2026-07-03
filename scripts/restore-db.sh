#!/bin/bash
set -euo pipefail

SA_PASSWORD="${MSSQL_SA_PASSWORD:?MSSQL_SA_PASSWORD required}"
DB_NAME="${DB_NAME:-DB_UNHEVAL}"
DB_USER="${DB_USER:-aulavirtualunh}"
DB_PASSWORD="${DB_PASSWORD:-4ulavirtualunH20\$20}"
SQL_HOST="${SQL_HOST:-localhost}"
BACKUP="/var/opt/mssql/backup/DB_UNHEVAL.bak"
SQLCMD="/opt/mssql-tools18/bin/sqlcmd"

echo "Waiting for SQL Server..."
for i in $(seq 1 60); do
  if $SQLCMD -S "$SQL_HOST" -U sa -P "$SA_PASSWORD" -C -Q "SELECT 1" &>/dev/null; then
    echo "SQL Server is ready."
    break
  fi
  sleep 2
done

EXISTS=$($SQLCMD -S "$SQL_HOST" -U sa -P "$SA_PASSWORD" -C -h -1 -Q \
  "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.databases WHERE name = '$DB_NAME'" | tr -d '[:space:]')

if [ "$EXISTS" = "1" ]; then
  echo "Database $DB_NAME already exists, skipping restore."
else
  if [ ! -f "$BACKUP" ]; then
    echo "ERROR: Backup file not found at $BACKUP"
    exit 1
  fi

  echo "Reading logical file names from backup..."
  DATA_LOGICAL=$($SQLCMD -S "$SQL_HOST" -U sa -P "$SA_PASSWORD" -C -s "|" -W -Q \
    "RESTORE FILELISTONLY FROM DISK = N'$BACKUP'" | awk -F'|' 'toupper($2) ~ /\.MDF/ { print $1; exit }')
  LOG_LOGICAL=$($SQLCMD -S "$SQL_HOST" -U sa -P "$SA_PASSWORD" -C -s "|" -W -Q \
    "RESTORE FILELISTONLY FROM DISK = N'$BACKUP'" | awk -F'|' 'toupper($2) ~ /\.LDF/ { print $1; exit }')

  if [ -z "$DATA_LOGICAL" ] || [ -z "$LOG_LOGICAL" ]; then
    echo "Could not parse logical names, using defaults..."
    DATA_LOGICAL="${DB_NAME}"
    LOG_LOGICAL="${DB_NAME}_log"
  fi

  echo "Restoring $DB_NAME (data=$DATA_LOGICAL, log=$LOG_LOGICAL)..."
  $SQLCMD -S "$SQL_HOST" -U sa -P "$SA_PASSWORD" -C -Q "
    RESTORE DATABASE [$DB_NAME]
    FROM DISK = N'$BACKUP'
    WITH
      MOVE N'$DATA_LOGICAL' TO N'/var/opt/mssql/data/${DB_NAME}.mdf',
      MOVE N'$LOG_LOGICAL' TO N'/var/opt/mssql/data/${DB_NAME}_log.ldf',
      REPLACE,
      STATS = 10
  "
  echo "Restore completed."
fi

echo "Ensuring login and user $DB_USER..."
$SQLCMD -S "$SQL_HOST" -U sa -P "$SA_PASSWORD" -C -Q "
  IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'$DB_USER')
    CREATE LOGIN [$DB_USER] WITH PASSWORD = N'$DB_PASSWORD', CHECK_POLICY = OFF, DEFAULT_DATABASE = [$DB_NAME];
  ELSE
    ALTER LOGIN [$DB_USER] WITH PASSWORD = N'$DB_PASSWORD', CHECK_POLICY = OFF, DEFAULT_DATABASE = [$DB_NAME];
  USE [$DB_NAME];
  IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'$DB_USER')
    CREATE USER [$DB_USER] FOR LOGIN [$DB_USER];
  ELSE
    ALTER USER [$DB_USER] WITH LOGIN = [$DB_USER];
  ALTER ROLE db_datareader ADD MEMBER [$DB_USER];
  ALTER ROLE db_datawriter ADD MEMBER [$DB_USER];
"

echo "Database setup complete."

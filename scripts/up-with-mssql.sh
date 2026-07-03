#!/bin/bash
# Levanta API + SQL Server e importa el backup si aún no existe
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE_PROFILES=local-db docker compose up -d --build
echo "Listo. Panel: http://localhost:8092/ · API docs: http://localhost:8092/docs"
echo "Seguir restore (solo primera vez): docker compose logs -f sqlserver"

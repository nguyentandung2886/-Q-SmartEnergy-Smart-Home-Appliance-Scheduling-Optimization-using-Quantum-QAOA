#!/bin/bash
set -e

HOST="${SQLSERVER_HOST:-sqlserver}"
DB="${SQLSERVER_DB:-q_smartenergy}"

echo "Waiting for SQL Server at $HOST..."
until sqlcmd -S "$HOST" -U sa -P "$SA_PASSWORD" -Q "SELECT 1" -b -o /dev/null -N -C 2>/dev/null; do
  echo "  not ready, retrying in 3s..."
  sleep 3
done
echo "SQL Server is up."

sqlcmd -S "$HOST" -U sa -P "$SA_PASSWORD" -N -C -Q \
  "IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = N'${DB}') CREATE DATABASE [${DB}]"
echo "Database '${DB}' ready."

exec uvicorn main:app --host 0.0.0.0 --port 8000

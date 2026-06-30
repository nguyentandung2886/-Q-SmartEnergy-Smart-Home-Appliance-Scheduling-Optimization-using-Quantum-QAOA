#!/bin/bash
set -e

# SQLite: the database file is created automatically on first run by
# Base.metadata.create_all (see server/main.py). No external DB to wait for.
exec uvicorn main:app --host 0.0.0.0 --port 8000

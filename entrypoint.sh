#!/bin/bash
set -e

# Bind to the port the platform provides ($PORT on Render/Railway), else 8000.
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"

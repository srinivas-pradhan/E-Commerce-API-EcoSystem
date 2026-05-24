#!/bin/bash

cd "$(dirname "$0")" || exit 1

source .venv/bin/activate

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

fastapi dev --port 8080

# PROD Environment 
#fastapi run --port 8080

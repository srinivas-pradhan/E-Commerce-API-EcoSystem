#!/bin/bash

source .venv/bin/activate

fastapi dev --port 8082

# PROD Environment
#fastapi run --port 8082

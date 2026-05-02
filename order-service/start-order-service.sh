#!/bin/bash

source .venv/bin/activate

fastapi dev --port 8084

# PROD Environment
#fastapi run --port 8084

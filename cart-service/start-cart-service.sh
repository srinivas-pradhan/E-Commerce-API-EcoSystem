#!/bin/bash

source .venv/bin/activate

fastapi dev --port 8081

# PROD Enviornment
#fastapi run --port 8081

#!/bin/bash

source .venv/bin/activate

fastapi dev --port 8083

# PROD Environment
#fastapi run --port 8083

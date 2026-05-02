#!/bin/bash

source .venv/bin/activate

fastapi dev --port 8085

# PROD Environment 
#fastapi run --port 8085

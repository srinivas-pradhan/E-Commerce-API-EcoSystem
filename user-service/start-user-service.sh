#!/bin/bash

source .venv/bin/activate

fastapi dev --port 8080

# PROD Environment 
#fastapi run --port 8080

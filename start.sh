#!/bin/bash
set -e

cd "$(dirname "$0")"

python frontend/server.py

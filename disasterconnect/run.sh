#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d venv ]; then
  echo "Setting up for the first time, please wait..."
  python3 -m venv venv || { echo "Install Python 3 first."; exit 1; }
  venv/bin/python -m pip install -q -r requirements.txt
fi
venv/bin/python app.py

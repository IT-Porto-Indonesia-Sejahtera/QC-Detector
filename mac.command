#!/bin/bash

# Navigate to the script's directory (safe even if user double-clicks from Finder)
cd "$(dirname "$0")"

# Use the Python inside your virtual environment
./venv/bin/python3 main.py

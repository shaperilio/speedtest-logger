#!/bin/bash

# Requires Python 3.8+, `pip`, and `virtualenv`
if [ -d venv ]; then
    echo "Virtual environment exists."
else
    echo "Creating virtual environment."
    virtualenv venv
fi
PYTHON=venv/bin/python
$PYTHON -m pip install -r requirements.txt

echo "Running program..."
$PYTHON exec.py
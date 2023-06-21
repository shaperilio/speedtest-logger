#!/bin/bash
# Check requirements.
if ! command -v virtualenv >/dev/null 2>&1; then
    echo "Please install `virtualenv`."
    exit 1
fi

if ! command -v screen >/dev/null 2>&1; then
    echo "Please install `screen`."
    exit 2
fi

if [ ! -f speedtest-logger-marker ]; then
    echo "Change to repo root directory; current directory is $pwd."
    exit 3
fi

# Requires Python 3.8+, `pip`, and `virtualenv`
if [ -d venv ]; then
    echo "Virtual environment exists."
else
    echo "Creating virtual environment."
    virtualenv venv
fi

PYTHON=venv/bin/python
$PYTHON -m pip install -r requirements.txt

echo "Running data collection on screen ``speedtest-logger-collect``..."
screen -dmS speedtest-logger-collect $PYTHON collector/exec.py

exit 0
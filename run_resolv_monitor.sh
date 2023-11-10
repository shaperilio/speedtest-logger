#!/bin/bash

if [ ! -f speedtest-logger-marker ]; then
    echo "Change to repo root directory; current directory is $pwd."
    exit 3
fi

PYTHON=venv/bin/python

echo "Running ``resolv.conf`` monitor on screen ``speedtest-logger-monitor``..."
sudo screen -dmS speedtest-logger-monitor $PYTHON fixer/resolv_conf.py

exit 0

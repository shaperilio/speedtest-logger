#!/bin/bash

if [ ! -f speedtest-logger-marker ]; then
    echo "Change to repo root directory; current directory is $pwd."
    exit 3
fi

echo "Running dashboard on screen ``speedtest-logger-dashboard``..."
screen -dmS speedtest-logger-dashboard venv/bin/flask --app dashboard.flask_app run --host=0.0.0.0 --port 10000 --reload

exit 0

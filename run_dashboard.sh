#!/bin/bash

echo "Running dashboard on screen ``speedtest-logger-dashboard``..."
screen -dmS speedtest-logger-dashboard venv/bin/flask --app dashboard.flask_app run --host=0.0.0.0 --port 10000

exit 0

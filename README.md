# Introduction

This is a set of two Python scripts to create a dashboard to monitor internet speeds, optionally
separated by interface.

It consists of a data collection script ([`collector`](collector)) and a Flask website
([`dashboard`](dashboard)). Both are intended to run via `screen`, launchable from
[`run_collection.sh`](run_collection.sh) and [`run_dashboard.sh`](run_dashboard.sh), respectively.

Collection should be launched first, as it will ensure the Python prerequisites (and the virtual
environment) are there.

Once the dashboard is running, you'll be able to see it at http://localhost:10000.

# Prerequisites
Python 3.8+ should be installed. You should also install the [Oklah Speedtest
CLI](https://www.speedtest.net/apps/cli). You'll need to point to its path in
[`config.py`](config.py).

# Configuration
[`config.py`](config.py) controls behavior of collection and display of results.

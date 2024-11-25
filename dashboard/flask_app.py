from typing import Dict
from threading import Thread
import time

from flask import Flask, request
from bokeh.models import ColumnDataSource

import config
from .data import (proc_results,
                   filter,
                   smooth,)
from .plots import (log_plot,
                    hourly_plot,
                    daily_plot,)

from utils.timing import TimeIt


from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s: %(message)s',
    }},
    'root': {
        'level': 'DEBUG',
    }
})

app = Flask(__name__)

_all_data: Dict[str, ColumnDataSource] = {}


def _data_grabber():
    """
    Data loader; runs on separate thread. NOTE: if the app is run with
    `--reload`, you will get multiple threads.
    """
    global _all_data
    time.sleep(3)  # need to wait until the app starts.
    while True:
        try:
            with app.app_context():
                # Needs this context to use the app logger :/
                with TimeIt('`proc_results` (in a thread)', log=app.logger):
                    _all_data = proc_results(span_hrs=None)
        except Exception as e:
            app.logger.error(f'Failed to load data:\n{e}')
        config.refresh()
        app.logger.debug(f'Waiting {config.data_load_interval_min:.1f} minutes to read data again.')
        time.sleep(config.data_load_interval_min*60)


t = Thread(target=_data_grabber, daemon=True, name='_data_grabber')
t.start()


def _get_plot_hrs(endpoint: str) -> int:
    if 'days' in request.args.keys():
        plot_hrs = int(float(request.args['days'])*24)
    elif 'hours' in request.args.keys():
        plot_hrs = int(float(request.args['hours']))
    else:
        plot_hrs = config.plot_hrs[endpoint]
    return plot_hrs


@app.route('/')
@app.route('/log')
def main():
    with TimeIt('`filter`', log=app.logger):
        filtered = filter(_all_data, _get_plot_hrs('log'))
    with TimeIt('`smooth`', log=app.logger):
        smoothed = smooth(filtered)
    return log_plot(smoothed)


def _time_pretty(hrs: int) -> str:
    if hrs < 24:
        return f'{hrs:d} hours'
    else:
        days = hrs/24
        if days == int(days):
            return f'{days:.0f} days'
        else:
            return f'{days:1.f} days'


@app.route('/hourly')
def hourly():
    hrs = _get_plot_hrs('hourly')
    filtered = filter(_all_data, hrs)
    smoothed = smooth(filtered)
    return hourly_plot(smoothed, title=f'Last {_time_pretty(hrs)}')


@app.route('/daily')
def daily():
    hrs = _get_plot_hrs('daily')
    filtered = filter(_all_data, hrs)
    smoothed = smooth(filtered)
    return daily_plot(smoothed, title=f'Last {_time_pretty(hrs)}')


@app.route('/favicon.ico')
def favicon():
    return ''

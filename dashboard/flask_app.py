from typing import Dict
from threading import Thread
import time

from flask import Flask, request
from bokeh.models import ColumnDataSource

import config
from .data import (proc_results,
                   filter,
                   smooth,)
from .plots import (down_up,
                    down_up_by_hour,
                    down_up_by_weekday,)

from utils.timing import TimeIt
app = Flask(__name__)

_all_data: Dict[str, ColumnDataSource] = {}


def _data_grabber():
    global _all_data
    with TimeIt('`proc_results` (in a thread)', single_line=False):
        _all_data = proc_results(span_hrs=None)
    config.refresh()
    time.sleep(config.data_load_interval_min*60)


t = Thread(target=_data_grabber, daemon=True)
t.start()


def _get_plot_hrs() -> int:
    if 'days' in request.args.keys():
        plot_hrs = int(float(request.args['days'])*24)
    elif 'hours' in request.args.keys():
        plot_hrs = int(float(request.args['hours']))
    else:
        plot_hrs = config.plot_hrs
    return plot_hrs


@app.route('/')
@app.route('/log')
def main():
    with TimeIt('`filter`'):
        filtered = filter(_all_data, _get_plot_hrs())
    with TimeIt('`smooth`'):
        smoothed = smooth(filtered)
    return down_up(smoothed)


@app.route('/hourly')
def hourly():
    filtered = filter(_all_data, _get_plot_hrs())
    smoothed = smooth(filtered)
    return down_up_by_hour(smoothed)


@app.route('/daily')
def daily():
    filtered = filter(_all_data, _get_plot_hrs())
    smoothed = smooth(filtered)
    return down_up_by_weekday(smoothed)


@app.route('/favicon.ico')
def favicon():
    return ''

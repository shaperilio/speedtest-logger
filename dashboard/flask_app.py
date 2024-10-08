from flask import Flask

import config

from .plots import proc_results, smooth, down_up, down_up_by_hour, down_up_by_weekday

app = Flask(__name__)


@app.route('/', defaults={'plot_hrs': str(config.plot_hrs)})
@app.route('/<plot_hrs>')
def main(plot_hrs: str):
    sources = proc_results(int(plot_hrs))
    smoothed = smooth(sources)
    return down_up(smoothed)


@app.route('/hourly/', defaults={'plot_hrs': str(config.hourly_plot_days * 24)})
@app.route('/hourly/<plot_hrs>')
def hourly(plot_hrs: str):
    sources = proc_results(int(plot_hrs))
    smoothed = smooth(sources)
    return down_up_by_hour(smoothed)


@app.route('/daily/', defaults={'plot_hrs': str(config.daily_plot_days * 24)})
@app.route('/daily/<plot_hrs>')
def daily(plot_hrs: str):
    sources = proc_results(int(plot_hrs))
    smoothed = smooth(sources)
    return down_up_by_weekday(smoothed)


@app.route('/favicon.ico')
def favicon():
    return ''

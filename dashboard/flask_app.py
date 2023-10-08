from flask import Flask

import config

from .plots import proc_results, smooth, down_up, down_up_by_hour

app = Flask(__name__)


@app.route('/', defaults={'n_records': config.n_records})
@app.route('/<n_records>')
def main(n_records: str):
    sources = proc_results(int(n_records))
    smoothed = smooth(sources)
    return down_up(smoothed)


@app.route('/hourly/', defaults={'n_records': config.n_records*10})
@app.route('/hourly/<n_records>')
def hourly(n_records: str):
    sources = proc_results(int(n_records))
    smoothed = smooth(sources)
    return down_up_by_hour(smoothed)


@app.route('/favicon.ico')
def favicon():
    return ''

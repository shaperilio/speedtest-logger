from flask import Flask

import config

from .plots import proc_results, smooth, down_up

app = Flask(__name__)

@app.route('/', defaults={'n_records': config.n_records})
@app.route('/<n_records>')
def main(n_records: str):
    sources = proc_results(int(n_records))
    smoothed = smooth(sources)
    return down_up(smoothed)


@app.route('/favicon.ico')
def favicon():
    return ''
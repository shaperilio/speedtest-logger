from flask import Flask

import config

from .plots import proc_results, smooth, down_up

app = Flask(__name__)

@app.route('/', defaults={'n_records': config.n_records})
@app.route('/<n_records>')
def main(n_records: int):
    sources = proc_results(n_records)
    smoothed = smooth(sources)
    return down_up(smoothed)

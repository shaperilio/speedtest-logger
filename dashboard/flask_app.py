from flask import Flask

import config

from .plots import proc_results, smooth, down_up

app = Flask(__name__)


@app.route('/')
def main():
    sources = proc_results(config.n_records)
    smoothed = smooth(sources)
    return down_up(smoothed)

from flask import Flask
from .plots import down_up
app = Flask(__name__)


@app.route('/')
def main():
    return down_up()


from typing import List, Dict, Any
import json
import dateutil.parser
from collections import defaultdict

from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource

import config


def plot() -> None:
    filename = 'example_results.json'
    with open(filename, 'r') as f:
        results: List[Dict[str, Any]] = json.loads(f.read())

    speeds: Dict[str, Dict[str, list]] = {}
    for result in results:
        utc = dateutil.parser.isoparse(result['timestamp'])
        # success = bool(result['returnCode'] == 0)
        nickname = result['nickname']
        if nickname not in speeds.keys():
            speeds[nickname] = defaultdict(list)
        speedtest = result['output']
        download_mbps = float(speedtest['download']['bandwidth']) * 8 / 1000 / 1000
        upload_mbps = float(speedtest['upload']['bandwidth']) * 8 / 1000 / 1000
        speeds[nickname]['date'].append(utc.timestamp())
        speeds[nickname]['download'].append(download_mbps)
        speeds[nickname]['upload'].append(upload_mbps)

    p = figure(height=300, width=800, tools="hover", toolbar_location='right',
               x_axis_type="datetime", x_axis_location="below")

    for nickname in speeds.keys():
        source = ColumnDataSource(data={'date': speeds[nickname]['date'],
                                        nickname: speeds[nickname]['download']}
                                  )
        p.line(x='date', y=nickname, source=source)
    p.yaxis.axis_label = 'Download rate (Mbps)'

    show(p)


plot()

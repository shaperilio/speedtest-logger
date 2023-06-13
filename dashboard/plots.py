
from typing import List, Dict, Any
import json
import dateutil.parser
from collections import defaultdict
import itertools

from bokeh.plotting import figure, output_file, save
from bokeh.models import ColumnDataSource, HoverTool, Scatter
from bokeh.palettes import Category10_10 as palette
import config


def line_dot(fig: figure,
             source: ColumnDataSource,
             *,
             y: str,
             legend_label: str,
             color: str,
             dashed: bool,
             ) -> Scatter:
    if dashed:
        line_dash = 'dashed'
    else:
        line_dash = 'solid'
    fig.line(x='date', y=y, source=source,
             line_width=2,
             line_color=color,
             legend_label=legend_label,
             line_dash=line_dash,
             )
    d = fig.circle(x='date', y=y, source=source,
                   size=6,
                   fill_color='white',
                   line_width=2,
                   line_color=color,
                   legend_label=legend_label,
                   )
    return d


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
        speeds[nickname]['nickname'].append(nickname)

    fig = figure(height=500, width=900, toolbar_location=None,
                 x_axis_type='datetime', x_axis_location='below')
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'

    dots: List[Scatter] = []

    color = itertools.cycle(palette)

    for nickname in speeds.keys():
        source = ColumnDataSource(data={'date': speeds[nickname]['date'],
                                        'download': speeds[nickname]['download'],
                                        'upload': speeds[nickname]['upload'],
                                        'nickname': speeds[nickname]['nickname']}
                                  )
        c = next(color)
        dots.extend([
            line_dot(fig, source, y='download',
                     legend_label=nickname, color=c, dashed=False),
            line_dot(fig, source, y='upload',
                     legend_label=nickname, color=c, dashed=True)
        ])

    fig.add_tools(
        HoverTool(
            tooltips=[
                ('Interface', '@nickname'),
                ('Date', '@date'),
                ('Download rate', '@download{0.0} MBps'),
                ('Upload rate', '@upload{0.0} MBps'),
            ],
            formatters={
                '@date': 'datetime'
            },
            mode='mouse',
            renderers=dots,
        ))

    output_file('plots.html')
    save(fig)


plot()

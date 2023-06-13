
from typing import List, Dict, Any
import json
import dateutil.parser
from dateutil import tz
from collections import defaultdict
import itertools

from bokeh.plotting import figure, output_file, save
from bokeh.models import ColumnDataSource, HoverTool, Scatter, OpenURL, TapTool
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
        utc = utc.replace(tzinfo=tz.UTC)
        local = utc.astimezone(tz.tzlocal())
        success = bool(result['returnCode'] == 0)
        if not success:
            continue
        nickname = result['nickname']
        if nickname not in speeds.keys():
            speeds[nickname] = defaultdict(list)
        speedtest = result['output']

        download_mbps = float(speedtest['download']['bandwidth']) * 8 / 1000 / 1000
        upload_mbps = float(speedtest['upload']['bandwidth']) * 8 / 1000 / 1000
        url = speedtest['result']['url']
        speeds[nickname]['date'].append(local)
        speeds[nickname]['download'].append(download_mbps)
        speeds[nickname]['upload'].append(upload_mbps)
        speeds[nickname]['nickname'].append(nickname)
        speeds[nickname]['url'].append(url)

    fig = figure(height=500, width=900, toolbar_location=None,
                 x_axis_type='datetime', x_axis_location='below')
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'

    dots: List[Scatter] = []

    color = itertools.cycle(palette)

    for nickname in speeds.keys():
        source = ColumnDataSource(data={'date': speeds[nickname]['date'],
                                        'download': speeds[nickname]['download'],
                                        'upload': speeds[nickname]['upload'],
                                        'nickname': speeds[nickname]['nickname'],
                                        'url': speeds[nickname]['url'],
                                        }
                                  )
        c = next(color)
        dots.extend([
            line_dot(fig, source, y='download',
                     legend_label=nickname, color=c, dashed=False),
            line_dot(fig, source, y='upload',
                     legend_label=nickname, color=c, dashed=True)
        ])

    hover = HoverTool(
        tooltips=[
            ('Interface', '@nickname'),
            ('Date', '@date{%Y-%m-%d %H:%M:%S}'),
            ('Download rate', '@download{0.0} MBps'),
            ('Upload rate', '@upload{0.0} MBps'),
        ],
        formatters={
            '@date': 'datetime'
        },
        mode='mouse',
        renderers=dots,
    )
    tap = TapTool()
    tap.callback = OpenURL(url='@url')
    fig.add_tools(hover, tap)

    output_file('plots.html')
    save(fig)


plot()


from typing import List, Dict, Any
import json
import dateutil.parser
from dateutil import tz
from collections import defaultdict
import itertools
import logging

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Scatter, OpenURL, TapTool
from bokeh.palettes import Category10_10 as palette
from bokeh.resources import CDN
from bokeh.embed import file_html
import config

_l = logging.getLogger(__name__)


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


def _latency_stats(latency: Dict[str, float]) -> str:
    l = float(latency['low'])
    h = float(latency['high'])
    j = float(latency['jitter'])
    return f'{l:.1f} - {h:.1f} ({j:.1f}) msec'


def _proc_results(n_records: int) -> Dict[str, ColumnDataSource]:
    filename = config.results_db
    # filename = 'example_results.json'
    with open(filename, 'r') as f:
        results: List[Dict[str, Any]] = json.loads(f.read())

    speeds: Dict[str, Dict[str, list]] = {}
    n = 0
    for idx, result in enumerate(reversed(results)):
        utc = dateutil.parser.isoparse(result['timestamp'])
        utc = utc.replace(tzinfo=tz.UTC)
        local = utc.astimezone(tz.tzlocal())
        success = bool(result['returnCode'] == 0)
        nickname = result['nickname']
        if nickname not in speeds.keys():
            speeds[nickname] = defaultdict(list)
        speeds[nickname]['nickname'].append(nickname)
        speeds[nickname]['date'].append(local)

        if success:
            try:
                speedtest = result['output']
                download_mbps = float(speedtest['download']['bandwidth']) * 8 / 1000 / 1000
                upload_mbps = float(speedtest['upload']['bandwidth']) * 8 / 1000 / 1000
                url = speedtest['result']['url']

                speeds[nickname]['download_mbps'].append(download_mbps)
                speeds[nickname]['upload_mbps'].append(upload_mbps)
                speeds[nickname]['url'].append(url)

                lat = _latency_stats(speedtest['ping'])
                speeds[nickname]['idle_latency_stats'].append(lat)
                # It appears sometimes latency results are not in the record...
                if 'latency' in speedtest['download'].keys():
                    lat = _latency_stats(speedtest['download']['latency'])
                    speeds[nickname]['down_latency_stats'].append(lat)
                else:
                    speeds[nickname]['down_latency_stats'].append('NT')

                if 'latency' in speedtest['upload'].keys():
                    lat = _latency_stats(speedtest['upload']['latency'])
                    speeds[nickname]['up_latency_stats'].append(lat)
                else:
                    speeds[nickname]['up_latency_stats'].append('NT')
            except KeyError as ke:
                _l.error(f'`KeyError` while processing record {idx} from the bottom.')
                _l.exception(ke)
        else:
            speeds[nickname]['download_mbps'].append(0)
            speeds[nickname]['upload_mbps'].append(0)
            speeds[nickname]['url'].append('')
            speeds[nickname]['idle_latency_stats'].append('NT')
            speeds[nickname]['down_latency_stats'].append('NT')
            speeds[nickname]['up_latency_stats'].append('NT')
        n += 1
        if n == n_records:
            break

    sources: Dict[str, ColumnDataSource] = {}
    for nickname in speeds.keys():
        data = {'date': speeds[nickname]['date'],
                'download_mbps': speeds[nickname]['download_mbps'],
                'upload_mbps': speeds[nickname]['upload_mbps'],
                'nickname': speeds[nickname]['nickname'],
                'url': speeds[nickname]['url'],
                'idle_latency_stats': speeds[nickname]['idle_latency_stats'],
                'down_latency_stats': speeds[nickname]['down_latency_stats'],
                'up_latency_stats': speeds[nickname]['up_latency_stats'],
                }
        sources[nickname] = ColumnDataSource(data)
    return sources


def down_up() -> str:
    fig = figure(height=500, width=1200, toolbar_location=None,
                 x_axis_type='datetime', x_axis_location='below')
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'

    dots: List[Scatter] = []
    color = itertools.cycle(palette)
    sources = _proc_results(config.n_records)
    for nickname, source in sources.items():
        c = next(color)
        dots.extend([
            line_dot(fig, source, y='download_mbps',
                     legend_label=nickname, color=c, dashed=False),
            line_dot(fig, source, y='upload_mbps',
                     legend_label=nickname, color=c, dashed=True)
        ])

    hover = HoverTool(
        tooltips=[
            ('Interface', '@nickname'),
            ('Date', '@date{%Y-%m-%d %H:%M:%S}'),
            ('Ping min - max (jitter)', '@idle_latency_stats'),
            ('Download rate', '@download_mbps{0.0} MBps'),
            ('Latency min - max (jitter)', '@down_latency_stats'),
            ('Upload rate', '@upload_mbps{0.0} MBps'),
            ('Latency min - max (jitter)', '@up_latency_stats'),

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

    return file_html(fig, CDN, 'Speedtest log')


from typing import List, Dict, Tuple, Any
import json
import dateutil.parser
from dateutil import tz
from collections import defaultdict
import itertools
import logging

import numpy

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
             x: str,
             y: str,
             legend_label: str,
             color: str,
             dashed: bool,
             ) -> Scatter:
    if dashed:
        line_dash = 'dashed'
    else:
        line_dash = 'solid'
    fig.line(x=x, y=y, source=source,
             line_width=2,
             line_color=color,
             legend_label=legend_label,
             line_dash=line_dash,
             )
    d = fig.circle(x=x, y=y, source=source,
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


def proc_results(n_records: int) -> Dict[str, ColumnDataSource]:
    filename = config.results_db
    with open(filename, 'r') as f:
        results: List[Dict[str, Any]] = json.loads(f.read())

    speeds: Dict[str, Dict[str, list]] = {}
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
                if 'url' not in speedtest['result'].keys():
                    url = ''
                else:
                    url = speedtest['result']['url']

                speeds[nickname]['success'].append(True)
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
            speeds[nickname]['success'].append(False)
            speeds[nickname]['download_mbps'].append(0)
            speeds[nickname]['upload_mbps'].append(0)
            speeds[nickname]['url'].append('')
            speeds[nickname]['idle_latency_stats'].append('NT')
            speeds[nickname]['down_latency_stats'].append('NT')
            speeds[nickname]['up_latency_stats'].append('NT')
        if idx+1 == n_records:
            break

    sources: Dict[str, ColumnDataSource] = {}
    for nickname in sorted(speeds.keys()):
        data = {'date': speeds[nickname]['date'],
                'weekday': [d.weekday() for d in speeds[nickname]['date']],
                'hour': [d.hour for d in speeds[nickname]['date']],
                'success': speeds[nickname]['success'],
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


def _time_average(vals: List[float], *, n_avg: int, keep_zero: bool) -> List[float]:
    window = [vals[0]] * n_avg
    averaged: List[float] = []
    for i in range(len(vals)):
        val = vals[i]
        window.append(val)
        window.pop(0)
        if keep_zero and val == 0:
            averaged.append(val)
        else:
            averaged.append(numpy.mean(window))
    return averaged


def smooth(sources: Dict[str, ColumnDataSource]) -> Dict[str, ColumnDataSource]:
    n_avg = config.n_time_avg
    if n_avg < 1:
        raise ValueError(f'`n_time_avg` must be at least 1, got {config.n_time_avg}.')
    if n_avg == 1:
        return sources

    smoothed: Dict[str, ColumnDataSource] = {}
    for source, cds in sources.items():
        data: Dict[str, list] = {}
        for key in cds.data.keys():
            if key in ['download_mbps', 'upload_mbps']:
                data[key] = _time_average(cds.data[key], n_avg=n_avg, keep_zero=True)
            else:
                data[key] = cds.data[key]
        smoothed[source] = ColumnDataSource(data=data)
    return smoothed


def down_up(sources: Dict[str, ColumnDataSource]) -> str:
    fig = figure(height=500, width=1500, toolbar_location=None,
                 x_axis_type='datetime', x_axis_location='below',
                 sizing_mode='stretch_width')
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'

    dots: List[Scatter] = []
    color = itertools.cycle(palette)
    for nickname, source in sources.items():
        c = next(color)
        dots.extend([
            line_dot(fig, source, x='date', y='download_mbps',
                     legend_label=nickname, color=c, dashed=False),
            line_dot(fig, source, x='date', y='upload_mbps',
                     legend_label=nickname, color=c, dashed=True)
        ])

    hover = HoverTool(
        tooltips=[
            ('Interface', '@nickname'),
            ('Date', '@date{%Y-%m-%d %H:%M:%S}'),
            ('Down / up rate', '@download_mbps{0.0} / @upload_mbps{0.0} Mbps'),
            ('Ping min - max (jitter)', '@idle_latency_stats'),
            ('Down latency min - max (jitter)', '@down_latency_stats'),
            ('Up latency min - max (jitter)', '@up_latency_stats'),

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


def down_up_by_val(source: Dict[str, ColumnDataSource],
                   val_name: str) -> Dict[str, ColumnDataSource]:
    by_val_speeds: Dict[str, Dict[str, list]] = {}
    for nickname, source in source.items():
        vals = source.data[val_name]
        dns = source.data['download_mbps']
        ups = source.data['upload_mbps']
        successes = source.data['success']
        by_val_dn_up: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
        fails: Dict[int, int] = defaultdict(lambda: 0)
        for val, dn, up, suc in zip(vals, dns, ups, successes):
            by_val_dn_up[val].append((dn, up))
            if not suc:
                fails[val] += 1
        by_val_dn_up = dict(sorted(by_val_dn_up.items(), key=lambda i: i[0]))

        dn_by_val = [[i[0] for i in by_val_dn_up[k]] for k in by_val_dn_up.keys()]
        up_by_val = [[i[1] for i in by_val_dn_up[k]] for k in by_val_dn_up.keys()]
        mean_dn_by_val = [numpy.mean(d) for d in dn_by_val]
        mean_up_by_val = [numpy.mean(u) for u in up_by_val]
        std_dn_by_val = [numpy.std(d) for d in dn_by_val]
        std_up_by_val = [numpy.std(u) for u in up_by_val]
        n_by_val = [len(d) for d in dn_by_val]
        fails_by_val = [f for f in fails.values()]

        by_val_speeds[nickname] = {}
        by_val_speeds[nickname][val_name] = list(by_val_dn_up.keys())
        by_val_speeds[nickname]['download_mbps_mean'] = mean_dn_by_val
        by_val_speeds[nickname]['upload_mbps_mean'] = mean_up_by_val
        by_val_speeds[nickname]['download_mbps_std'] = std_dn_by_val
        by_val_speeds[nickname]['upload_mbps_std'] = std_up_by_val
        by_val_speeds[nickname]['num_tests'] = n_by_val
        by_val_speeds[nickname]['num_tests_failed'] = fails_by_val

    by_val: Dict[str, ColumnDataSource] = {}
    for nickname in sorted(by_val_speeds.keys()):
        n_points = len(by_val_speeds[nickname][val_name])
        data = {'nickname': [nickname] * n_points,
                val_name: by_val_speeds[nickname][val_name],
                'download_mbps_mean': by_val_speeds[nickname]['download_mbps_mean'],
                'upload_mbps_mean': by_val_speeds[nickname]['upload_mbps_mean'],
                'download_mbps_std': by_val_speeds[nickname]['download_mbps_std'],
                'upload_mbps_std': by_val_speeds[nickname]['upload_mbps_std'],
                'num_tests': by_val_speeds[nickname]['num_tests'],
                'num_tests_failed': by_val_speeds[nickname]['num_tests_failed'],
                }
        by_val[nickname] = ColumnDataSource(data)

    return by_val


def down_up_by_hour(sources: Dict[str, ColumnDataSource]) -> str:
    fig = figure(height=800, width=800, toolbar_location=None, x_axis_location='below')
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'
    fig.xaxis.axis_label = 'Hour of day'
    fig.xaxis.ticker = list(range(24))

    sources = down_up_by_val(sources, 'hour')

    dots: List[Scatter] = []
    color = itertools.cycle(palette)
    for nickname, source in sources.items():
        source.data['hour']
        c = next(color)
        dots.extend([
            line_dot(fig, source, x='hour', y='download_mbps_mean',
                     legend_label=nickname, color=c, dashed=False),
            line_dot(fig, source, x='hour', y='upload_mbps_mean',
                     legend_label=nickname, color=c, dashed=True)
        ])

    hover = HoverTool(
        tooltips=[
            ('Interface', '@nickname'),
            ('Avg down', '@download_mbps_mean{0.0} +/- @download_mbps_std{0.0} Mbps'),
            ('Avg up rate', ' @upload_mbps_mean{0.0} +/- @upload_mbps_std{0.0} Mbps'),
            ('Num tests (total / failed)', ' @num_tests{,} / @num_tests_failed{,}')
        ],
        mode='mouse',
        renderers=dots,
    )
    fig.add_tools(hover)

    return file_html(fig, CDN, 'Speedtest log')


def down_up_by_weekday(sources: Dict[str, ColumnDataSource]) -> str:
    fig = figure(height=800, width=800, toolbar_location=None, x_axis_location='below')
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'
    fig.xaxis.axis_label = 'Weekday'
    ticks = {0: 'Mon',
             1: 'Tue',
             2: 'Wed',
             3: 'Thu',
             4: 'Fri',
             5: 'Sat',
             6: 'Sun'}
    fig.xaxis.ticker = list(ticks.keys())
    fig.xaxis.major_label_overrides = ticks
    sources = down_up_by_val(sources, 'weekday')

    dots: List[Scatter] = []
    color = itertools.cycle(palette)
    for nickname, source in sources.items():
        source.data['weekday']
        c = next(color)
        dots.extend([
            line_dot(fig, source, x='weekday', y='download_mbps_mean',
                     legend_label=nickname, color=c, dashed=False),
            line_dot(fig, source, x='weekday', y='upload_mbps_mean',
                     legend_label=nickname, color=c, dashed=True)
        ])

    hover = HoverTool(
        tooltips=[
            ('Interface', '@nickname'),
            ('Avg down', '@download_mbps_mean{0.0} +/- @download_mbps_std{0.0} Mbps'),
            ('Avg up rate', ' @upload_mbps_mean{0.0} +/- @upload_mbps_std{0.0} Mbps'),
            ('Num tests (total / failed)', ' @num_tests{,} / @num_tests_failed{,}')
        ],
        mode='mouse',
        renderers=dots,
    )
    fig.add_tools(hover)

    return file_html(fig, CDN, 'Speedtest log')

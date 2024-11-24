from typing import List, Sequence, Dict, Tuple, Any, Optional, cast
import json
from collections import defaultdict
import itertools
import logging
from datetime import datetime

import numpy
import dateutil.parser
from dateutil import tz

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Scatter, OpenURL, TapTool
from bokeh.palettes import Category10_10 as palette
from bokeh.resources import CDN
from bokeh.embed import file_html

import config
from utils.timing import TimeIt

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
    d = fig.scatter(x=x, y=y, source=source,
                    size=6,
                    fill_color='white',
                    line_width=2,
                    line_color=color,
                    legend_label=legend_label,
                    )
    return d


def _latency_stats(latency: Dict[str, float]) -> str:
    lo = float(latency['low'])
    hi = float(latency['high'])
    jt = float(latency['jitter'])
    return f'{lo:.1f} - {hi:.1f} ({jt:.1f}) msec'


def proc_results(span_hrs: Optional[int]) -> Dict[str, ColumnDataSource]:
    """Returns a `ColumnDataSource` for each interface, keyed by nickname."""
    config.refresh()
    filename = config.results_db
    with TimeIt('Opening JSON results file', log_name=None):
        with open(filename, 'r') as f:
            results: List[Dict[str, Any]] = json.loads(f.read())
    results = list(reversed(results))
    speeds: Dict[str, Dict[str, list]] = {}
    last_succeeded: Dict[str, bool] = {}  # for keeping track of consecutive failures.
    first_timestamp_sec = None
    for idx in range(len(results)):
        result = results[idx]
        utc = dateutil.parser.isoparse(result['timestamp'])
        if first_timestamp_sec is None:
            first_timestamp_sec = utc.timestamp()
        else:
            if span_hrs is not None and (first_timestamp_sec-utc.timestamp()) / 60 / 60 > span_hrs:
                break  # We've exceed the maximum time span.
        nickname = result['nickname']
        if nickname not in last_succeeded.keys():
            # We need an initial value in case the first result is a failure.
            # If the first result is a failure, we want to show it, so we set this to True
            # regardless of the value of `success`.
            last_succeeded[nickname] = True
        success = bool(result['returnCode'] == 0)
        if config.keep_consecutive_failures is False:  # need to check for consecutive failures.
            # We need to check three things:
            # 1. Did this test fail?
            # 2. Did the previous test succeed? If so, we want to keep this failure.
            # 3. Did the next test succeed? If so, we want to keep this failure.
            # Otherwise, we discard this point, as it's got a failure on both sides.
            if success is False:  # 1
                if last_succeeded[nickname] is False:  # 2: last test also failed; do #3
                    def get_next_success() -> bool:
                        for n in range(idx+1, len(results)):  # 3a: look for next test.
                            next_result = results[n]
                            next_nickname = next_result['nickname']
                            if next_nickname == nickname:
                                # this is the next test
                                next_success = bool(next_result['returnCode'] == 0)
                                return next_success
                        else:
                            # Never found the next test. Abort.
                            return True  # This ensures the current result is included.
                    next_success = get_next_success()
                    if next_success is False:  # 3b: next test is also a failure; skip.
                        continue
        last_succeeded[nickname] = success
        if nickname not in speeds.keys():
            speeds[nickname] = defaultdict(list)
        speeds[nickname]['nickname'].append(nickname)
        utc = utc.replace(tzinfo=tz.UTC)
        local = utc.astimezone(tz.tzlocal())
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

    sources: Dict[str, ColumnDataSource] = {}
    for nickname in sorted(speeds.keys()):
        data = {
            'date': speeds[nickname]['date'],
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


def filter(sources: Dict[str, ColumnDataSource], span_hrs: int) -> Dict[str, ColumnDataSource]:
    """Returns `sources` with data for only the most recent `span_hrs`."""
    now = datetime.now().replace(tzinfo=tz.tzlocal())
    cutoff_by_nickname: Dict[str, int] = {}

    def find_span_idx(dates: List[datetime]) -> int:
        for idx, date in enumerate(dates):
            diff_hours = (now-date).total_seconds() / (60 * 60)
            if diff_hours > span_hrs:
                return idx
        return len(dates) - 1

    for nickname, data in sources.items():
        data_dates: List[datetime] = data.data['date']
        cutoff_by_nickname[nickname] = find_span_idx(data_dates)

    # Now create new `ColumnDataSource`s cut off for the given span.
    filtered: Dict[str, ColumnDataSource] = {}
    for nickname, data in sources.items():
        e = cutoff_by_nickname[nickname]
        if e == 0:
            continue  # don't show this interface
        data = {field: seq[0:e] for field, seq in sources[nickname].data.items()}
        filtered[nickname] = ColumnDataSource(data=data)
    return filtered


def _time_average(vals: Sequence[float], *, n_avg: int, keep_zero: bool) -> List[float]:
    window = [vals[0]] * n_avg
    averaged: List[float] = []
    for i in range(len(vals)):
        val = vals[i]
        window.append(val)
        window.pop(0)
        if keep_zero and val == 0:
            averaged.append(val)
        else:
            averaged.append(float(numpy.mean(window)))
    return averaged


def smooth(sources: Dict[str, ColumnDataSource]) -> Dict[str, ColumnDataSource]:
    config.refresh()
    n_avg = config.n_time_avg
    if n_avg == 1:
        return sources

    smoothed: Dict[str, ColumnDataSource] = {}
    for source, cds in sources.items():
        data: Dict[str, list] = {}
        for key in cds.data.keys():
            if key in ['download_mbps', 'upload_mbps']:
                data[key] = _time_average(cast(Sequence[float], cds.data[key]),
                                          n_avg=n_avg, keep_zero=True)
            else:
                data[key] = cast(list, cds.data[key])
        smoothed[source] = ColumnDataSource(data=data)
    return smoothed


def down_up(sources: Dict[str, ColumnDataSource]) -> str:
    fig = figure(height=500, width=1500, toolbar_location=None,
                 x_axis_type='datetime', x_axis_location='below',
                 sizing_mode='stretch_width', tools=[])
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
    tap.callback = OpenURL(url='@url')  # type: ignore[assignment]
    fig.add_tools(hover, tap)

    return file_html(fig, CDN, 'Speedtest log')


def down_up_by_val(sources: Dict[str, ColumnDataSource],
                   val_name: str) -> Dict[str, ColumnDataSource]:
    by_val_speeds: Dict[str, Dict[str, list]] = {}
    for nickname, source in sources.items():
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
        for k in by_val_dn_up.keys():
            if k not in fails.keys():
                fails[k] = 0
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
    fig = figure(height=800, width=800, toolbar_location=None, x_axis_location='below', tools=[])
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
    fig = figure(height=800, width=800, toolbar_location=None, x_axis_location='below', tools=[])
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

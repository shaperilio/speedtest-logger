from typing import List, Dict
import itertools
import logging

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Scatter, OpenURL, TapTool
from bokeh.palettes import Category10_10 as palette
from bokeh.resources import CDN
from bokeh.embed import file_html

from .data import down_up_by_val


_l = logging.getLogger(__name__)


def _line_dot(fig: figure,
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


def log_plot(sources: Dict[str, ColumnDataSource]) -> str:
    fig = figure(height=500, width=1500, toolbar_location=None,
                 x_axis_type='datetime', x_axis_location='below',
                 sizing_mode='stretch_width', tools=[])
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'

    dots: List[Scatter] = []
    color = itertools.cycle(palette)
    for nickname, source in sources.items():
        c = next(color)
        dots.extend([
            _line_dot(fig, source, x='date', y='download_mbps',
                      legend_label=nickname, color=c, dashed=False),
            _line_dot(fig, source, x='date', y='upload_mbps',
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


def hourly_plot(sources: Dict[str, ColumnDataSource], title: str) -> str:
    fig = figure(height=800, width=800, toolbar_location=None, x_axis_location='below', tools=[],
                 title=title)
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
            _line_dot(fig, source, x='hour', y='download_mbps_mean',
                      legend_label=nickname, color=c, dashed=False),
            _line_dot(fig, source, x='hour', y='upload_mbps_mean',
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


def daily_plot(sources: Dict[str, ColumnDataSource], title: str) -> str:
    fig = figure(height=800, width=800, toolbar_location=None, x_axis_location='below', tools=[],
                 title=title)
    fig.yaxis.axis_label = 'Transfer rate (Mbps)'
    fig.xaxis.axis_label = 'Weekday'
    fig
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
            _line_dot(fig, source, x='weekday', y='download_mbps_mean',
                      legend_label=nickname, color=c, dashed=False),
            _line_dot(fig, source, x='weekday', y='upload_mbps_mean',
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

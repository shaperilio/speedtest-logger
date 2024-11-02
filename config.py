from typing import Tuple, Union

test_interval_min: float = 20
"""How often to run the speed test. Note there's a 10 second resolution."""
assert test_interval_min >= 10/60.0

retry_interval_min: float = 1
"""How soon to re-run the speed test if there's an error. Note there's a 10 second resolution."""
assert retry_interval_min >= 10/60.0

speedtest_path: str = '/usr/bin/speedtest'
"""Path to Ooklah speedtest CLI executable."""

results_db: str = './results/results.json'
"""Path to database results file."""

log_file: Union[bool, str] = './results/run.log'
"""
Log file location. See `log.configure_logging`.
Changes to this only take effect at startup.
"""

server_id: str = '9436'  # Comcast Sacramento, CA
"""
[Optional] Specify a specific Speedtest server by ID.
Comment this out if you don't want it.
"""

interfaces: Tuple[Tuple[str, str], ...] = (
    ('enx8cae4cdd62b9', 'ARC-XCI55AX QuadPro'),
    ('enx8cae4cdd62d6', 'ASK-NCQ1338FA'),
)
"""
[Optional] Tuple of interface definitions to test. The first item in each tuple should be the
interface name (suitable for passing to Speedtest with `-I`); the second is a nickname for use in
displaying results.
Comment this out if you don't want it.
"""

n_attempts: int = 5
"""Number of times to execute `speedtest` while the return code is not 0. Must be at least 1."""
assert n_attempts > 0

plot_hrs = 24
"""
Maximum number of hours of results to to show on the plot by default.
Changes to this only take effect at startup.
"""
assert plot_hrs > 0

hourly_plot_days = 10
"""
Default number of days' worth of data to show in the hourly plot.
Changes to this only take effect at startup.
"""

daily_plot_days = 28
"""
Default number of days' worth of data to show in the daily plot.
Changes to this only take effect at startup.
"""

n_time_avg = 5
"""Number of points to use for time average smoothing of the plot. Must be at least 1."""
assert n_time_avg > 0

keep_consecutive_failures: bool = False
"""
True to show every failed test on the plot, False to show only the first failure and the last
failure before success.
Failed tests get retried every `retry_interval_min` which is often less than `test_interval_min` and
thus it may be useful to not saturate the plot with lots of failures if e.g. an ISP is down for 2
straight days.
"""

resolv_conf_check_interval_sec: int = 5
"""How often to check `resolv.conf` for Speedify DNS servers."""
assert resolv_conf_check_interval_sec > 0

resolv_conf_log_file: Union[bool, str] = './results/resolv_conf.log'
"""
Log file location for `resolv.conf` monitoring. See `log.configure_logging`.
Changes to this only take effect at startup.
"""


def refresh() -> None:
    """Reloads the configuration file and updates the `config` module."""
    import os
    import logging
    import importlib.util
    import sys

    _l = logging.getLogger(__name__)

    filename = __file__
    if not os.path.exists(filename):
        _l.error(f'Cannot find config file at "{filename}".')
        return

    code = open(filename, 'r', encoding='utf-8').read()

    try:
        # Much confusion here as to how to do this. `spec_from_loader` with `loader`
        # set to None seems like nonsense, but that's the way it goes...
        spec = importlib.util.spec_from_loader('config', loader=None, origin=filename)
        if spec is None:
            raise NotImplementedError  # No idea what to do with this
        module = importlib.util.module_from_spec(spec)
        # I want `__name__` and `__file__` to be available. From what I can tell, to
        # put `__file__` in there, you have to make an actual `Loader` instance to
        # override `get_filename`?
        module.__file__ = filename
        # NOTE: `__name__` has already been set by `spec_from_loader`
        exec(code, module.__dict__)
        module.refresh = refresh  # type: ignore[attr-defined]
    except Exception as e:
        _l.error(f'Failed to refresh config: {e}')
        return

    # If we've already been imported, shoehorn in the new version. This will update all references
    # with the current config.
    # NOTE: this is always True. When the importing system imports this file, it's already created a
    # `sys.modules` key for it.
    if __name__ in sys.modules.keys():
        # Remove things no longer in the config module one by one, except for things in `keep`
        # Note: we can't just clear the `__dict__`, because that dictionary, in this case, is also
        # `globals`. So clearing it would "unimport" sys.
        m_dict = sys.modules[__name__].__dict__
        old_attrs = list(m_dict.keys())  # [k for k in list(m_dict.keys()) if k not in keep]
        # Don't delete a few things:
        old_attrs.remove('refresh')  # We'll need this.
        old_attrs.remove('__warningregistry__')  # no idea what this is.
        for k in old_attrs:
            if k not in module.__dict__.keys():
                del m_dict[k]
        sys.modules[__name__].__dict__.update(module.__dict__)


# refresh()

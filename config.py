from typing import Tuple, Union

test_interval_min: float = 20
"""How often to run the speed test. Note there's a 10 second resolution."""

retry_interval_min: float = 1
"""How soon to re-run the speed test if there's an error. Note there's a 10 second resolution."""

speedtest_path: str = '/usr/bin/speedtest'
"""Path to Ooklah speedtest CLI executable."""

results_db: str = './results/results.json'
"""Path to database results file."""

log_file: Union[bool, str] = './results/run.log'
"""Log file location. See `log.configure_logging`."""

server_id = '27781'  # Converse in Code Networks - Fremont, CA (id: 27781)
"""[Optional] Specify a specific Speedtest server by ID."""

interfaces: Tuple[Tuple[str, str]] = (
    ('enx8cae4cdd62b9', 'ARC-XCI55AX'),
    ('enx8cae4cdd62d6', 'ASK-NCQ1338FA'),
    ('connectify0', 'Speedify')
)
"""
[Optional] Tuple of interface definitions to test. The first item in each tuple should be the
interface name (suitable for passing to Speedtest with `-I`); the second is a nickname for use in
displaying results.
"""

n_attempts: int = 5
"""Number of times to execute `speedtest` while the return code is not 0. Must be at least 1."""

n_records = 300
"""Maximum number of records to show on the plot."""

n_time_avg = 5
"""Number of points to use for time average smoothing of the plot. Must be at least 1."""

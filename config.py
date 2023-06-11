from typing import Tuple

test_interval_min = 20
"""How often to run the speed test."""

speedtest_path = '/usr/bin/speedtest'
"""Path to Ooklah speedtest CLI executable."""

results_db = './results/results.json'
"""Path to database results file."""

# server_id = '30989'
# """[Optional] Specify a specific Speedtest server by ID."""

interfaces: Tuple[Tuple[str, str]] = (
    ('eth1', 'ARC-XCI55AX'),
    ('eth2', 'ASK-NCQ1338FA')
)
"""
[Optional] Tuple of interface definitions to test. The first item in each tuple should be the
interface name (suitable for passing to Speedtest with `-I`); the second is a nickname for use in
displaying results.
"""
from typing import List
import logging
import os
import time
import json

import speedtest
import config
import log

log.configure_logging()

_l = logging.getLogger(__name__)

while True:
    results_path = os.path.abspath(config.results_db)
    results: List[dict] = []
    if not os.path.exists(results_path):
        _l.debug(f'Results file "{results_path}" does not exist.')
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
    else:
        _l.debug(f'Loading results from "{results_path}"...')
        with open(results_path, 'r') as f:
            results = json.loads(f.read())

    if hasattr(config, 'interfaces'):
        for name, nickname in config.interfaces:
            _l.info(
                f'Running test on interface "{name}", a.k.a. "{nickname}"...')
            result = speedtest.run_speedtest(interface=name)
            result['interface']['nickname'] = nickname
            results.append(result)
    else:
        _l.info('Running test...')
        result = speedtest.run_speedtest(interface=name)
        results.append(result)
    _l.debug(f'Saving results to "{results_path}".')
    with open(results_path, 'w') as f:
        f.write(json.dumps(results, sort_keys=True, indent=4))

    _l.info(f'Waiting {config.test_interval_min} minutes to test again...')
    time.sleep(config.test_interval_min*60)

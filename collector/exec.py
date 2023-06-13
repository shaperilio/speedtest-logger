from typing import List, Optional, Dict, Any
import logging
import os
import time
import json
from datetime import datetime

import speedtest
import config
from utils import log

if isinstance(config.log_file, str):
    os.makedirs(os.path.dirname(config.log_file), exist_ok=True)

log.configure_logging(log_to_file=config.log_file)

_l = logging.getLogger(__name__)

if config.n_attempts < 1:
    raise ValueError(f'Invalid value `{config.n_attempts=}`; should be at least 1.')


def _isotime() -> str:
    return datetime.utcnow().isoformat()[:-4]+'Z'


def _run(interface: Optional[str], nickname: Optional[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}

    result['timestamp'] = _isotime()
    if interface is None:
        result['interface'] = 'none'
    else:
        result['interface'] = interface

    if interface is not None and nickname is None:
        result['nickname'] = interface
    else:
        result['nickname'] = nickname

    try:
        for a in range(config.n_attempts):
            returncode, output = speedtest.run_speedtest(interface=interface)
            result['returnCode'] = returncode
            if returncode == 0:
                result['output'] = output
                return result

            _l.error(f'[Attempt {a+1} of {config.n_attempts}] '
                     f'`speedtest` exited with status {returncode}.\n{output}')
        raise RuntimeError(f'Failed to run after {config.n_attempts} tries.')
    except Exception as e:
        _l.exception(e)
        result['output'] = {'exception': {'type': type(e).__name__, 'message': str(e)}}
        result['returnCode'] = -1
        return result


_l.debug(f'Starting execution at {_isotime()}.')

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
            _l.info(f'Running test on interface "{name}", a.k.a. "{nickname}"...')
            results.append(_run(name, nickname))
    else:
        _l.info('Running test without specifying interface...')
        results.append(_run(interface=None, nickname=None))
    _l.debug(f'Saving results to "{results_path}".')
    with open(results_path, 'w') as f:
        f.write(json.dumps(results, sort_keys=True, indent=4))

    _l.info(f'Waiting {config.test_interval_min} minutes to test again...')
    time.sleep(config.test_interval_min*60)

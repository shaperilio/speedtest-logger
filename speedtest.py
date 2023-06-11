from typing import List, Optional
import json
import os
import logging
import subprocess

import config

_l = logging.getLogger(__name__)


def run_speedtest(interface: Optional[str]) -> dict:
    s = config.speedtest_path
    _l.debug(f'Speedtest is at "{s}".')

    if not os.path.exists(s):
        raise RuntimeError(f'Path "{config.speedtest_path}" not found.')

    results_path = os.path.abspath(config.results_db)
    _l.debug(f'Results file is at "{results_path}".')
    os.makedirs(os.path.dirname(results_path), exist_ok=True)

    args: List[str] = [s]
    if hasattr(config, 'server_id'):
        args.append(f'--server-id={config.server_id}')

    if interface is not None:
        args.append(f'--interface={interface}')

    args.append('--format=json')
    _l.debug(f'Exectuing "{" ".join(args)}".')

    result_json = subprocess.check_output(args)
    return json.laods(result_json)

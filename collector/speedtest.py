from typing import List, Optional, Dict, Any, Tuple
import json
import os
import logging
import subprocess

import config

_l = logging.getLogger(__name__)

limit_reached = 173
"""Return code for exceeding the maximum number of requests over some period."""


def run_speedtest(interface: Optional[str]) -> Tuple[int, Dict[str, Any]]:
    s = config.speedtest_path
    _l.debug(f'Speedtest is at "{s}".')

    if not os.path.exists(s):
        raise RuntimeError(f'Path "{config.speedtest_path}" not found.')

    args: List[str] = [s]
    if hasattr(config, 'server_id'):
        args.append(f'--server-id={config.server_id}')

    if interface is not None:
        args.append(f'--interface={interface}')

    args.append('--format=json')
    _l.debug(f'Executing "{" ".join(args)}".')

    try:
        result_json = json.loads(subprocess.check_output(args, stderr=subprocess.STDOUT))
        returncode = 0
    except subprocess.CalledProcessError as e:
        result_json = {}
        returncode = e.returncode

    return returncode, result_json

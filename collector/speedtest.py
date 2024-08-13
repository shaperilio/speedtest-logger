from typing import List, Optional, Dict, Any, Tuple, TextIO
import json
import os
import logging
import subprocess

import config

_l = logging.getLogger(__name__)

limit_reached = 173
"""Return code for exceeding the maximum number of requests over some period."""


def _parse_output(f: TextIO) -> Dict[str, Any]:
    """
    Parses the output written to open file `f`, assuming the last line is valid
    JSON content.

    Around 2024-08-12, the output of `speedtest` started including more than
    one independent JSON string, so decoding the thing as a whole raised
    exceptions.
    """
    f.seek(0)
    out = f.read()
    lines = out.split('\n')
    return json.loads(lines[-1])


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
    cmd = ' '.join(args)
    _l.debug(f'Executing "{cmd}".')

    dump_file = (os.path.dirname(os.path.abspath(config.results_db))
                 + f'/last_speedtest_{interface}.out')

    with open(dump_file, 'w') as f:
        f.write(f'> {cmd}\n')
        try:
            result_out = subprocess.check_output(args, stderr=subprocess.STDOUT)
            f.write(result_out.decode())
            result_json = _parse_output(f)
            returncode = 0
        except subprocess.CalledProcessError as e:
            result_json = {}
            returncode = e.returncode

    return returncode, result_json

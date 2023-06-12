from typing import List, Optional, Dict, Any
import json
import os
import logging
import subprocess
from datetime import datetime

import config

_l = logging.getLogger(__name__)


def _isotime() -> str:
    return datetime.utcnow().isoformat()[:-3]+'Z'


def run_speedtest(interface: Optional[str], nickname: Optional[str]) -> Dict[str, Any]:
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

    result: Dict[str, Any] = {}
    try:
        result_json = json.loads(subprocess.check_output(args, stderr=subprocess.STDOUT))
        returncode = 0
    except subprocess.CalledProcessError as e:
        returncode = e.returncode

    if interface is None:
        interface = 'none'
    if interface is not None and nickname is None:
        nickname = interface

    result['timestamp'] = _isotime()
    result['returnCode'] = returncode
    result['interface'] = interface
    result['nickname'] = nickname
    result['output'] = result_json
    return result

from typing import List, Optional, Dict, Any
import logging
import os
import time
import json
from datetime import datetime
import socket

from utils import log
from collector import speedtest
import config


if isinstance(config.log_file, str):
    os.makedirs(os.path.dirname(config.log_file), exist_ok=True)

log.configure_logging(log_to_file=config.log_file)

_l = logging.getLogger(__name__)


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
            if returncode == speedtest.limit_reached:
                # We're being throttled for trying too often.
                result['output'] = {'error': {'type': 'speedtest',
                                              'message': 'Too many requests received.'}}
                _l.error(f'[Attempt {a+1} of {config.n_attempts}] '
                         f'`speedtest` exited with status {returncode}: too many requests.')
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

waits_min: Dict[str, float] = {}
"""How long to wait to retest each interface."""
last_test: Dict[str, float] = {}
"""Last time each interface was tested."""


def _is_time_to_test(interface: str) -> bool:
    # Note default values guarantee a return value of True
    delta_sec = time.time() - last_test.get(interface, 0)
    if delta_sec >= waits_min.get(interface, 0) * 60:
        return True
    else:
        return False


def _set_wait_time(interface: str, result: dict) -> float:
    if result['returnCode'] == 0 or result['returnCode'] == speedtest.limit_reached:
        waits_min[interface] = config.test_interval_min
    else:
        waits_min[interface] = config.retry_interval_min
    return waits_min[interface]


def _load_results_from_disk(results_path: str) -> List[dict]:
    if not os.path.exists(results_path):
        _l.debug(f'Results file "{results_path}" does not exist.')
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        return []
    else:
        _l.debug(f'Loading results from "{results_path}"...')
        with open(results_path, 'r') as f:
            return json.loads(f.read())


def _save_results_to_disk(results_path: str, results: List[dict]) -> None:
    temp_results_path = results_path+'.tmp'
    _l.debug(f'Saving results to "{temp_results_path}".')
    with open(temp_results_path, 'w') as f:
        f.write(json.dumps(results, sort_keys=True, indent=4))
    _l.debug(f'Transferring results to "{results_path}".')
    os.replace(temp_results_path, results_path)


def _append_result(result: dict) -> None:
    results_path = os.path.abspath(config.results_db)
    results = _load_results_from_disk(results_path)
    results.append(result)
    _save_results_to_disk(results_path, results)


def _record(interface: Optional[str], nickname: Optional[str]) -> None:
    if interface is None:
        name = 'all'
        _l.info('Running test without specifying interface...')
    else:
        name = interface
        _l.info(f'Running test on interface "{name}", a.k.a. "{nickname}"...')

    if not _is_time_to_test(name):
        return

    result = _run(interface, nickname)
    _append_result(result)
    interval_min = _set_wait_time(name, result)
    _l.info(f'Will test again on interface "{name}", a.k.a. "{nickname}" '
            f'in {interval_min} minutes...')
    last_test[name] = time.time()


def _interface_exists(interface: str, nickname: str) -> bool:
    iface_names = [i[1] for i in socket.if_nameindex()]
    if interface not in iface_names:
        waits_min[interface] = config.test_interval_min
        last_test[interface] = time.time()
        avail = ', '.join([f'"{i}"' for i in iface_names])
        _l.error(f'Interface "{interface}", a.k.a. "{nickname}" is not in the system. '
                 f'Available interfaces: {avail}. '
                 f'Will try again in {waits_min[interface]} minutes...')
        return False
    return True


while True:
    config.refresh()

    if hasattr(config, 'interfaces'):
        for name, nickname in config.interfaces:
            if not _interface_exists(name, nickname):
                continue
            _record(interface=name, nickname=nickname)
    else:
        _record(interface=None, nickname=None)

    time.sleep(10)

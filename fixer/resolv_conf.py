from typing import Optional
import logging
import os
import time

from utils import log
import config


if isinstance(config.resolv_conf_log_file, str):
    os.makedirs(os.path.dirname(config.resolv_conf_log_file), exist_ok=True)

log.configure_logging(log_to_file=config.resolv_conf_log_file)

_l = logging.getLogger(__name__)

filename = '/etc/resolv.conf'


def get_speedify_dns(line: str) -> Optional[str]:
    speedify_dns = ['2600:1010:a101:21c3:ca99:b2ff:feb7:a64',
                    '10.202.0.1']
    for dns in speedify_dns:
        if dns in line:
            return dns


_l.info('Started monitoring `resolf.conf`...')
while True:
    config.refresh()
    try:
        with open(filename, 'r') as f:
            resolv_conf = f.read()
        cleaned_resolv = ''
        for line in resolv_conf.splitlines(keepends=True):
            if line.startswith('#'):
                cleaned_resolv += line
                continue
            if (dns := get_speedify_dns(line)) is not None:
                cleaned_resolv += f'# {line}'
                _l.info(f'Removing "{dns}" from `resolf.conf`.')
                continue
            cleaned_resolv += line
        if cleaned_resolv != resolv_conf:
            with open(filename, 'w') as f:
                f.write(cleaned_resolv)
    except Exception as e:
        _l.error(f'Exception while cleaning `resolv.conf`: {e}')
    finally:
        time.sleep(config.resolv_conf_check_interval_sec)

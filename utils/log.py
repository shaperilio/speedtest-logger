# Modified from this Gist:
# https://gist.github.com/mbrengel/c823baa45ed21dce86e8b8321c804bcf

# From the entry point of your program, simply do
#   import log
#   log.configure_logging()
#
# You can filter out noisy modules:
#   import log
#   log.configure_logging(level=log.DEBUG,
#                         except_modules=['PIL', 'matplotlib'])
#
# and then from any other file, follow the convention to do something like:
#   import logging
#   _l = logging.getLogger(__name__)
#  ...
#   _l.warning("Warning!")

from typing import Union, List, Optional
import time
from datetime import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
import sys

import colorama


# Replicate log levels from logging so that you don't have to import logging
# when setting them on your entry point.
CRITICAL = logging.CRITICAL
FATAL = logging.FATAL
ERROR = logging.ERROR
WARNING = logging.WARNING
WARN = logging.WARN
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET


# We store some instances here so that we can clean up after ourselves, if
# desired.
_handlers: List[logging.Handler] = []  # list of handlers we've installed.


class NoLogFilter():
    """
    Creates a filter object to ignore log messages from a particular module. Any
    children of the module will also be ignored.

    Attributes
    ----------
    name: string
        Name of the module whose messages we don't want to see.
    """

    def __init__(self, name):
        self._name = name

    def filter(self, record):
        if record.name.startswith(self._name):
            return False
        return True


_default_except_modules: List[str] = ['PIL', 'matplotlib', 'parso', 'asyncio', 'MARKDOWN']


def configure_logging(log_to_file: Union[bool, str] = False,
                      root_name: Optional[str] = None,
                      level: int = logging.DEBUG,
                      except_modules: Optional[List[str]] = None):
    """
    Configure logging output. Logging messages are shown on screen, color-coded by level, and,
    optionally, saved to a file.

    `configure_logging` can be called multiple times without causing duplicate output on-screen.
    Subsequent calls can add new file handlers (i.e. log files), such that code like this is
    possible:

    >>> configure_logging(log_to_file=f'program.log')
    >>> def do_work(dat: int): dat
    >>> for i in range(10):
    ...     configure_logging(log_to_file=f'log_{i}.log')
    ...     do_work(i)
    ...     close_log_file(f'log_{i}.log')  # removes handler that outputs to log_{i}.log
    >>> close_log_file('program.log')  # removes handler that outputs to program.log

    Which will have all log messages in program.log and only the messages produced by each iteration
    of `do_work` in log_{i}.log. The on-screen log will match the contents of program.log

    It will also ensure that two file handlers will not be created for the same file.

    Parameters
    ----------
    log_to_file: Union[bool, str] = False
        If True, the log filename will be "./log_<milliseconds since epoch>.log". Rotation is set at
        100 MiB with a maximum of 5 backups. If a string is passed, then that string is the log
        filename. Defaults to False, which means no logging to file.

    root_name: Optional[str] = None
        Name of the logger to configure. The concept of parent/child in logging is usually set by
        module path; i.e. this assumes that you use the convention of creating loggers in your files
        as `logging.getLogger(__name__)`. Thus, passing in "decipher" for this argument will only
        log from `decipher` and its submodules, such as `decipher.patch_tracker.ChainSet`. Defaults
        to None, which means you're configuring the root logger (and thus will see log messages from
        everything, e.g. `matplotlib`).

    level: int = logging.DEBUG
        The minimum log level you want to see on-screen. File level is always `logging.DEBUG`.
        Defaults to logging.DEBUG.

    except_modules: Optional[List[str]] = None
        A list of full  module paths to omit from on-screen display (everything is logged to file).
        "image" will omit all messages from a module called `image` and its children, but not
        messages from, e.g., `decipher.image`. Defaults to `_default_except_modules`.
    """
    if except_modules is None:
        except_modules = _default_except_modules

    # enable cross-platform colored output
    colorama.init()

    # get the root logger and set the level
    logger = logging.getLogger(root_name)
    logger.setLevel(logging.DEBUG)

    # use colored output and use different colors for different levels
    class ColorFormatter(logging.Formatter):
        def __init__(self, colorfmt, *args, **kwargs):
            self._colorfmt = colorfmt
            super(ColorFormatter, self).__init__(*args, **kwargs)

        def format(self, record):
            if record.levelno == logging.INFO:
                color = colorama.Fore.GREEN
            elif record.levelno == logging.WARNING:
                color = colorama.Fore.YELLOW
            elif record.levelno == logging.ERROR:
                color = colorama.Fore.RED
            elif record.levelno == logging.DEBUG:
                color = colorama.Fore.CYAN
            else:
                color = ""
            self._style._fmt = self._colorfmt.format(color, colorama.Style.RESET_ALL)
            return logging.Formatter.format(self, record)

        def formatTime(self, record, datefmt=None):
            created = datetime.fromtimestamp(record.created)
            return datetime.strftime(created, '%Y-%m-%d %H:%M:%S.%f')[:-3]

    class FileFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            created = datetime.fromtimestamp(record.created)
            return datetime.strftime(created, '%Y-%m-%d %H:%M:%S.%f')[:-3]

    # configure stdout handler and pipe everything there.
    # First, check if we already have an stdout handler.
    for handler in _handlers:
        if not isinstance(handler, logging.StreamHandler):
            continue
        # In Linux, the stream is sys.stdout; in windows, it's this mess from
        # colorama.
        if handler.stream is sys.stdout or isinstance(handler.stream,
                                                      colorama.ansitowin32.StreamWrapper):
            stdouthandler = handler
            break  # we already have a handler pumping out to screen.
    else:
        # No handler was found for stdout, so create one.
        stdouthandler = logging.StreamHandler(sys.stdout)
        # The empty `{}` are the entry and exit points for color; you need exactly two.
        fmt = "{}[%(asctime)s|%(name)20s]{} %(message)s"
        stdouthandler.setFormatter(ColorFormatter(fmt))
        stdouthandler.setLevel(level)
        logger.addHandler(stdouthandler)
        _handlers.append(stdouthandler)

    if log_to_file is not False:
        if log_to_file is True:
            # User wants an automatically named log file.
            log_file = f'log_{time.time() * 1000:0.0f}.log'
        else:
            # User has provided a filename.
            log_file = log_to_file
        log_file = os.path.abspath(log_file)
        # Ensure no file handler already exists with this filename.
        for handler in _handlers:
            if isinstance(handler, RotatingFileHandler):
                if os.path.abspath(handler.baseFilename) == os.path.abspath(log_file):
                    break
        else:
            # This is a unique filename. Add the handler.
            filehandler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 10, backupCount=5)
            filehandler.setLevel(logging.DEBUG)
            # configure file handler (no colored messages here)
            fmt = "[%(levelname)+8s|%(asctime)s|%(name)20s] %(message)s"
            filehandler.setFormatter(FileFormatter(fmt))

            logger.addHandler(filehandler)
            _handlers.append(filehandler)

    # Install filters.
    for m in except_modules:
        stdouthandler.addFilter(NoLogFilter(m))

    return logger


def close_log_file(logger_name: str):
    """
    Removes the most recent file handler for the logger. Will not complain if
    there are no file handlers.

    Args:
        logger_name (str): Name of the logger for which to remove the handler.
        Pass None to remove it from the root logger.
    """
    for handler in reversed(_handlers):
        if isinstance(handler, RotatingFileHandler):
            _handlers.remove(handler)
            logging.getLogger(logger_name).removeHandler(handler)
            return


def main(argv):
    # a demo
    configure_logging(log_to_file='test.log')
    logging.debug("This is a debug message")
    logging.info("This is an info message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

from typing import Optional, Union, Callable
import time
import logging
from logging import Logger


class TimeIt:
    def __init__(self, msg: str,
                 single_line: bool = True,
                 log: Optional[Union[str, Logger]] = None) -> None:
        """
        Simple class for timing, use as a context.

        Parameters
        ----------
        msg : str
            The message to show, i.e. what task you're timing.

        single_line : bool = True
            True to show output in a single line, False if you expect your task
            to also put things on the screen.

        log: Optional[Union[str, Logger]]
            If None, output using `print`, otherwise, log to the log with this
            name (if string) or the given `Logger` instance at DEBUG level.
            Note that if logging is used, `single_line` will be set to `False`.
        """
        self._msg = msg
        self._prn: Callable[[str, str, bool], None]  # (msg: str, end: str, flush: bool)
        if log is not None:
            if isinstance(log, Logger):
                l = log
            else:
                l = logging.getLogger(log)
            single_line = False
            self._prn = lambda msg, end, flush: l.debug(msg)
        else:
            self._prn = lambda msg, end, flush: print(msg, end=end, flush=flush)
        if single_line:
            task = self._msg[0].upper() + self._msg[1:]
            self._start_msg = lambda: self._prn(f'{task}...',
                                                end='', flush=True)
            self._end_msg = lambda sec: self._prn(f'done in {sec:,.3f} seconds.',
                                                  end='\n', flush=True)
        else:
            task = self._msg[0].lower() + self._msg[1:]
            self._start_msg = lambda: self._prn(f'Starting {task}...',
                                                end='\n', flush=True)
            self._end_msg = lambda sec: self._prn(f'Done with {task} in {sec:,.3f} seconds.',
                                                  end='\n', flush=True)

    def __enter__(self) -> None:
        self._start_msg()
        self.t0 = time.perf_counter()

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        elapsed = time.perf_counter() - self.t0
        self._end_msg(elapsed)

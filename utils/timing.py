from typing import Optional
import time
import logging


class TimeIt:
    def __init__(self, msg: str,
                 single_line: bool = True,
                 log_name: Optional[str] = None) -> None:
        """
        Simple class for timing, use as a context.

        Parameters
        ----------
        msg : str
            The message to show, i.e. what task you're timing.

        single_line : bool = True
            True to show output in a single line, False if you expect your task to also put things
            on the screen.

        log_name: Optional[str] = None
            If None, output using `print`, otherwise, log to the log with this name at DEBUG level.
        """
        self._msg = msg
        if log_name is not None:
            l = logging.getLogger(log_name)
            self._prn = l.debug
        else:
            self._prn = print
        if single_line:
            task = self._msg[0].upper() + self._msg[1:]
            self._start_msg = lambda: self._prn(f'{task}...', end='', flush=True)
            self._end_msg = lambda sec: self._prn(f'done in {sec:,.3f} seconds.')
        else:
            task = self._msg[0].lower() + self._msg[1:]
            self._start_msg = lambda: self._prn(f'Starting {task}...')
            self._end_msg = lambda sec: self._prn(f'Done with {task} in {sec:,.3f} seconds.')

    def __enter__(self) -> None:
        self._start_msg()
        self.t0 = time.perf_counter()

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        elapsed = time.perf_counter() - self.t0
        self._end_msg(elapsed)

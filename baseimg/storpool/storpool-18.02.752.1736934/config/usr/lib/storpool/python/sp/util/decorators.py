"""Provides different function decorators."""

import errno
import functools
import os
import signal


def static_vars(**kwargs):
    """Adds static variables to the function and initialize them with the given values."""
    def _decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func

    return _decorate


class TimeoutError(Exception):
    pass


def timeout(seconds, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            _sig_info = (signum, frame)
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return functools.wraps(func)(wrapper)

    return decorator

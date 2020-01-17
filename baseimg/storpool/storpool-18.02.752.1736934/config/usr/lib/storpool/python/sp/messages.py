"""Message stylizing functions with a global verbose level."""

from __future__ import print_function

import sys


class MessagesConfig(object):
    # pylint: disable=too-few-public-methods
    '''Verbose level configuration.'''

    def __init__(self):
        pass

    verbose_level = 0


def set_verbose_level(v_lvl):
    '''Change the verbose level to the specified one.'''
    MessagesConfig.verbose_level = v_lvl


def exit_msg(message, status=1):
    '''
    Print a stylized error message and exit with the specified status
    (default is 1).
    '''
    err_msg(message)
    sys.exit(status)


def err_msg(message):
    '''Print a stylized error message.'''
    print("E: {err}".format(err=message), file=sys.stderr)


def warn_msg(message):
    '''Print a stylized warning message.'''
    print("W: {warn}".format(warn=message), file=sys.stderr)


def msg(message, verbose=1):
    '''
    Print a stylized message with the specified verbose level (default is 1).
    The message will only be displayed if its verbose level is equal or
    less than the configured verbose level.
    '''
    if MessagesConfig.verbose_level >= verbose:
        print("M: {msg}".format(msg=message))

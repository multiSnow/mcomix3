# -*- coding: utf-8 -*-

""" Logging module for MComix. Provides a logger 'mcomix' with a few
pre-configured settings. Functions in this module are redirected to
this default logger. """

import threading
import logging
from logging import DEBUG, INFO, WARNING, ERROR

from mcomix import tools
from mcomix import preferences

__all__ = ['debug', 'info', 'warning', 'error', 'setLevel',
           'DEBUG', 'INFO', 'WARNING', 'ERROR']

class PrintHandler(logging.Handler):
    """ Handler using L{tools.print_} to output messages. """

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        tools.print_(self.format(record))

# Set up default logger.
__logger = logging.getLogger('mcomix')
if not __logger.handlers:
    __handler = PrintHandler()
    __handler.setFormatter(logging.Formatter(
        '%(asctime)s: %(levelname)s: %(message)s',
        '%H:%M:%S'))
    __logger.handlers = [ __handler ]
    __logger.setLevel(preferences.prefs['log level'])

# The following functions direct all input to __logger.

debug = __logger.debug
info = __logger.info
warning = __logger.warning
error = __logger.error
setLevel = __logger.setLevel


# vim: expandtab:sw=4:ts=4

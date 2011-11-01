# -*- coding: utf-8 -*-

""" Logging module for MComix. Provides a logger 'mcomix' with a few
pre-configured settings. Functions in this module are redirected to
this default logger. """

import logging
import sys
import locale
from logging import DEBUG, INFO, WARNING, ERROR

from mcomix import i18n

__all__ = ['debug', 'info', 'warning', 'error', 'setLevel',
           'DEBUG', 'INFO', 'WARNING', 'ERROR']

def print_(*args, **options):
    """ This function is supposed to replace the standard print statement.
    Its prototype follows that of the print() function introduced in Python 2.6:
    Prints <args>, with each argument separeted by sep=' ' and ending with
    end='\n'.

    It converts any text to the encoding used by STDOUT, and replaces problematic
    characters with underscore. Prevents UnicodeEncodeErrors and similar when
    using print on non-ASCII strings, on systems not using UTF-8 as default encoding.
    """

    args = [ i18n.to_unicode(val) for val in args ]

    if 'sep' in options: sep = options['sep']
    else: sep = u' '
    if 'end' in options: end = options['end']
    else: end = u'\n'

    def print_generic(text):
        if text:
            if sys.stdout and sys.stdout.encoding:
                encoding = sys.stdout.encoding
            else:
                encoding = locale.getpreferredencoding() or sys.getfilesystemencoding()

            sys.stdout.write(text.encode(encoding, 'replace'))

    def print_win32(text):
        if not text: return

        import ctypes
        INVALID_HANDLE_VALUE, STD_OUTPUT_HANDLE = -1, -11
        outhandle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if outhandle != INVALID_HANDLE_VALUE and outhandle:
            chars_written = ctypes.c_int(0)
            ctypes.windll.kernel32.WriteConsoleW(outhandle,
                text, len(text), ctypes.byref(chars_written), None)
        else:
            print_generic(text)

    print_function = sys.platform == 'win32' and print_win32 or print_generic
    if len(args) > 0:
        print_function(args[0])

    for text in args[1:]:
        print_function(sep)
        print_function(text)

    print_function(end)

class PrintHandler(logging.Handler):
    """ Handler using L{print_} to output messages. """

    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        print_(self.format(record))

# Set up default logger.
__logger = logging.getLogger('mcomix')
if not __logger.handlers:
    __handler = PrintHandler()
    __handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s',
        '%H:%M:%S'))
    __logger.handlers = [ __handler ]

# The following functions direct all input to __logger.

debug = __logger.debug
info = __logger.info
warning = __logger.warning
error = __logger.error
setLevel = __logger.setLevel


# vim: expandtab:sw=4:ts=4

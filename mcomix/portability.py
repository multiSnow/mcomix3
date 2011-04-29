"""Portability functions for MComix."""

import os
import sys
import locale
import ctypes

def uri_prefix():
    """ The prefix used for creating file URIs. This is 'file://' on
    Linux, but 'file:' on Windows due to urllib using a different
    URI creating scheme here. """
    if sys.platform == 'win32':
        return 'file:'
    else:
        return 'file://'

def normalize_uri(uri):
    """ Normalize URIs passed into the program by different applications,
    normally via drag-and-drop. """

    if uri.startswith('file://localhost/'):  # Correctly formatted.
        return uri[16:]
    elif uri.startswith('file:///'):  # Nautilus etc.
        return uri[7:]
    elif uri.startswith('file:/'):  # Xffm etc.
        return uri[5:]
    else:
        return uri

def get_commandline_args():
    """ Simply returns sys.argv, converted to Unicode objects on UNIX.
    Does a bit more work on win32 since Python 2.x' handling of
    command line strings is broken. It only passes ASCII characters
    while replacing all chars that cannot be converted with the current
    encoding to "?".
    So we'll just bypass Python and get an unicode argument vector from
    native win32 library functions."""

    if sys.platform == 'win32':
        # Set up function prototypes
        ctypes.windll.kernel32.GetCommandLineW.restype = ctypes.c_wchar_p
        ctypes.windll.shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        args_length = ctypes.c_int(0)
        # Convert argument string from GetCommandLineW to array
        args_pointer = ctypes.windll.shell32.CommandLineToArgvW(
            ctypes.windll.kernel32.GetCommandLineW(),
            ctypes.byref(args_length))

        if args_pointer:
            args = [args_pointer[i] for i in range(args_length.value)]
            ctypes.windll.kernel32.LocalFree(args_pointer)
            # The first argument is the python interpreter, skip it.
            return args[1:]
        else:
            # For some reason CommandLineToArgvW failed and returned NULL
            # Fall back to sys.argv
            return [arg.decode(locale.getpreferredencoding(), 'replace') for arg in sys.argv]
    else:
        return [arg.decode(locale.getpreferredencoding(), 'replace') for arg in sys.argv]

def invalid_filesystem_chars():
    """ List of characters that cannot be used in filenames on the target platform. """
    if sys.platform == 'win32':
        return ur':*?"<>|' + u"".join([unichr(i) for i in range(0, 32)])
    else:
        return u''

def get_default_locale():
    """ Gets the user's default locale. """
    if sys.platform == 'win32':
        LOCALE_USER_DEFAULT = 0x0400
        LOCALE_SISO639LANGNAME = 0x0059
        LOCALE_SISO3166CTRYNAME = 0x005a

        buffer = ctypes.create_unicode_buffer(9)
        success = ctypes.windll.kernel32.GetLocaleInfoW(LOCALE_USER_DEFAULT, LOCALE_SISO639LANGNAME, buffer, 9)
        if not success: return u"C"
        lang = unicode(buffer.value)
        success = ctypes.windll.kernel32.GetLocaleInfoW(LOCALE_USER_DEFAULT, LOCALE_SISO3166CTRYNAME, buffer, 9)
        if not success: return u"C"
        country = unicode(buffer.value)

        return u"%s_%s" % (lang, country)
    else:
        lang, _ = locale.getdefaultlocale(['LANGUAGE', 'LC_ALL', 'LC_CTYPE', 'LANG'])
        if lang:
            return unicode(lang)
        else:
            return u"C"

# vim: expandtab:sw=4:ts=4

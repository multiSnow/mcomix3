"""Portability functions for MComix."""

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
            # The first argument is either the python interpreter, or MComix.exe
            # in case of being called as py2exe wrapper. If called by Python, the
            # second argument will be a Python script, which needs to be removed.
            if hasattr(sys, 'frozen'):
                return args[1:]
            else:
                return args[2:]
        else:
            # For some reason CommandLineToArgvW failed and returned NULL
            # Fall back to sys.argv
            return [arg.decode(locale.getpreferredencoding(), 'replace') for arg in sys.argv[1:]]
    else:
        return [arg for arg in sys.argv[1:]]

def invalid_filesystem_chars():
    """ List of characters that cannot be used in filenames on the target platform. """
    if sys.platform == 'win32':
        return u':*?"<>|' + u"".join([unichr(i) for i in range(0, 32)])
    else:
        return u''

def get_default_locale():
    """ Gets the user's default locale. """
    if sys.platform == 'win32':
        windll = ctypes.windll.kernel32
        code = windll.GetUserDefaultUILanguage()
        return locale.windows_locale[code]
    else:
        lang, _ = locale.getdefaultlocale(['LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'])
        if lang:
            return lang
        else:
            return u"C"

# vim: expandtab:sw=4:ts=4

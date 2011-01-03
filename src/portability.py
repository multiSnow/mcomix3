"""Portability functions for MComix."""

import os
import sys
import locale
import ctypes

def get_home_directory():
    """On UNIX-like systems, this method will return the path of the home
    directory, e.g. /home/username. On Windows, it will return a MComix
    sub-directory of <Documents and Settings/Username>.
    """
    if sys.platform == 'win32':
        return os.path.join(os.path.expanduser('~'), 'MComix')
    else:
        return os.path.expanduser('~')


def get_config_directory():
    """Return the path to the MComix config directory. On UNIX, this will
    be $XDG_CONFIG_HOME/mcomix, on Windows it will be the same directory as
    get_home_directory().

    See http://standards.freedesktop.org/basedir-spec/latest/ for more
    information on the $XDG_CONFIG_HOME environmental variable.
    """
    if sys.platform == 'win32':
        return get_home_directory()
    else:
        base_path = os.getenv('XDG_CONFIG_HOME',
            os.path.join(get_home_directory(), '.config'))
        return os.path.join(base_path, 'mcomix')


def get_data_directory():
    """Return the path to the MComix data directory. On UNIX, this will
    be $XDG_DATA_HOME/mcomix, on Windows it will be the same directory as
    get_home_directory().

    See http://standards.freedesktop.org/basedir-spec/latest/ for more
    information on the $XDG_DATA_HOME environmental variable.
    """
    if sys.platform == 'win32':
        return get_home_directory()
    else:
        base_path = os.getenv('XDG_DATA_HOME',
            os.path.join(get_home_directory(), '.local/share'))
        return os.path.join(base_path, 'mcomix')

def uri_prefix():
    """ The prefix used for creating file URIs. This is 'file://' on
    Linux, but 'file:' on Windows due to urllib using a different
    URI creating scheme here. """
    if sys.platform == 'win32':
        return 'file:'
    else:
        return 'file://'

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

# vim: expandtab:sw=4:ts=4

"""tools.py - Contains various helper functions."""

import os
import sys
import re
import encoding

def alphanumeric_sort(filenames):
    """Do an in-place alphanumeric sort of the strings in <filenames>,
    such that for an example "1.jpg", "2.jpg", "10.jpg" is a sorted
    ordering.
    """
    def _format_substring(s):
        if s.isdigit():
            return int(s)

        return s.lower()

    rec = re.compile("\d+|\D+")
    filenames.sort(key=lambda s: map(_format_substring, rec.findall(s)))

def get_home_directory():
    """On UNIX-like systems, this method will return the path of the home
    directory, e.g. /home/username. On Windows, it will return an MComix
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

def number_of_digits( n ):

    num_of_digits = 1

    while n > 9:
        n /= 10
        num_of_digits += 1

    return num_of_digits

def print_(*args, **options):
    """ This function is supposed to replace the standard print statement.
    Its prototype follows that of the print() function introduced in Python 2.6:
    Prints <args>, with each argument separeted by sep=' ' and ending with
    end='\n'.

    It converts any text to the encoding used by STDOUT, and replaces problematic
    characters with underscore. Prevents UnicodeEncodeErrors and similar when
    using print on non-ASCII strings, on systems not using UTF-8 as default encoding.
    """

    args = [ encoding.to_unicode(val) for val in args ]

    if 'sep' in options: sep = options['sep']
    else: sep = u' '
    if 'end' in options: end = options['end']
    else: end = u'\n'

    def print_generic(text):
        if text:
            sys.stdout.write(text.encode(sys.stdout.encoding, 'replace'))

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

# vim: expandtab:sw=4:ts=4

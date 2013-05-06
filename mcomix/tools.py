"""tools.py - Contains various helper functions."""

import os
import sys
import re
import gc
import bisect


NUMERIC_REGEXP = re.compile(r"\d+|\D+")  # Split into numerics and characters


def alphanumeric_sort(filenames):
    """Do an in-place alphanumeric sort of the strings in <filenames>,
    such that for an example "1.jpg", "2.jpg", "10.jpg" is a sorted
    ordering.
    """
    def _format_substring(s):
        if s.isdigit():
            return int(s)

        return s.lower()

    filenames.sort(key=lambda s: map(_format_substring, NUMERIC_REGEXP.findall(s)))

def alphanumeric_compare(s1, s2):
    """ Compares two strings by their natural order (i.e. 1 before 10)
    and returns a result comparable to the cmp function.
    @return: 0 if identical, -1 if s1 < s2, +1 if s1 > s2. """
    if s1 is None:
        return 1
    elif s2 is None:
        return -1

    stringparts1 = NUMERIC_REGEXP.findall(s1.lower())
    stringparts2 = NUMERIC_REGEXP.findall(s2.lower())
    for i, part in enumerate(stringparts1):
        if part.isdigit():
            stringparts1[i] = int(part)
    for i, part in enumerate(stringparts2):
        if part.isdigit():
            stringparts2[i] = int(part)

    return cmp(stringparts1, stringparts2)

def bin_search(lst, value):
    """ Binary search for sorted list C{lst}, looking for C{value}.
    @return: List index on success, -1 on failure. """

    index = bisect.bisect_left(lst, value)
    if index != len(lst) and lst[index] == value:
        return index
    else:
        return -1


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


def number_of_digits(n):
    num_of_digits = 1

    while n > 9:
        n /= 10
        num_of_digits += 1

    return num_of_digits


def garbage_collect():
    """ Runs the garbage collector. """
    if sys.version_info[:3] >= (2, 5, 0):
        gc.collect(0)
    else:
        gc.collect()

# vim: expandtab:sw=4:ts=4

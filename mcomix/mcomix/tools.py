"""tools.py - Contains various helper functions."""

import os
import sys
import re
import gc
import bisect
import operator
import math
import io
from functools import reduce


NUMERIC_REGEXP = re.compile(r"\d+|\D+")  # Split into numerics and characters
PREFIXED_BYTE_UNITS = ('B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB')

def cmp(x,y):
    if x>y:return 1
    if x<y:return -1
    return 0

def alphanumeric_sort(filenames):
    """Do an in-place alphanumeric sort of the strings in <filenames>,
    such that for an example "1.jpg", "2.jpg", "10.jpg" is a sorted
    ordering.
    """
    def _format_substring(s):
        if s.isdigit():
            return 0,int(s)

        return 1,s.lower()

    filenames.sort(key=lambda s: list(map(_format_substring, NUMERIC_REGEXP.findall(s))))

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
            stringparts1[i] = 0,int(part)
        else:
            stringparts1[i] = 1,part
    for i, part in enumerate(stringparts2):
        if part.isdigit():
            stringparts2[i] = int(part)
        else:
            stringparts2[i] = 1,part

    return cmp(stringparts1, stringparts2)

def bin_search(lst, value):
    """ Binary search for sorted list C{lst}, looking for C{value}.
    @return: List index on success. On failure, it returns the 1's
    complement of the index where C{value} would be inserted.
    This implies that the return value is non-negative if and only if
    C{value} is contained in C{lst}. """

    index = bisect.bisect_left(lst, value)
    if index != len(lst) and lst[index] == value:
        return index
    else:
        return ~index


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
    if 0 == n:
        return 1
    return int(math.log10(abs(n))) + 1

def format_byte_size(n):
    s=0
    while n>=1024:
        s+=1
        n/=1024.0
    try:
        e=PREFIXED_BYTE_UNITS[s]
    except IndexError:
        e='C{}i'.format(s)
    return '{} {}'.format(round(n,3),e)

def garbage_collect():
    """ Runs the garbage collector. """
    gc.collect(0)

def pkg_path(*args):
    return os.path.join(sys.path[0], 'mcomix', *args)

def read_binary(*args):
    with open(pkg_path(*args), mode='rb') as f:
        return f.read()

def div(a, b):
    return float(a) / float(b)

def volume(t):
    return reduce(operator.mul, t, 1)

def relerr(approx, ideal):
    return abs(div(approx - ideal, ideal))

def smaller(a, b):
    """ Returns a list with the i-th element set to True if and only the i-th
    element in a is less than the i-th element in b. """
    return map(operator.lt, a, b)

def smaller_or_equal(a, b):
    """ Returns a list with the i-th element set to True if and only the i-th
    element in a is less than or equal to the i-th element in b. """
    return list(map(operator.le, a, b))

def scale(t, factor):
    return [x * factor for x in t]

def vector_sub(a, b):
    """ Subtracts vector b from vector a. """
    return tuple(map(operator.sub, a, b))

def vector_add(a, b):
    """ Adds vector a to vector b. """
    return tuple(map(operator.add, a, b))

def vector_opposite(a):
    """ Returns the opposite vector -a. """
    return tuple(map(operator.neg, a))

# vim: expandtab:sw=4:ts=4

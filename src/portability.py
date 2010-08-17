"""Portability functions for Comix."""

import os
import sys


def get_home_directory():
    """On UNIX-like systems, this method will return the path of the home
    directory, e.g. /home/username. On Windows, it will return a Comix
    sub-directory of <Documents and Settings/Username>.
    """
    if sys.platform == 'win32':
        return os.path.join(os.path.expanduser('~'), 'Comix')
    else:
        return os.path.expanduser('~')


def get_config_directory():
    """Return the path to the Comix config directory. On UNIX, this will
    be $XDG_CONFIG_HOME/comix, on Windows it will be the same directory as
    get_home_directory().
    
    See http://standards.freedesktop.org/basedir-spec/latest/ for more
    information on the $XDG_CONFIG_HOME environmental variable.
    """
    if sys.platform == 'win32':
        return get_home_directory()
    else:
        base_path = os.getenv('XDG_CONFIG_HOME',
            os.path.join(get_home_directory(), '.config'))
        return os.path.join(base_path, 'comix')


def get_data_directory():
    """Return the path to the Comix data directory. On UNIX, this will
    be $XDG_DATA_HOME/comix, on Windows it will be the same directory as
    get_home_directory().
    
    See http://standards.freedesktop.org/basedir-spec/latest/ for more
    information on the $XDG_DATA_HOME environmental variable.
    """
    if sys.platform == 'win32':
        return get_home_directory()
    else:
        base_path = os.getenv('XDG_DATA_HOME',
            os.path.join(get_home_directory(), '.local/share'))
        return os.path.join(base_path, 'comix')

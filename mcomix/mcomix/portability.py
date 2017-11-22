"""Portability functions for MComix."""

import sys
import locale
import ctypes

def uri_prefix():
    """ The prefix used for creating file URIs. """
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
    """ Simply returns sys.argv, converted to Unicode objects on UNIX. """

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

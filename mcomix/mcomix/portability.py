'''Portability functions for MComix.'''

import sys
import locale
import ctypes

def uri_prefix():
    ''' The prefix used for creating file URIs. '''
    return 'file://'

def normalize_uri(uri):
    ''' Normalize URIs passed into the program by different applications,
    normally via drag-and-drop. '''

    if uri.startswith('file://localhost/'):  # Correctly formatted.
        return uri[16:]
    elif uri.startswith('file:///'):  # Nautilus etc.
        return uri[7:]
    elif uri.startswith('file:/'):  # Xffm etc.
        return uri[5:]
    else:
        return uri

def invalid_filesystem_chars():
    ''' List of characters that cannot be used in filenames on the target platform. '''
    if sys.platform == 'win32':
        return ':*?"<>|' + ''.join(chr(i) for i in range(32))
    else:
        return ''

def get_default_locale():
    ''' Gets the user's default locale. '''
    if sys.platform == 'win32':
        windll = ctypes.windll.kernel32
        code = windll.GetUserDefaultUILanguage()
        return locale.windows_locale[code]
    else:
        lang, _ = locale.getlocale()
        if lang:
            return lang
        else:
            return 'C'

# vim: expandtab:sw=4:ts=4

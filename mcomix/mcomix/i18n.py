''' i18n.py - Encoding and translation handler.'''

import gettext
import locale
import os
import sys
import threading

try:
    import chardet
except ImportError:
    chardet = None

from mcomix import preferences
from mcomix import portability
from mcomix import constants
from mcomix import tools
from mcomix import log

# Translation instance to enable other modules to use
# functions other than the global _() if necessary
_translation = None
_unicode_cache = {}
_lock = threading.Lock()

def to_unicode(s):
    with _lock:
        return _to_unicode(s)

def _to_unicode(string):
    '''Convert <string> to unicode. First try the default filesystem
    encoding, and then fall back on some common encodings.
    '''
    if string in _unicode_cache:
        return _unicode_cache[string]
    fsencoding = sys.getfilesystemencoding()
    if not isinstance(string, (bytes, bytearray)):
        string = string.encode(fsencoding, 'surrogateescape')

    probable_encoding = None
    if chardet:
        # Try chardet heuristic
        result = chardet.detect(string)
        if result['confidence'] > 0.9:
            # only accept detection with enough confidence
            probable_encoding = result['encoding']
    if not probable_encoding:
        probable_encoding = locale.getpreferredencoding()

    newstr = None
    for encoding in (probable_encoding, fsencoding,
                     'utf-8', 'latin-1'):
        try:
            newstr = string.decode(encoding)
            break
        except (UnicodeError, LookupError):
            pass
    if newstr is None:
        newstr = string.decode('utf-8', 'replace')

    _unicode_cache[string]=newstr
    return newstr

def to_utf8(string):
    ''' Helper function that converts unicode objects to UTF-8 encoded
    strings. Non-unicode strings are assumed to be already encoded
    and returned as-is. '''

    if isinstance(string, str):
        return string.encode('utf-8')
    else:
        return string

def install_gettext():
    ''' Initialize gettext with the correct directory that contains
    MComix translations. This has to be done before any calls to gettext.gettext
    have been made to ensure all strings are actually translated. '''

    # Add the sources' base directory to PATH to allow development without
    # explicitly installing the package.
    sys.path.append(constants.BASE_PATH)

    # Initialize default locale
    locale.setlocale(locale.LC_ALL, '')

    lang_identifiers = []
    if preferences.prefs['language'] != 'auto':
        lang = preferences.prefs['language']
        if lang not in ('en', 'en_US'):
            # .mo is not needed for english
            lang_identifiers.append(lang)
    else:
        # Get the user's current locale
        lang = portability.get_default_locale()
        for s in gettext._expand_lang(lang):
            lang = s.split('.')[0]
            if lang in ('en', 'en_US'):
                # .mo is not needed for english
                continue
            if lang not in lang_identifiers:
                lang_identifiers.append(lang)

    # Make sure GTK uses the correct language.
    os.environ['LANGUAGE'] = lang

    domain = constants.APPNAME.lower()

    for lang in lang_identifiers:
        resource_path = tools.pkg_path('messages', lang,
                                       'LC_MESSAGES', '%s.mo' % domain)
        try:
            with open(resource_path, mode = 'rb') as fp:
                translation = gettext.GNUTranslations(fp)
            break
        except IOError:
            log.error('locale file: %s not found.', resource_path)
    else:
        translation = gettext.NullTranslations()

    translation.install()

    global _translation
    _translation = translation

def get_translation():
    ''' Returns the gettext.Translation instance that has been initialized with
    install_gettext(). '''

    return _translation or gettext.NullTranslations()

# vim: expandtab:sw=4:ts=4

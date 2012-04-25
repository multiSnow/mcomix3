""" i18n.py - Encoding and translation handler."""

import sys
import os
import locale
import gettext
import pkg_resources

try:
    import chardet
except ImportError:
    chardet = None

from mcomix import preferences
from mcomix import portability
from mcomix import constants

# Translation instance to enable other modules to use
# functions other than the global _() if necessary
_translation = None

def to_unicode(string):
    """Convert <string> to unicode. First try the default filesystem
    encoding, and then fall back on some common encodings.
    """
    if isinstance(string, unicode):
        return string

    # Try chardet heuristic
    if chardet:
        probable_encoding = chardet.detect(string)['encoding'] or \
            locale.getpreferredencoding() # Fallback if chardet detection fails
    else:
        probable_encoding = locale.getpreferredencoding()

    for encoding in (
        probable_encoding,
        sys.getfilesystemencoding(),
        'utf-8',
        'latin-1'):

        try:
            ustring = unicode(string, encoding)
            return ustring

        except (UnicodeError, LookupError):
            pass

    return string.decode('utf-8', 'replace')

def to_utf8(string):
    """ Helper function that converts unicode objects to UTF-8 encoded
    strings. Non-unicode strings are assumed to be already encoded
    and returned as-is. """

    if isinstance(string, unicode):
        return string.encode('utf-8')
    else:
        return string

def install_gettext():
    """ Initialize gettext with the correct directory that contains
    MComix translations. This has to be done before any calls to gettext.gettext
    have been made to ensure all strings are actually translated. """

    # Add the sources' base directory to PATH to allow development without
    # explicitly installing the package.
    sys.path.append(constants.BASE_PATH)

    # Initialize default locale
    locale.setlocale(locale.LC_ALL, '')

    if preferences.prefs['language'] != 'auto':
        lang_identifiers = [ preferences.prefs['language'] ]
    else:
        # Get the user's current locale
        code = portability.get_default_locale()
        lang_identifiers = gettext._expand_lang(code)

    domain = constants.APPNAME.lower()
    translation = gettext.NullTranslations()

    # Search for .mo files manually, since gettext doesn't support setuptools/pkg_resources.
    for lang in lang_identifiers:
        resource = os.path.join(lang, 'LC_MESSAGES', '%s.mo' % domain)
        if pkg_resources.resource_exists('mcomix.messages', resource):
            translation = gettext.GNUTranslations(
                    pkg_resources.resource_stream('mcomix.messages', resource))
            break

    translation.install(unicode=True)

    global _translation
    _translation = translation

def get_translation():
    """ Returns the gettext.Translation instance that has been initialized with
    install_gettext(). """

    return _translation or gettext.NullTranslations()

# vim: expandtab:sw=4:ts=4

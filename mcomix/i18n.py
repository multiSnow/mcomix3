""" i18n.py - Encoding and translation handler."""

import sys
import os
import locale
import gettext

import preferences
import portability
import constants
import pkg_resources

# Translation instance to enable other modules to use
# functions other than the global _() if necessary
_translation = None

def to_unicode(string):
    """Convert <string> to unicode. First try the default filesystem
    encoding, and then fall back on some common encodings. If none
    of the convertions are successful, "???" is returned.
    """
    if isinstance(string, unicode):
        return string

    for encoding in (locale.getpreferredencoding(),
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

"""encoding.py - Encoding handler."""

import sys

_filesystemencoding = sys.getfilesystemencoding()

def to_unicode(string):
    """Convert <string> to unicode. First try the default filesystem
    encoding, and then fall back on some common encodings. If none
    of the convertions are successful, "???" is returned.
    """
    if isinstance(string, unicode):
        return string

    for encoding in (_filesystemencoding, 'utf-8', 'latin-1'):

        try:
            ustring = unicode(string, encoding)
            return ustring

        except (UnicodeError, LookupError):
            pass

    return u'???'

def to_utf8(string):
    """ Helper function that converts unicode objects to UTF-8 encoded
    strings. Non-unicode strings are assumed to be already encoded
    and returned as-is. """

    if isinstance(string, unicode):
        return string.encode('utf-8')
    else:
        return string

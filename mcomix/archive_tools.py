"""archive_tools.py - Archive tool functions."""

import os
import re
import zipfile
import tarfile

from mcomix import constants
from mcomix import log
from mcomix.archive import zip
from mcomix.archive import rar
from mcomix.archive import tar
from mcomix.archive import sevenzip
from mcomix.archive import lha

def szip_available():
    return sevenzip.SevenZipArchive.is_available()

def rar_available():
    return rar.RarArchive.is_available() or szip_available()

def lha_available():
    return lha.LhaArchive.is_available() or szip_available()

def get_supported_archive_regex():
    """ Returns a compiled regular expression that contains extensions
    of all currently supported file types, based on available applications.
    """
    formats = list(constants.ZIP_FORMATS[1] + constants.TAR_FORMATS[1])

    if szip_available():
        formats.extend(constants.SZIP_FORMATS[1])

    if rar_available():
        formats.extend(constants.RAR_FORMATS[1])

    if lha_available():
        formats.extend(constants.LHA_FORMATS[1])

    # Strip leading glob characters "*." from file extensions
    formats = [format[2:] for format in formats]
    return re.compile(r'\.(' + '|'.join(formats) + r')\s*$', re.I)

def archive_mime_type(path):
    """Return the archive type of <path> or None for non-archives."""
    try:

        if os.path.isfile(path):

            if not os.access(path, os.R_OK):
                return None

            if zipfile.is_zipfile(path):
                return constants.ZIP

            fd = open(path, 'rb')
            magic = fd.read(4)
            fd.close()

            try:
                istarfile = tarfile.is_tarfile(path)
            except IOError:
                # Tarfile raises an error when accessing certain network shares
                istarfile = False

            if istarfile and os.path.getsize(path) > 0:
                if magic.startswith('BZh'):
                    return constants.BZIP2
                elif magic.startswith('\037\213'):
                    return constants.GZIP
                else:
                    return constants.TAR

            if magic == 'Rar!':
                return constants.RAR

            elif magic == '7z\xBC\xAF':
                return constants.SEVENZIP

            elif magic[2:] == '-l':
                return constants.LHA

            #if magic == '%PDF':
            #    return constants.PDF

    except Exception:
        log.warning(_('! Could not read %s'), path)

    return None

def get_archive_info(path):
    """Return a tuple (mime, num_pages, size) with info about the archive
    at <path>, or None if <path> doesn't point to a supported
    """
    image_re = constants.SUPPORTED_IMAGE_REGEX

    # XXX: Deferred import to avoid circular dependency
    from mcomix import archive_extractor

    extractor = archive_extractor.Extractor()
    try:
        extractor.setup(path, None)
    except archive_extractor.ArchiveException:
        return None

    mime = extractor.get_mime_type()
    if mime is None:
        return None

    files = extractor.get_files()
    extractor.close()

    num_pages = len(filter(image_re.search, files))
    size = os.stat(path).st_size

    return (mime, num_pages, size)

def get_archive_handler(path):
    """ Returns a fitting extractor handler for the archive passed
    in <path>. Returns None if no matching extractor was found. """
    mime = archive_mime_type(path)

    if mime == constants.ZIP:
        return zip.ZipArchive(path)
    elif mime in (constants.TAR, constants.GZIP, constants.BZIP2):
        return tar.TarArchive(path)
    elif mime == constants.RAR and rar.RarArchive.is_available():
        return rar.RarArchive(path)
    elif mime == constants.RAR and sevenzip.SevenZipArchive.is_available():
        log.info('Using Sevenzip for RAR archives.')
        return sevenzip.SevenZipArchive(path)
    elif mime == constants.SEVENZIP and sevenzip.SevenZipArchive.is_available():
        return sevenzip.SevenZipArchive(path)
    elif mime == constants.LHA and lha.LhaArchive.is_available():
        return lha.LhaArchive(path)
    elif mime == constants.LHA and sevenzip.SevenZipArchive.is_available():
        log.info('Using Sevenzip for LHA archives.')
        return sevenzip.SevenZipArchive(path)
    else:
        return None

# vim: expandtab:sw=4:ts=4

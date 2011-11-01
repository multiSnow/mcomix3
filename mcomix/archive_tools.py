"""archive_tools.py - Archive tool functions."""

import os
import zipfile
import tarfile

from mcomix import constants
from mcomix import log
from mcomix.archive import zip
from mcomix.archive import rar
from mcomix.archive import tar
from mcomix.archive import sevenzip
from mcomix.archive import lha

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

            if tarfile.is_tarfile(path) and os.path.getsize(path) > 0:

                if magic.startswith('BZh'):
                    return constants.BZIP2

                if magic.startswith('\037\213'):
                    return constants.GZIP

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
    extractor.setup(path, None)
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

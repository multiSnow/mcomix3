"""archive_tools.py - Archive tool functions."""

import os
import zipfile
import tarfile

import archive_extractor
import constants
import log
import archive.zip
import archive.rar
import archive.tar
import archive.sevenzip
import archive.lha

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
    at <path>, or None if <path> doesn't point to a supported archive.
    """
    image_re = constants.SUPPORTED_IMAGE_REGEX

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
        return archive.zip.ZipArchive(path)
    elif mime in (constants.TAR, constants.GZIP, constants.BZIP2):
        return archive.tar.TarArchive(path)
    elif mime == constants.RAR and archive.rar.RarArchive.is_available():
        return archive.rar.RarArchive(path)
    elif mime == constants.RAR and archive.sevenzip.SevenZipArchive.is_available():
        return archive.sevenzip.SevenZipArchive(path)
    elif mime == constants.SEVENZIP and archive.sevenzip.SevenZipArchive.is_available():
        return archive.sevenzip.SevenZipArchive(path)
    elif mime == constants.LHA and archive.lha.LhaArchive.is_available():
        return archive.lha.LhaArchive(path)
    elif mime == constants.LHA and archive.sevenzip.SevenZipArchive.is_available():
        return archive.sevenzip.SevenZipArchive(path)
    else:
        return None

# vim: expandtab:sw=4:ts=4

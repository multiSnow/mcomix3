"""archive_tools.py - Archive tool functions."""

import os
import zipfile
import tarfile
import process
import archive_extractor
import constants
#import poppler
#import cairo

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
                
            #if magic == '%PDF':
            #    return constants.PDF

    except Exception:
        print _('! Error while reading'), path

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


def _get_rar_exec():
    """Return the name of the RAR file extractor executable, or None if
    no such executable is found.
    """
    for command in ('unrar', 'rar'):

        if process.Process([command]).spawn() is not None:
            return command

    return None


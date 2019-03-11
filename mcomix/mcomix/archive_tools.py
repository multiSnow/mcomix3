"""archive_tools.py - Archive tool functions."""

import os
import re
import shutil
import zipfile
import tarfile
import tempfile
import operator
from functools import reduce

from mcomix import image_tools
from mcomix import constants
from mcomix import log
from mcomix.archive import (
    lha_external,
    pdf_external,
    rar,
    rar_external,
    sevenzip_external,
    tar,
    zip,
    zip_external,
)

# Handlers for each archive type.
_HANDLERS = {
    constants.ZIP: (
        zip.ZipArchive,
    ),
    # Prefer 7z over zip executable for encryption and Unicode support.
    constants.ZIP_EXTERNAL: (
        sevenzip_external.SevenZipArchive,
        zip_external.ZipArchive
    ),
    constants.TAR: (
        tar.TarArchive,
    ),
    constants.GZIP: (
        tar.TarArchive,
    ),
    constants.BZIP2: (
        tar.TarArchive,
    ),
    constants.XZ: (
        # No LZMA support in Python 2 tarfile module.
        sevenzip_external.TarArchive,
    ),
    constants.RAR: (
        rar.RarArchive,
        rar_external.RarArchive,
        # Last resort: some versions of 7z support RAR.
        sevenzip_external.SevenZipArchive,
    ),
    # Prefer 7z over lha executable for Unicode support.
    constants.LHA: (
        sevenzip_external.SevenZipArchive,
        lha_external.LhaArchive,
    ),
    constants.SEVENZIP: (
        sevenzip_external.SevenZipArchive,
    ),
    constants.PDF: (
        pdf_external.PdfArchive,
    ),
}

def _get_handler(archive_type):
    """ Return best archive class for format <archive_type> """

    for handler in _HANDLERS[archive_type]:
        if not hasattr(handler, 'is_available'):
            return handler
        if handler.is_available():
            return handler

def _is_available(archive_type):
    """ Return True if a handler supporting the <archive_type> format is available """
    return _get_handler(archive_type) is not None

def szip_available():
    return _is_available(constants.SEVENZIP)

def rar_available():
    return _is_available(constants.RAR)

def lha_available():
    return _is_available(constants.LHA)

def pdf_available():
    return _is_available(constants.PDF)

SUPPORTED_ARCHIVE_EXTS=[]
SUPPORTED_ARCHIVE_FORMATS={}

def init_supported_formats():
    for name, formats, is_available in (
        ('ZIP', constants.ZIP_FORMATS , True            ),
        ('Tar', constants.TAR_FORMATS , True            ),
        ('RAR', constants.RAR_FORMATS , rar_available() ),
        ('7z' , constants.SZIP_FORMATS, szip_available()),
        ('LHA', constants.LHA_FORMATS , lha_available() ),
        ('PDF', constants.PDF_FORMATS , pdf_available() ),
    ):
        if not is_available:
            continue
        SUPPORTED_ARCHIVE_FORMATS[name]=([],[])
        SUPPORTED_ARCHIVE_FORMATS[name][0].extend(
            map(lambda s:s.lower(),formats[0])
        )
        # archive extensions has no '.'
        SUPPORTED_ARCHIVE_FORMATS[name][1].extend(
            map(lambda s:'.'+s.lower(),formats[1])
        )
    # cache a supported extensions list
    for mimes,exts in SUPPORTED_ARCHIVE_FORMATS.values():
        SUPPORTED_ARCHIVE_EXTS.extend(exts)

def get_supported_formats():
    if not SUPPORTED_ARCHIVE_FORMATS:
        init_supported_formats()
    return SUPPORTED_ARCHIVE_FORMATS

def is_archive_file(path):
    if not SUPPORTED_ARCHIVE_FORMATS:
        init_supported_formats()
    return os.path.splitext(path)[1].lower() in SUPPORTED_ARCHIVE_EXTS

def archive_mime_type(path):
    """Return the archive type of <path> or None for non-archives."""
    try:

        if os.path.isfile(path):

            if not os.access(path, os.R_OK):
                return None

            if zipfile.is_zipfile(path):
                if zip.is_py_supported_zipfile(path):
                    return constants.ZIP
                else:
                    return constants.ZIP_EXTERNAL

            with open(path, 'rb') as fd:
                magic = fd.read(5)

            try:
                istarfile = tarfile.is_tarfile(path)
            except IOError:
                # Tarfile raises an error when accessing certain network shares
                istarfile = False

            if istarfile and os.path.getsize(path) > 0:
                if magic.startswith(b'BZh'):
                    return constants.BZIP2
                elif magic.startswith(b'\037\213'):
                    return constants.GZIP
                else:
                    return constants.TAR

            if magic[0:4] == b'Rar!':
                return constants.RAR

            if magic[0:4] == b'7z\xBC\xAF':
                return constants.SEVENZIP

            # Headers for TAR-XZ and TAR-LZMA that aren't supported by tarfile
            if magic[0:5] == b'\xFD7zXZ' or magic[0:5] == b']\x00\x00\x80\x00':
                return constants.XZ

            if magic[2:4] == b'-l':
                return constants.LHA

            if magic[0:4] == b'%PDF':
                return constants.PDF

    except Exception:
        log.warning(_('! Could not read %s'), path)

    return None

def get_archive_info(path):
    """Return a tuple (mime, num_pages, size) with info about the archive
    at <path>, or None if <path> doesn't point to a supported
    """
    with tempfile.TemporaryDirectory(prefix='mcomix_archive_info.') as tmpdir:
        mime = archive_mime_type(path)
        archive = get_recursive_archive_handler(path, tmpdir, type=mime)
        if archive is None:
            return None

        files = archive.list_contents(decrypt=False)
        num_pages = sum([image_tools.is_image_file(f) for f in files])
        size = os.stat(path).st_size

        return (mime, num_pages, size)

def get_archive_handler(path, type=None):
    """ Returns a fitting extractor handler for the archive passed
    in <path> (with optional mime type <type>. Returns None if no matching
    extractor was found.
    """
    if type is None:
        type = archive_mime_type(path)
        if type is None:
            return None

    handler = _get_handler(type)
    if handler is None:
        return None

    return handler(path)

def get_recursive_archive_handler(path, destination_dir, type=None):
    """ Same as <get_archive_handler> but the handler will transparently handle
    archives within archives.
    """
    archive = get_archive_handler(path, type=type)
    if archive is None:
        return None
    # XXX: Deferred import to avoid circular dependency
    from mcomix.archive import archive_recursive
    return archive_recursive.RecursiveArchive(archive, destination_dir)
 
# vim: expandtab:sw=4:ts=4

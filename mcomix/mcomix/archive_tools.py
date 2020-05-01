'''archive_tools.py - Archive tool functions.'''

import os
import re
import shutil
import zipfile
import tarfile
import tempfile
import operator

from mcomix import image_tools
from mcomix import constants
from mcomix import log
from mcomix.archive import (
    archivemount,
    lha_external,
    pdf_external,
    rar,
    rar_external,
    sevenzip_external,
    squashfs,
    tar,
    zip_py,
    zip_external,
)

# Handlers for each archive type.
_HANDLERS = {
    constants.ZIP: (
        zip_py.ZipArchive,
    ),
    constants.ZIP_EXTERNAL: (
        # Prefer 7z over zip executable for encryption and Unicode support.
        sevenzip_external.SevenZipArchive,
        zip_external.ZipArchive
    ),
    constants.TAR: (
        archivemount.ArchivemountArchive,
        tar.TarArchive,
    ),
    constants.GZIP: (
        tar.TarArchive,
    ),
    constants.BZIP2: (
        tar.TarArchive,
    ),
    constants.XZ: (
        tar.TarArchive,
    ),
    constants.RAR: (
        rar.RarArchive,
        rar_external.RarArchive,
        # Last resort: some versions of 7z support RAR.
        sevenzip_external.SevenZipArchive,
    ),
    constants.RAR5: (
        rar.RarArchive,
        rar_external.RarArchive,
    ),
    constants.LHA: (
        # Prefer 7z over lha executable for Unicode support.
        sevenzip_external.SevenZipArchive,
        lha_external.LhaArchive,
    ),
    constants.SEVENZIP: (
        sevenzip_external.SevenZipArchive,
    ),
    constants.PDF: (
        pdf_external.PdfArchive,
    ),
    constants.SQUASHFS: (
        squashfs.SquashfsArchive,
        sevenzip_external.SevenZipArchive,
    ),
}

def _get_handler(archive_type):
    ''' Return best archive class for format <archive_type> '''

    for handler in _HANDLERS[archive_type]:
        if not hasattr(handler, 'is_available'):
            return handler
        if handler.is_available():
            return handler

def _is_available(archive_type):
    ''' Return True if a handler supporting the <archive_type> format is available '''
    return _get_handler(archive_type) is not None

def szip_available():
    return _is_available(constants.SEVENZIP)

def rar_available():
    return _is_available(constants.RAR)

def lha_available():
    return _is_available(constants.LHA)

def pdf_available():
    return _is_available(constants.PDF)

def squashfs_available():
    return _is_available(constants.SQUASHFS)

SUPPORTED_ARCHIVE_EXTS=set()
SUPPORTED_ARCHIVE_FORMATS={}

def init_supported_formats():
    for name, formats, is_available in (
        ('ZIP', constants.ZIP_FORMATS , True            ),
        ('Tar', constants.TAR_FORMATS , True            ),
        ('RAR', constants.RAR_FORMATS , rar_available() ),
        ('7z' , constants.SZIP_FORMATS, szip_available()),
        ('LHA', constants.LHA_FORMATS , lha_available() ),
        ('PDF', constants.PDF_FORMATS , pdf_available() ),
        ('SquashFS', constants.SQUASHFS_FORMATS , squashfs_available() ),
    ):
        if not is_available:
            continue
        SUPPORTED_ARCHIVE_FORMATS[name]=(set(),set())
        for ext, mime in formats:
            SUPPORTED_ARCHIVE_FORMATS[name][0].add(mime.lower())
            SUPPORTED_ARCHIVE_FORMATS[name][1].add(ext.lower())
        # also add to supported extensions list
        SUPPORTED_ARCHIVE_EXTS.update(SUPPORTED_ARCHIVE_FORMATS[name][1])

def get_supported_formats():
    if not SUPPORTED_ARCHIVE_FORMATS:
        init_supported_formats()
    return SUPPORTED_ARCHIVE_FORMATS

def is_archive_file(path):
    if not SUPPORTED_ARCHIVE_FORMATS:
        init_supported_formats()
    return path.lower().endswith(tuple(SUPPORTED_ARCHIVE_EXTS))

def archive_mime_type(path):
    '''Return the archive type of <path> or None for non-archives.'''
    try:

        if os.path.isfile(path):

            if not os.access(path, os.R_OK):
                return None

            if zipfile.is_zipfile(path):
                if zip_py.is_py_supported_zipfile(path):
                    return constants.ZIP
                else:
                    return constants.ZIP_EXTERNAL

            with open(path, 'rb') as fd:
                magic = fd.read(10)

            try:
                istarfile = tarfile.is_tarfile(path)
            except IOError:
                # Tarfile raises an error when accessing certain network shares
                istarfile = False

            if istarfile and os.path.getsize(path) > 0:
                if magic.startswith(b'\x1f\x8b\x08'):
                    return constants.GZIP
                elif magic.startswith(b'BZh') and magic[4:10] == b'1AY&SY':
                    return constants.BZIP2
                elif magic.startswith((b'\x5d\x00\x00\x80', b'\xfd7zXZ')):
                    return constants.XZ
                else:
                    return constants.TAR

            if magic.startswith(b'Rar!\x1a\x07\x00'):
                return constants.RAR

            # test Rar 5.0 format
            if magic.startswith(b'Rar!\x1a\x07\x01'):
                if sevenzip_external.is_7z_support_rar5():
                    return constants.RAR5
                else:
                    return constants.RAR

            if magic[0:6] == b'7z\xbc\xaf\x27\x1c':
                return constants.SEVENZIP

            if magic[2:].startswith((b'-lh',b'-lz')):
                return constants.LHA

            if magic[0:4] == b'%PDF':
                return constants.PDF

            if magic.startswith((b'sqsh',b'hsqs')):
                return constants.SQUASHFS

    except Exception:
        log.warning(_('! Could not read %s'), path)

    return None

def get_archive_info(path):
    '''Return a tuple (mime, num_pages, size) with info about the archive
    at <path>, or None if <path> doesn't point to a supported
    '''
    mime = archive_mime_type(path)
    with get_recursive_archive_handler(path, type=mime,
                                       prefix='mcomix_archive_info.') as archive:
        if archive is None:
            return None

        files = archive.list_contents(decrypt=False)
        num_pages = sum([image_tools.is_image_file(f) for f in files])
        size = os.stat(path).st_size

        return (mime, num_pages, size)

def get_archive_handler(path, type=None):
    ''' Returns a fitting extractor handler for the archive passed
    in <path> (with optional mime type <type>. Returns None if no matching
    extractor was found.
    '''
    if type is None:
        type = archive_mime_type(path)
        if type is None:
            return None

    handler = _get_handler(type)
    if handler is None:
        return None

    return handler(path)

def get_recursive_archive_handler(path, type=None, **kwargs):
    ''' Same as <get_archive_handler> but the handler will transparently handle
    archives within archives.
    '''
    archive = get_archive_handler(path, type=type)
    if archive is None:
        return None
    # XXX: Deferred import to avoid circular dependency
    from mcomix.archive import archive_recursive
    return archive_recursive.RecursiveArchive(archive, **kwargs)

# vim: expandtab:sw=4:ts=4

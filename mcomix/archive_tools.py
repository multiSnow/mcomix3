"""archive_tools.py - Archive tool functions."""

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
from mcomix.archive import zip
from mcomix.archive import zip_external
from mcomix.archive import rar
from mcomix.archive import tar
from mcomix.archive import sevenzip
from mcomix.archive import lha
from mcomix.archive import pdf

def szip_available():
    return sevenzip.SevenZipArchive.is_available()

def rar_available():
    return rar.RarArchive.is_available() or szip_available()

def lha_available():
    return lha.LhaArchive.is_available() or szip_available()

def pdf_available():
    return pdf.PdfArchive.is_available()

def get_supported_formats():
    supported_formats = {}
    for name, formats, is_available in (
        ('ZIP', constants.ZIP_FORMATS , True            ),
        ('Tar', constants.TAR_FORMATS , True            ),
        ('RAR', constants.RAR_FORMATS , rar_available() ),
        ('7z' , constants.SZIP_FORMATS, szip_available()),
        ('LHA', constants.LHA_FORMATS , lha_available() ),
        ('PDF', constants.PDF_FORMATS , pdf_available() ),
    ):
        if is_available:
            supported_formats[name] = formats
    return supported_formats

# Set supported archive extensions regexp from list of supported formats.
SUPPORTED_ARCHIVE_REGEX = re.compile(r'\.(%s)$' %
                                     '|'.join(sorted(reduce(
                                         operator.add,
                                         [map(re.escape, fmt[1]) for fmt
                                          in get_supported_formats().values()]
                                     ))), re.I)

def is_archive_file(path):
    """Return True if the file at <path> is a supported archive file.
    """
    return SUPPORTED_ARCHIVE_REGEX.search(path) is not None

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

            fd = open(path, 'rb')
            magic = fd.read(5)
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

            if magic[0:4] == 'Rar!':
                return constants.RAR

            elif magic[0:4] == '7z\xBC\xAF':
                return constants.SEVENZIP

            # Headers for TAR-XZ and TAR-LZMA that aren't supported by tarfile
            elif magic[0:5] == '\xFD7zXZ' or magic[0:5] == ']\x00\x00\x80\x00':
                return constants.SEVENZIP

            elif magic[2:] == '-l':
                return constants.LHA

            if magic[0:4] == '%PDF':
                return constants.PDF

    except Exception:
        log.warning(_('! Could not read %s'), path)

    return None

def get_archive_info(path):
    """Return a tuple (mime, num_pages, size) with info about the archive
    at <path>, or None if <path> doesn't point to a supported
    """
    cleanup = []
    try:
        tmpdir = tempfile.mkdtemp(prefix=u'mcomix_archive_info.')
        cleanup.append(lambda: shutil.rmtree(tmpdir, True))

        mime = archive_mime_type(path)
        archive = get_recursive_archive_handler(path, tmpdir, type=mime)
        if archive is None:
            return None
        cleanup.append(archive.close)

        files = archive.list_contents()
        num_pages = len(filter(image_tools.SUPPORTED_IMAGE_REGEX.search, files))
        size = os.stat(path).st_size

        return (mime, num_pages, size)
    finally:
        for fn in reversed(cleanup):
            fn()

def get_archive_handler(path, type=None):
    """ Returns a fitting extractor handler for the archive passed
    in <path> (with optional mime type <type>. Returns None if no matching
    extractor was found.
    """
    if type is None:
        type = archive_mime_type(path)

    if type == constants.ZIP:
        return zip.ZipArchive(path)
    elif type == constants.ZIP_EXTERNAL and zip_external.ZipExecArchive.is_available():
        return zip_external.ZipExecArchive(path)
    elif type == constants.ZIP_EXTERNAL and sevenzip.SevenZipArchive.is_available():
        log.info('Using Sevenzip for unsupported zip archives.')
        return sevenzip.SevenZipArchive(path)
    elif type in (constants.TAR, constants.GZIP, constants.BZIP2):
        return tar.TarArchive(path)
    elif type == constants.RAR and rar.RarArchive.is_available():
        return rar.RarArchive(path)
    elif type == constants.RAR and sevenzip.SevenZipArchive.is_available():
        log.info('Using Sevenzip for RAR archives.')
        return sevenzip.SevenZipArchive(path)
    elif type == constants.SEVENZIP and sevenzip.SevenZipArchive.is_available():
        return sevenzip.SevenZipArchive(path)
    elif type == constants.LHA and lha.LhaArchive.is_available():
        return lha.LhaArchive(path)
    elif type == constants.LHA and sevenzip.SevenZipArchive.is_available():
        log.info('Using Sevenzip for LHA archives.')
        return sevenzip.SevenZipArchive(path)
    elif type == constants.PDF and pdf.PdfArchive.is_available():
        return pdf.PdfArchive(path)
    else:
        return None

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

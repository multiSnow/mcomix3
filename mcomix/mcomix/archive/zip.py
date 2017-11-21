# -*- coding: utf-8 -*-

""" Unicode-aware wrapper for zipfile.ZipFile. """

import os
import zipfile
from contextlib import closing

from mcomix import log
from mcomix.archive import archive_base



def is_py_supported_zipfile(path):
    """Check if a given zipfile has all internal files stored with Python supported compression
    """
    # Use contextlib's closing for 2.5 compatibility
    with closing(zipfile.ZipFile(path, 'r')) as zip_file:
        for file_info in zip_file.infolist():
            if file_info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                return False
    return True

class ZipArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(ZipArchive, self).__init__(archive)
        self.zip = zipfile.ZipFile(archive, 'r')

        # Encryption is supported starting with Python 2.6
        self._encryption_supported = hasattr(self.zip, "setpassword")
        self._password = None

    def iter_contents(self):
        if self._encryption_supported and self._has_encryption():
            self._get_password()
            self.zip.setpassword(self._password)

        for filename in self.zip.namelist():
            yield self._unicode_filename(filename)

    def extract(self, filename, destination_dir):
        with self._create_file(os.path.join(destination_dir, filename)) as new:
            content = self.zip.read(self._original_filename(filename))
            new.write(content)

        zipinfo = self.zip.getinfo(self._original_filename(filename))
        if len(content) != zipinfo.file_size:
            log.warning(_('%(filename)s\'s extracted size is %(actual_size)d bytes,'
                ' but should be %(expected_size)d bytes.'
                ' The archive might be corrupt or in an unsupported format.'),
                { 'filename' : filename, 'actual_size' : len(content),
                  'expected_size' : zipinfo.file_size })



    def close(self):
        self.zip.close()

    def _has_encryption(self):
        """ Checks all files in the archive for encryption.
        Returns True if at least one encrypted file was found. """
        for zipinfo in self.zip.infolist():
            if zipinfo.flag_bits & 0x1: # File is encrypted
                return True

        return False

# vim: expandtab:sw=4:ts=4

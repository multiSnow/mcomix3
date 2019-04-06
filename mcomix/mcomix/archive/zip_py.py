# -*- coding: utf-8 -*-

''' Unicode-aware wrapper for zipfile.ZipFile. '''

import os
import zipfile

from mcomix import log
from mcomix.archive import archive_base



def is_py_supported_zipfile(path):
    '''Check if a given zipfile has all internal files stored with Python supported compression
    '''
    with zipfile.ZipFile(path, mode='r') as zip_file:
        for file_info in zip_file.infolist():
            try:
                descr=zipfile._get_decompressor(file_info.compress_type)
            except:
                return False
    return True

class ZipArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(ZipArchive, self).__init__(archive)
        self._zip = zipfile.ZipFile(archive, 'r')

        self.is_encrypted = self._has_encryption()
        self._password = None

    def iter_contents(self):
        if self.is_encrypted:
            self._get_password()
            self._zip.setpassword(self._password)

        for filename in self._zip.namelist():
            yield self._unicode_filename(filename)

    def extract(self, filename, destination_dir):
        destination_path = os.path.join(destination_dir, filename)
        with self._create_file(destination_path) as new:
            content = self._zip.read(self._original_filename(filename))
            new.write(content)

        zipinfo = self._zip.getinfo(self._original_filename(filename))
        if len(content) != zipinfo.file_size:
            log.warning(_('%(filename)s\'s extracted size is %(actual_size)d bytes,'
                ' but should be %(expected_size)d bytes.'
                ' The archive might be corrupt or in an unsupported format.'),
                { 'filename' : filename, 'actual_size' : len(content),
                  'expected_size' : zipinfo.file_size })
        return destination_path

    def close(self):
        self._zip.close()

    def _has_encryption(self):
        ''' Checks all files in the archive for encryption.
        Returns True if at least one encrypted file was found. '''
        for zipinfo in self._zip.infolist():
            if zipinfo.flag_bits & 0x1: # File is encrypted
                return True

        return False

# vim: expandtab:sw=4:ts=4

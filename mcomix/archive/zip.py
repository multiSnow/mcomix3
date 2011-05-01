# -*- coding: utf-8 -*-

""" Unicode-aware wrapper for zipfile.ZipFile. """

import os
import zipfile
import threading
import archive_base

class ZipArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(ZipArchive, self).__init__(archive)
        self.zip = zipfile.ZipFile(archive, 'r')

        # Encryption is supported starting with Python 2.6
        self._encryption_supported = hasattr(self.zip, "setpassword")
        self._password = None

    def list_contents(self):
        if self._encryption_supported \
            and self._has_encryption()\
            and self._password is None:

            # Wait for the main thread to set self._password
            event = threading.Event()
            self._password_required(event)
            event.wait()

        if self._encryption_supported \
            and self._password is not None:

            self.zip.setpassword(self._password)

        return [self._unicode_filename(filename)
           for filename in self.zip.namelist()]

    def extract(self, filename, destination_path):
        destination_dir = os.path.split(destination_path)[0]
        self._create_directory(destination_dir)

        new = file(destination_path, 'wb')
        new.write(self.zip.read(self._original_filename(filename)))
        new.close()

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

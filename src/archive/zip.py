# -*- encoding: utf-8 -*-

""" Unicode-aware wrapper for zipfile.ZipFile. """

import os
import zipfile
import archive_base

class ZipArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(ZipArchive, self).__init__(archive)
        self.zip = zipfile.ZipFile(archive, 'r')

    def list_contents(self):
        return [self._unicode_filename(filename)
           for filename in self.zip.namelist()]

    def extract(self, filename, destination_path):
        destination_dir = os.path.split(destination_path)[0]
        self._create_directory(destination_path)

        new = file(destination_path, 'wb')
        new.write(self.zip.read(self._original_filename(filename)))
        new.close()

    def close(self):
        self.zip.close()

# vim: expandtab:sw=4:ts=4

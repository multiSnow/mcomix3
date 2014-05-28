# -*- coding: utf-8 -*-

""" Unicode-aware wrapper for tarfile.TarFile. """

import os
import tarfile
import archive_base

class TarArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(TarArchive, self).__init__(archive)
        self.tar = tarfile.open(archive, 'r')

    def is_solid(self):
        return True

    def list_contents(self):
        return [self._unicode_filename(filename)
           for filename in self.tar.getnames()]

    def extract(self, filename, destination_dir):
        new = self._create_file(os.path.join(destination_dir, filename))
        file_object = self.tar.extractfile(self._original_filename(filename))
        new.write(file_object.read())
        file_object.close()
        new.close()

    def close(self):
        self.tar.close()

# vim: expandtab:sw=4:ts=4

# -*- coding: utf-8 -*-

""" Unicode-aware wrapper for tarfile.TarFile. """

import os
import tarfile
import archive_base

class TarArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(TarArchive, self).__init__(archive)
        # Track if archive contents have been listed at least one time: this
        # must be done before attempting to extract contents.
        self._contents_listed = False
        self._contents = []

    def is_solid(self):
        return True

    def iter_contents(self):
        if self._contents_listed:
            for name in self._contents:
                yield name
            return
        # Make sure we start back at the beginning of the tar.
        self.tar = tarfile.open(self.archive, 'r')
        self._contents = []
        while True:
            info = self.tar.next()
            if info is None:
                break
            name = self._unicode_filename(info.name)
            self._contents.append(name)
            yield name
        self._contents_listed = True

    def list_contents(self):
        return [f for f in self.iter_contents()]

    def extract(self, filename, destination_dir):
        if not self._contents_listed:
            self.list_contents()
        new = self._create_file(os.path.join(destination_dir, filename))
        file_object = self.tar.extractfile(self._original_filename(filename))
        new.write(file_object.read())
        file_object.close()
        new.close()

    def iter_extract(self, entries, destination_dir):
        if not self._contents_listed:
            self.list_contents()
        for f in super(TarArchive, self).iter_extract(entries, destination_dir):
            yield f

    def close(self):
        self.tar.close()

# vim: expandtab:sw=4:ts=4

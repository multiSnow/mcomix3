# -*- coding: utf-8 -*-

''' Unicode-aware wrapper for tarfile.TarFile. '''

import collections
import os
import tarfile

from mcomix.archive import archive_base

class TarArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(TarArchive, self).__init__(archive)
        self._tar = tarfile.open(self.archive, 'r:*')

        # tarfile is not thread-safe
        # so use OrderedDict to save TarInfo in order
        # {unicode_name: TarInfo}
        self._contents_info = collections.OrderedDict()
        for member in self._tar.getmembers():
            if tarfile.ENCODING is 'utf-8':
                # filename is utf8 encoded
                self._contents_info[member.name] = member
            else:
                # tarfile use tarfile.ENCODING to decode non-utf8 filename
                # revert to bytes before guessing encode
                name_bytes = member.name.encode(tarfile.ENCODING)
                self._contents_info[self._unicode_filename(name_bytes)] = member

    def is_solid(self):
        return True

    def iter_contents(self):
        yield from self._contents_info.keys()

    def extract(self, filename, destination_dir):
        destination_path = os.path.join(destination_dir, filename)
        member = self._contents_info[filename]
        with self._create_file(destination_path) as new:
            new.write(self._tar.extractfile(member))
        return destination_path

    def iter_extract(self, entries, destination_dir):
        # generate members from entries, same order as getmembers
        infos = []
        names = []
        for name, info in self._contents_info.items():
            if name in entries:
                infos.append(info)
                names.append(name)
        self._tar.extractall(path=destination_dir, members=infos)
        for name, info in zip(names, infos):
            self._rename_in_dir(info.name, name, destination_dir)
        yield from names

    def close(self):
        self._tar.close()

# vim: expandtab:sw=4:ts=4

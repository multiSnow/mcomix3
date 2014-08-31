# -*- coding: utf-8 -*-

""" Class for transparently handling an archive containing sub-archives. """

from mcomix.archive import archive_base
from mcomix import archive_tools
from mcomix import log

import os

class RecursiveArchive(archive_base.BaseArchive):

    def __init__(self, archive, destination_dir):
        self._main_archive = archive
        self._destination_dir = destination_dir
        self._archive_list = []
        # Map entry name to its archive+name.
        self._entry_mapping = {}
        # Map archive to its root.
        self._archive_root = {}
        self._contents_listed = False
        self._contents = []
        # Assume concurrent extractions are not supported.
        self.support_concurrent_extractions = False

    def _iter_contents(self, archive, root=None):
        self._archive_list.append(archive)
        self._archive_root[archive] = root
        supported_archive_regexp = archive_tools.get_supported_archive_regex()
        sub_archive_list = []
        for f in archive.iter_contents():
            if supported_archive_regexp.search(f):
                # We found a sub-archive, don't try to extract it now, as we
                # must finish listing the containing archive contents before
                # any extraction can be done.
                sub_archive_list.append(f)
                continue
            name = f
            if root is not None:
                name = os.path.join(root, name)
            self._entry_mapping[name] = (archive, f)
            yield name
        for f in sub_archive_list:
            # Extract sub-archive.
            destination_dir = self._destination_dir
            if root is not None:
                destination_dir = os.path.join(destination_dir, root)
            archive.extract(f, destination_dir)
            sub_archive_ext = os.path.splitext(f)[1].lower()[1:]
            sub_archive_path = os.path.join(
                self._destination_dir, 'sub-archives',
                '%04u.%s' % (len(self._archive_list), sub_archive_ext
            ))
            self._create_directory(os.path.dirname(sub_archive_path))
            os.rename(os.path.join(destination_dir, f), sub_archive_path)
            # And open it and list its contents.
            sub_archive = archive_tools.get_archive_handler(sub_archive_path)
            if sub_archive is None:
                log.warning('Non-supported archive format: %s' %
                            os.path.basename(sub_archive_path))
                continue
            sub_root = f
            if root is not None:
                sub_root = os.path.join(root, sub_root)
            for name in self._iter_contents(sub_archive, sub_root):
                yield name

    def _check_concurrent_extraction_support(self):
        supported = True
        # We need all archives to support concurrent extractions.
        for archive in self._archive_list:
            if not archive.support_concurrent_extractions:
                supported = False
                break
        self.support_concurrent_extractions = supported

    def iter_contents(self):
        if self._contents_listed:
            for f in self._contents:
                yield f
            return
        self._contents = []
        for f in self._iter_contents(self._main_archive):
            self._contents.append(f)
            yield f
        self._contents_listed = True
        # We can now check if concurrent extractions are really supported.
        self._check_concurrent_extraction_support()

    def list_contents(self):
        if self._contents_listed:
            return self._contents
        return [f for f in self.iter_contents()]

    def extract(self, filename, destination_dir):
        if not self._contents_listed:
            self.list_contents()
        archive, name = self._entry_mapping[filename]
        root = self._archive_root[archive]
        if root is not None:
            destination_dir = os.path.join(destination_dir, root)
        log.debug('extracting from %s to %s: %s',
                  archive.archive, destination_dir, filename)
        archive.extract(name, destination_dir)

    def iter_extract(self, entries, destination_dir):
        if not self._contents_listed:
            self.list_contents()
        # Unfortunately we can't just rely on BaseArchive default
        # implementation if solid archives are to be correctly supported:
        # we need to call iter_extract (not extract) for each archive ourselves.
        wanted = set(entries)
        for archive in self._archive_list:
            archive_wanted = {}
            for name in wanted:
                name_archive, name_archive_name = self._entry_mapping[name]
                if name_archive == archive:
                    archive_wanted[name_archive_name] = name
            if 0 == len(archive_wanted):
                continue
            root = self._archive_root[archive]
            archive_destination_dir = destination_dir
            if root is not None:
                archive_destination_dir = os.path.join(destination_dir, root)
            log.debug('extracting from %s to %s: %s',
                      archive.archive, archive_destination_dir,
                      ' '.join(archive_wanted.keys()))
            for f in archive.iter_extract(archive_wanted.keys(), archive_destination_dir):
                yield archive_wanted[f]
            wanted -= set(archive_wanted.values())
            if 0 == len(wanted):
                break

    def is_solid(self):
        if not self._contents_listed:
            self.list_contents()
        # We're solid if at least one archive is solid.
        for archive in self._archive_list:
            if archive.is_solid():
                return True
        return False

    def close(self):
        for archive in self._archive_list:
            archive.close()


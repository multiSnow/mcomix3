# -*- coding: utf-8 -*-

""" 7z archive extractor. """

import os
import sys
import tempfile

from mcomix import process
from mcomix.archive import archive_base

# Filled on-demand by SevenZipArchive
_7z_executable = -1

class SevenZipArchive(archive_base.ExternalExecutableArchive):
    """ 7z file extractor using the 7z executable. """

    STATE_HEADER, STATE_LISTING, STATE_FOOTER = 1, 2, 3

    def __init__(self, archive):
        super(SevenZipArchive, self).__init__(archive)

        self._is_solid = False
        #: Indicates which part of the file listing has been read
        self._state = SevenZipArchive.STATE_HEADER
        self._contents = []
        #: Current path while listing contents
        self._path = None

    def _get_executable(self):
        return SevenZipArchive._find_7z_executable()

    def _get_list_arguments(self):
        args = [u'l', u'-slt', u'-p']
        if sys.platform == 'win32':
            args.append(u'-sccUTF-8')
        args.append(u'--')
        return args

    def _parse_list_output_line(self, line):
        """ Start parsing after the first delimiter (bunch of - characters),
        and end when delimiters appear again. Format:
        Date <space> Time <space> Attr <space> Size <space> Compressed <space> Name"""
        line = line.decode('UTF-8')
        if line.startswith('----'):
            if self._state == SevenZipArchive.STATE_HEADER:
                # First delimiter reached, start reading from next line
                self._state = SevenZipArchive.STATE_LISTING
            elif self._state == SevenZipArchive.STATE_LISTING:
                # Last delimiter read, stop reading from now on
                self._state = SevenZipArchive.STATE_FOOTER

            return None

        if self._state == SevenZipArchive.STATE_HEADER:
            if 'Solid = +' == line:
                self._is_solid = True

        if self._state == SevenZipArchive.STATE_LISTING:
            if line.startswith('Path = '):
                self._path = line[7:]
                return self._path
            if line.startswith('Size ='):
                self._contents.append((self._path, int(line[7:])))

        return None

    def is_solid(self):
        return self._is_solid

    def extract(self, filename, destination_dir):
        """ Extract <filename> from the archive to <destination_dir>. """
        assert isinstance(filename, unicode) and \
                isinstance(destination_dir, unicode)

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        tmplistfile = tempfile.NamedTemporaryFile(prefix='mcomix.7z.', delete=False)
        try:
            tmplistfile.write(self._original_filename(filename).encode('UTF-8') + os.linesep)
            tmplistfile.close()
            proc = process.Process([self._get_executable(),
                                    u'x', u'-so', u'-p',
                                    u'-i@' + tmplistfile.name,
                                    u'--', self.archive])
            fd = proc.spawn()

            if fd:
                # Create new file
                new = self._create_file(os.path.join(destination_dir, filename))
                stdout, stderr = proc.communicate()
                new.write(stdout)
                new.close()

                # Wait for process to finish
                fd.close()
                proc.wait()
        finally:
            os.unlink(tmplistfile.name)

    def extract_all(self, entries, destination_dir, callback):

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        proc = process.Process([self._get_executable(),
                                u'x', u'-so', u'-p',
                                u'--', self.archive])
        fd = proc.spawn(stdin=process.NULL)
        if not fd:
            return

        wanted = dict([(self._original_filename(unicode_name), unicode_name)
                       for unicode_name in entries])

        for filename, filesize in self._contents:
            data = fd.read(filesize)
            if filename not in wanted:
                continue
            unicode_name = wanted.get(filename, None)
            if unicode_name is None:
                continue
            new = self._create_file(os.path.join(destination_dir, unicode_name))
            new.write(data)
            new.close()
            if not callback(unicode_name):
                break
            del wanted[filename]
            if 0 == len(wanted):
                break

        # Wait for process to finish
        fd.close()
        proc.wait()

    @staticmethod
    def _find_7z_executable():
        """ Tries to start 7z, and returns either '7z' if
        it was started successfully or None otherwise. """
        global _7z_executable
        if _7z_executable != -1:
            return _7z_executable
        else:
            proc = process.Process([u'7z'])
            fd = proc.spawn()
            if fd is not None:
                fd.close()
                _7z_executable = u'7z'
                return u'7z'
            else:
                _7z_executable = None
                return None

    @staticmethod
    def is_available():
        return bool(SevenZipArchive._find_7z_executable())


# vim: expandtab:sw=4:ts=4

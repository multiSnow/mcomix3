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
            args.append(u'-sccUTF-8')  # This switch is only supported on Win32
        args.append(u'--')
        return args

    def _parse_list_output_line(self, line):
        """ Start parsing after the first delimiter (bunch of - characters),
        and end when delimiters appear again. Format:
        Date <space> Time <space> Attr <space> Size <space> Compressed <space> Name"""

        # Encoding is only guaranteed on win32 due to the -scc switch
        if sys.platform == 'win32':
            line = line.decode('utf-8')

        if line.startswith('----------'):
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
                filesize = int(line[7:])
                if filesize > 0:
                    self._contents.append((self._path, filesize))

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
            desired_filename = self._original_filename(filename)
            if isinstance(desired_filename, unicode):
                desired_filename = desired_filename.encode('utf-8')

            tmplistfile.write(desired_filename + os.linesep)
            tmplistfile.close()

            output = self._create_file(os.path.join(destination_dir, filename))
            try:
                process.call([self._get_executable(),
                              u'x', u'-so', u'-p',
                              u'-i@' + tmplistfile.name,
                              u'--', self.archive],
                             stdout=output)
            finally:
                output.close()
        finally:
            os.unlink(tmplistfile.name)

    def iter_extract(self, entries, destination_dir):

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        proc = process.popen([self._get_executable(),
                             u'x', u'-so', u'-p',
                             u'--', self.archive])
        try:
            wanted = dict([(self._original_filename(unicode_name), unicode_name)
                           for unicode_name in entries])

            for filename, filesize in self._contents:
                data = proc.stdout.read(filesize)
                if filename not in wanted:
                    continue
                unicode_name = wanted.get(filename, None)
                if unicode_name is None:
                    continue
                new = self._create_file(os.path.join(destination_dir, unicode_name))
                new.write(data)
                new.close()
                yield unicode_name
                del wanted[filename]
                if 0 == len(wanted):
                    break

        finally:
            proc.stdout.close()
            proc.wait()

    @staticmethod
    def _find_7z_executable():
        """ Tries to start 7z, and returns either '7z' if
        it was started successfully or None otherwise. """
        global _7z_executable
        if _7z_executable != -1:
            return _7z_executable
        _7z_executable = u'7z'
        try:
            process.call([_7z_executable])
        except:
            _7z_executable = None
        return _7z_executable

    @staticmethod
    def is_available():
        return bool(SevenZipArchive._find_7z_executable())


# vim: expandtab:sw=4:ts=4

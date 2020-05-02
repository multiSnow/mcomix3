''' PackARC archive extractor. '''

import re
import os

from mcomix import process
from mcomix.archive import archive_base

class PackARCArchive(archive_base.ExternalExecutableArchive):
    ''' PackARC file extractor using the packARC executable. '''
    def _get_executable(self):
        return PackARCArchive._find_packarc_executable()

    def _get_list_arguments(self):
        return ['l', '-sl', '-q']

    def _get_extract_arguments(self):
        return ['x', '-o', '-q']

    def _parse_list_output_line(self, line):
        workline = line.rstrip()
        if not (re.match(br'<PJA v\d.\d+ ARCHIVE ".*">$', workline)
                or re.match(b'-+$', workline)
                or re.match(br'TOTAL \d+ FILES, \d+kb COMPRESSED TO \d+kb (\d+.\d+%)$', workline)):
            return workline

    def iter_contents(self):
        executable = self._get_executable()
        if not executable:
            return
        arguments = self._get_list_arguments()
        with process.popen([executable] + arguments + [self.archive]) as proc:
            yield from (filename.rstrip().decode() for filename in proc.stdout
                        if self._parse_list_output_line(filename))
        self.filenames_initialized = True

    def extract(self, filename, destination_dir):
        self._create_directory(destination_dir)
        process.call([self._get_executable()] +
                     self._get_extract_arguments() +
                     [self.archive, self._original_filename(filename)],
                     cwd=destination_dir)
        destination_path = os.path.join(destination_dir, filename)
        return destination_path

    @staticmethod
    def _find_packarc_executable():
        ''' Tries to start packARC, and returns one of the possibilities
        if it was started successfully or None otherwise. '''
        _packarc_executable = process.find_executable(
            ('packARC', 'packARC.lxe', 'packarc'))
        return _packarc_executable

    @staticmethod
    def is_available():
        return bool(PackARCArchive._find_packarc_executable())

    @staticmethod
    def test_if_archive(filename):
        "Test whether a particular file is a packARC archive."
        # Doing this test is not entirely trivial. A packARC file does not
        # contain a header, meaning that we need to process a file to check
        # if it is a valid archive. (We cannot rely on file extension alone).
        # We will try to list the contents of the archive and test for
        # success.
        executable = PackARCArchive._find_packarc_executable()
        return executable and process.call([executable, 'l', '-sl', filename])

# vim: expandtab:sw=4:ts=4

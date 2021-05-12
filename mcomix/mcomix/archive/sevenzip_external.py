# -*- coding: utf-8 -*-

''' 7z archive extractor. '''

import os
import sys
import tempfile

from mcomix import log
from mcomix import process
from mcomix.archive import archive_base

# Filled on-demand by SevenZipArchive
_7z_executable = {}

def _has_rar_so():
    if not (_7z:=SevenZipArchive._find_7z_executable()):
        return False
    if sys.platform=='win32':
        # assume 7z in windows already support rar
        return True
    with process.popen((_7z,'i'),universal_newlines=True) as proc:
        lines=proc.stdout.read().splitlines()
        try:
            del lines[:lines.index('Libs:')+1]
            del lines[lines.index(''):]
        except ValueError:
            # no library found
            return False
        for line in lines:
            if line.endswith('/Rar.so'):
                return True
    return False

def is_7z_support_rar():
    '''Check whether p7zip has Rar.so, which is needed to Rar format'''
    if 'support_rar' not in _7z_executable:
        _7z_executable['support_rar'] = _has_rar_so()
        if _7z_executable['support_rar']:
            log.debug('rar format supported by 7z')
        else:
            log.debug('rar format not supported by 7z')
    return _7z_executable['support_rar']

class SevenZipArchive(archive_base.ExternalExecutableArchive):
    ''' 7z file extractor using the 7z executable. '''

    STATE_HEADER, STATE_LISTING, STATE_FOOTER = 1, 2, 3

    class EncryptedHeader(Exception):
        pass

    def __init__(self, archive):
        super(SevenZipArchive, self).__init__(archive)
        self._is_solid = False
        self._contents = []

        self.is_encrypted = False
        self.is_encrypted = self._has_encryption()

    def _get_executable(self):
        return SevenZipArchive._find_7z_executable()

    def _get_password_argument(self):
        if self.is_encrypted:
            self._get_password()
            return '-p' + self._password
        else:
            # Add an empty password anyway, to prevent deadlock on reading for
            # input if we did not correctly detect the archive is encrypted.
            return '-p'

    def _get_list_arguments(self):
        args = [self._get_executable(), 'l', '-slt']
        if sys.platform == 'win32':
            # This switch is only supported on Win32.
            args.append('-sccUTF-8')
        args.append(self._get_password_argument())
        args.extend(('--', self.archive))
        return args

    def _get_extract_arguments(self, list_file=None):
        args = [self._get_executable(), 'x', '-so']
        if list_file is not None:
            args.append('-i@' + list_file)
        args.append(self._get_password_argument())
        args.extend(('--', self.archive))
        return args

    def _parse_list_output_line(self, line):
        ''' Start parsing after the first delimiter (bunch of - characters),
        and end when delimiters appear again. Format:
        Date <space> Time <space> Attr <space> Size <space> Compressed <space> Name'''

        # Encoding is only guaranteed on win32 due to the -scc switch.
        if sys.platform == 'win32':
            line = line.decode('utf-8')

        if line.startswith('----------'):
            if self._state == self.STATE_HEADER:
                # First delimiter reached, start reading from next line.
                self._state = self.STATE_LISTING
            elif self._state == self.STATE_LISTING:
                # Last delimiter read, stop reading from now on.
                self._state = self.STATE_FOOTER

            return None

        if self._state == self.STATE_HEADER:
            if (line.startswith('Error:') or line.startswith('ERROR:')) and \
               line.endswith(': Can not open encrypted archive. Wrong password?'):
                raise self.EncryptedHeader()
            if 'Solid = +' == line:
                self._is_solid = True

        if self._state == self.STATE_LISTING:
            if line.startswith('Path = '):
                self._path = line[7:]
                return self._path
            if line.startswith('Size = '):
                filesize = int(line[7:])
                if filesize > 0:
                    self._contents.append((self._path, filesize))

        return None

    def _has_encryption(self):
        with process.popen(self._get_list_arguments(),
                           stderr=process.STDOUT,
                           universal_newlines=True) as proc:
            for line in proc.stdout:
                if line.startswith('Encrypted = +'):
                    return True
                if 'Can not open encrypted archive. Wrong password' in line:
                    return True
        return False

    def is_solid(self):
        return self._is_solid

    def iter_contents(self):
        if not self._get_executable():
            return

        # We'll try at most 2 times:
        # - the first time without a password
        # - a second time with a password if the header is encrypted
        for retry_count in range(2):
            #: Indicates which part of the file listing has been read.
            self._state = self.STATE_HEADER
            #: Current path while listing contents.
            self._path = None
            with process.popen(self._get_list_arguments(), stderr=process.STDOUT, universal_newlines=True) as proc:
                try:
                    for line in proc.stdout:
                        filename = self._parse_list_output_line(line.rstrip(os.linesep))
                        if filename is not None:
                            yield self._unicode_filename(filename)
                except self.EncryptedHeader:
                    # The header is encrypted, try again
                    # if it was our first attempt.
                    if 0 == retry_count:
                        continue
            break

        self.filenames_initialized = True

    def extract(self, filename, destination_dir):
        ''' Extract <filename> from the archive to <destination_dir>. '''
        assert isinstance(filename, str) and \
                isinstance(destination_dir, str)

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        destination_path = os.path.join(destination_dir, filename)
        with tempfile.NamedTemporaryFile(mode='wt', prefix='mcomix.7z.') as tmplistfile:
            desired_filename = self._original_filename(filename)
            tmplistfile.write(desired_filename + os.linesep)
            tmplistfile.flush()
            with self._create_file(destination_path) as output:
                process.call(self._get_extract_arguments(list_file=tmplistfile.name),
                             stdout=output)
        return destination_path

    def iter_extract(self, entries, destination_dir):

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        with process.popen(self._get_extract_arguments()) as proc:
            wanted = dict([(self._original_filename(unicode_name), unicode_name)
                           for unicode_name in entries])

            for filename, filesize in self._contents:
                data = proc.stdout.read(filesize)
                if filename not in wanted:
                    continue
                unicode_name = wanted.get(filename, None)
                if unicode_name is None:
                    continue
                with self._create_file(os.path.join(destination_dir, unicode_name)) as new:
                    new.write(data)
                yield unicode_name
                del wanted[filename]
                if 0 == len(wanted):
                    break

    @staticmethod
    def _find_7z_executable():
        ''' Tries to start 7z, and returns either '7z' if
        it was started successfully or None otherwise. '''
        if 'path' not in _7z_executable:
            _7z_executable['path'] = process.find_executable(('7z',))
        return _7z_executable['path']

    @staticmethod
    def is_available():
        return bool(SevenZipArchive._find_7z_executable())

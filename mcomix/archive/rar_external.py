# -*- coding: utf-8 -*-

""" RAR archive extractor. """

import os
import sys

from mcomix import log
from mcomix import process
from mcomix.archive import archive_base

# Filled on-demand by RarArchive
_rar_executable = -1

class RarArchive(archive_base.ExternalExecutableArchive):
    """ RAR file extractor using the unrar/rar executable. """

    STATE_HEADER, STATE_LISTING = 1, 2

    class EncryptedHeader(Exception):
        pass

    def __init__(self, archive):
        super(RarArchive, self).__init__(archive)
        self._is_solid = False
        self._is_encrypted =  False
        self._contents = []

    def _get_executable(self):
        return self._find_unrar_executable()

    def _get_password_argument(self):
        if not self._is_encrypted:
            # Add a dummy password anyway, to prevent deadlock on reading for
            # input if we did not correctly detect the archive is encrypted.
            return u'-p-'
        self._get_password()
        # Check for invalid empty password, see comment above.
        if not self._password:
            return u'-p-'
        return u'-p' + self._password

    def _get_list_arguments(self):
        args = [self._get_executable(), u'vt']
        args.append(self._get_password_argument())
        args.extend((u'--', self.archive))
        return args

    def _get_extract_arguments(self):
        args = [self._get_executable(), u'p', u'-inul', u'-@']
        args.append(self._get_password_argument())
        args.extend((u'--', self.archive))
        return args

    def _parse_list_output_line(self, line):
        if self._state == self.STATE_HEADER:
            if line.startswith('Details: '):
                flags = line[9:].split(', ')
                if 'solid' in flags:
                    self._is_solid = True
                if 'encrypted headers' in flags:
                    if not self._is_encrypted:
                        # Trigger a restart of the enclosing
                        # iter_contents loop with a password.
                        self._is_encrypted = True
                        raise self.EncryptedHeader()
                self._state = self.STATE_LISTING
                return None
        if self._state == self.STATE_LISTING:
            line = line.lstrip()
            if line.startswith('Name: '):
                self._path = line[6:]
                return self._path
            if line.startswith('Size: '):
                filesize = int(line[6:])
                if filesize > 0:
                    self._contents.append((self._path, filesize))
            if line.startswith('Flags: '):
                flags = line[7:].split()
                if 'solid' in flags:
                    self._is_solid = True
                if 'encrypted' in flags:
                    self._is_encrypted = True
        return None

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
            proc = process.popen(self._get_list_arguments(), stderr=process.STDOUT)
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
            finally:
                proc.stdout.close()
                proc.wait()
            # Last and/or successful attempt.
            break

        self.filenames_initialized = True

    def extract(self, filename, destination_dir):
        """ Extract <filename> from the archive to <destination_dir>. """
        assert isinstance(filename, unicode) and \
                isinstance(destination_dir, unicode)

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        desired_filename = self._original_filename(filename)
        cmd = self._get_extract_arguments() + [desired_filename]
        output = self._create_file(os.path.join(destination_dir, filename))
        try:
            process.call(cmd, stdout=output)
        finally:
            output.close()

    def iter_extract(self, entries, destination_dir):

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        proc = process.popen(self._get_extract_arguments())
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
    def _find_unrar_executable():
        """ Tries to start rar/unrar, and returns either 'rar' or 'unrar' if
        one of them was started successfully.
        Returns None if neither could be started. """
        global _rar_executable
        if _rar_executable == -1:
            if 'win32' == sys.platform:
                is_not_unrar_free = lambda exe: True
            else:
                def is_not_unrar_free(exe):
                    real_exe = exe
                    while os.path.islink(real_exe):
                          real_exe = os.readlink(real_exe)
                    if real_exe.endswith(os.path.sep + 'unrar-free'):
                        log.warning('RAR executable %s is unrar-free, ignoring', exe)
                        return False
                    return True
            _rar_executable = process.find_executable((u'unrar-nonfree', u'unrar', u'rar'),
                                                      is_valid_candidate=is_not_unrar_free)
        return _rar_executable

    @staticmethod
    def is_available():
        return bool(RarArchive._find_unrar_executable())

# vim: expandtab:sw=4:ts=4

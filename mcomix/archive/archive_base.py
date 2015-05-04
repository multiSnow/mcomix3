# -*- coding: utf-8 -*-

""" Base class for unified handling of various archive formats. Used for simplifying
extraction and adding new archive formats. """

import os
import errno
import threading

from mcomix import portability
from mcomix import i18n
from mcomix import process
from mcomix import callback
from mcomix import archive

class BaseArchive(object):
    """ Base archive interface. All filenames passed from and into archives
    are expected to be Unicode objects. Archive files are converted to
    Unicode with some guess-work. """

    """ True if concurrent calls to extract is supported. """
    support_concurrent_extractions = False

    def __init__(self, archive):
        assert isinstance(archive, unicode), "File should be an Unicode string."

        self.archive = archive
        self._password = None
        self._event = threading.Event()
        if self.support_concurrent_extractions:
            # When multiple concurrent extractions are supported,
            # we need a lock to handle concurent calls to _get_password.
            self._lock = threading.Lock()
            self._waiting_for_password = False

    def iter_contents(self):
        """ Generator for listing the archive contents.
        """
        return
        yield

    def list_contents(self):
        """ Returns a list of unicode filenames relative to the archive root.
        These names do not necessarily exist in the actual archive since they
        need to saveable on the local filesystems, so some characters might
        need to be replaced. """

        return [f for f in self.iter_contents()]

    def extract(self, filename, destination_dir):
        """ Extracts the file specified by <filename>. This filename must
        be obtained by calling list_contents(). The file is saved to
        <destination_dir>. """

        assert isinstance(filename, unicode) and \
            isinstance(destination_dir, unicode)

    def iter_extract(self, entries, destination_dir):
        """ Generator to extract <entries> from archive to <destination_dir>. """
        wanted = set(entries)
        for filename in self.iter_contents():
            if not filename in wanted:
                continue
            self.extract(filename, destination_dir)
            yield filename
            wanted.remove(filename)
            if 0 == len(wanted):
                break

    def close(self):
        """ Closes the archive and releases held resources. """

        pass

    def is_solid(self):
        """ Returns True if the archive is solid and extraction should be done
        in one pass. """
        return False

    def _replace_invalid_filesystem_chars(self, filename):
        """ Replaces characters in <filename> that cannot be saved to the disk
        with underscore and returns the cleaned-up name. """

        unsafe_chars = portability.invalid_filesystem_chars()
        translation_table = {}
        replacement_char = u'_'
        for char in unsafe_chars:
            translation_table[ord(char)] = replacement_char

        new_name = filename.translate(translation_table)

        # Make sure the filename does not contain portions that might
        # traverse directories, i.e. do not allow absolute paths
        # and paths containing ../
        normalized = os.path.normpath(new_name)
        return normalized.lstrip('..' + os.sep).lstrip(os.sep)

    def _create_directory(self, directory):
        """ Recursively create a directory if it doesn't exist yet. """
        if os.path.exists(directory):
            return
        try:
            os.makedirs(directory)
        except OSError, e:
            # Can happen with concurrent calls.
            if e.errno != errno.EEXIST:
                raise e

    def _create_file(self, dst_path):
        """ Open <dst_path> for writing, making sure base directory exists. """
        dst_dir = os.path.dirname(dst_path)
        # Create directory if it doesn't exist
        self._create_directory(dst_dir)
        return open(dst_path, 'wb')

    @callback.Callback
    def _password_required(self):
        """ Asks the user for a password and sets <self._password>.
        If <self._password> is None, no password has been requested yet.
        If an empty string is set, assume that the user did not provide
        a password. """

        password = archive.ask_for_password(self.archive)
        if password is None:
            password = ""

        self._password = password
        self._event.set()

    def _get_password(self):
        ask_for_password = self._password is None
        # Don't trigger concurrent password dialogs.
        if ask_for_password and self.support_concurrent_extractions:
            with self._lock:
                if self._waiting_for_password:
                    ask_for_password = False
                else:
                    self._waiting_for_password = True
        if ask_for_password:
            self._password_required()
        self._event.wait()

class NonUnicodeArchive(BaseArchive):
    """ Base class for archives that manage a conversion of byte member names ->
    Unicode member names internally. Required for formats that do not provide
    wide character member names. """

    def __init__(self, archive):
        super(NonUnicodeArchive, self).__init__(archive)
        # Maps Unicode names to regular names as expected by the original archive format
        self.unicode_mapping = {}

    def _unicode_filename(self, filename, conversion_func=i18n.to_unicode):
        """ Instead of returning archive members directly, map each filename through
        this function first to convert them to Unicode. """

        unicode_name = conversion_func(filename)
        safe_name = self._replace_invalid_filesystem_chars(unicode_name)
        self.unicode_mapping[safe_name] = filename
        return safe_name

    def _original_filename(self, filename):
        """ Map Unicode filename back to original archive name. """
        if filename in self.unicode_mapping:
            return self.unicode_mapping[filename]
        else:
            return i18n.to_utf8(filename)

class ExternalExecutableArchive(NonUnicodeArchive):
    """ For archives that are extracted by spawning an external
    application. """

    # Since we're using an external program for extraction,
    # concurrent calls are supported.
    support_concurrent_extractions = True

    def __init__(self, archive):
        super(ExternalExecutableArchive, self).__init__(archive)
        # Flag to determine if list_contents() has been called
        # This builds the Unicode mapping and is likely required
        # for extracting filenames that have been internally mapped.
        self.filenames_initialized = False

    def _get_executable(self):
        """ Returns the executable's name or path. Return None if no executable
        was found on the system. """
        raise NotImplementedError("Subclasses must override _get_executable.")

    def _get_list_arguments(self):
        """ Returns an array of arguments required for the executable
        to produce a list of archive members. """
        raise NotImplementedError("Subclasses must override _get_list_arguments.")

    def _get_extract_arguments(self):
        """ Returns an array of arguments required for the executable
        to extract a file to STDOUT. """
        raise NotImplementedError("Subclasses must override _get_extract_arguments.")

    def _parse_list_output_line(self, line):
        """ Parses the output of the external executable's list command
        and return either a file path relative to the archive's root,
        or None if the current line doesn't contain any file references. """

        return line

    def iter_contents(self):
        if not self._get_executable():
            return

        proc = process.popen([self._get_executable()] +
                             self._get_list_arguments() +
                             [self.archive])
        try:
            for line in proc.stdout:
                filename = self._parse_list_output_line(line.rstrip(os.linesep))
                if filename is not None:
                    yield self._unicode_filename(filename)
        finally:
            proc.stdout.close()
            proc.wait()

        self.filenames_initialized = True

    def extract(self, filename, destination_dir):
        """ Extract <filename> from the archive to <destination_dir>. """
        assert isinstance(filename, unicode) and \
                isinstance(destination_dir, unicode)

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        output = self._create_file(os.path.join(destination_dir, filename))
        try:
            process.call([self._get_executable()] +
                         self._get_extract_arguments() +
                         [self.archive, self._original_filename(filename)],
                         stdout=output)
        finally:
            output.close()

# vim: expandtab:sw=4:ts=4

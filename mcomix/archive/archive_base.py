# -*- coding: utf-8 -*-

""" Base class for unified handling of various archive formats. Used for simplifying
extraction and adding new archive formats. """

import os
from mcomix import portability
from mcomix import i18n
from mcomix import process
from mcomix import callback
from mcomix import archive

class BaseArchive(object):
    """ Base archive interface. All filenames passed from and into archives
    are expected to be Unicode objects. Archive files are converted to
    Unicode with some guess-work. """

    def __init__(self, archive):
        assert isinstance(archive, unicode), "File should be an Unicode string."

        self.archive = archive
        self._password = None

    def list_contents(self):
        """ Returns a list of unicode filenames relative to the archive root.
        These names do not necessarily exist in the actual archive since they
        need to saveable on the local filesystems, so some characters might
        need to be replaced. """

        return []

    def extract(self, filename, destination_path):
        """ Extracts the file specified by <filename>. This filename must
        be obtained by calling list_contents(). The file is saved to
        <destination_path>, which includes both target path and filename. """

        assert isinstance(filename, unicode) and \
            isinstance(destination_path, unicode)

    def close(self):
        """ Closes the archive and releases held resources. """

        pass

    def _replace_invalid_filesystem_chars(self, filename):
        """ Replaces characters in <filename> that cannot be saved to the disk
        with underscore and returns the cleaned-up name. """

        unsafe_chars = portability.invalid_filesystem_chars()
        translation_table = {}
        replacement_char = u'_'
        for char in unsafe_chars:
            translation_table[ord(char)] = replacement_char

        return filename.translate(translation_table)

    def _create_directory(self, directory):
        """ Recursively create a directory if it doesn't exist yet. """
        if not os.path.exists(directory):
            os.makedirs(directory)

    @callback.Callback
    def _password_required(self, event):
        """ Asks the user for a password and sets <self._password>.
        If <self._password> is None, no password has been requested yet.
        If an empty string is set, assume that the user did not provide
        a password. """

        password = archive.ask_for_password()
        if password is None:
            password = ""

        self._password = password
        event.set()

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

    def __init__(self, archive):
        super(ExternalExecutableArchive, self).__init__(archive)
        # Flag to determine if list_contents() has been called
        # This builds the Unicode mapping and is likely required
        # for extracting filenames that have been internally mapped.
        self.filenames_initialized = False

    def _get_executable(self):
        """ Returns the executable's name or path. Return None if no executable
        was found on the system. """
        raise NotImplementedError("Subclasses must override this method.")

    def _get_list_arguments(self):
        """ Returns an array of arguments required for the executable
        to produce a list of archive members. """
        raise NotImplementedError("Subclasses must override this method.")

    def _get_extract_arguments(self):
        """ Returns an array of arguments required for the executable
        to extract a file to STDOUT. """
        raise NotImplementedError("Subclasses must override this method.")

    def _parse_list_output_line(self, line):
        """ Parses the output of the external executable's list command
        and return either a file path relative to the archive's root,
        or None if the current line doesn't contain any file references. """

        return line

    def list_contents(self):
        if not self._get_executable():
            return []

        proc = process.Process([self._get_executable()] +
            self._get_list_arguments() +
            [self.archive])
        fd = proc.spawn()

        filenames = [ ]
        for line in fd.readlines():
            filename = self._parse_list_output_line(line.rstrip(os.linesep))
            if filename is not None:
                filenames.append(self._unicode_filename(filename))

        fd.close()
        proc.wait()

        self.filenames_initialized = True
        return filenames

    def extract(self, filename, destination_path):
        """ Extract <filename> from the archive to <destination_path>.
        This path should include the full filename. """
        assert isinstance(filename, unicode) and isinstance(destination_path, unicode)

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        # Create directory if it doesn't exist
        destination_dir = os.path.split(destination_path)[0]
        self._create_directory(destination_dir)
        proc = process.Process([self._get_executable()] +
            self._get_extract_arguments() +
            [self.archive, self._original_filename(filename)])
        fd = proc.spawn()

        if fd:
            # Create new file
            new = open(destination_path, 'wb')
            stdout, stderr = proc.communicate()
            new.write(stdout)
            new.close()

            # Wait for process to finish
            fd.close()
            proc.wait()

# vim: expandtab:sw=4:ts=4

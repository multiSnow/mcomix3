# -*- coding: utf-8 -*-

""" ZIP archive extractor via executable."""

from mcomix import i18n
from mcomix import process
from mcomix.archive import archive_base

# Filled on-demand by ZipArchive
_zip_executable = -1

class ZipArchive(archive_base.ExternalExecutableArchive):
    """ ZIP file extractor using unzip executable. """

    def _get_executable(self):
        return ZipArchive._find_unzip_executable()

    def _get_list_arguments(self):
        return [u'-Z1']

    def _get_extract_arguments(self):
        return [u'-p', u'-P', u'']

    @staticmethod
    def _find_unzip_executable():
        """ Tries to run unzip, and returns 'unzip' on success.
        Returns None on failure. """
        global _zip_executable
        if -1 == _zip_executable:
            _zip_executable = process.find_executable((u'unzip',))
        return _zip_executable

    @staticmethod
    def is_available():
        return bool(ZipArchive._find_unzip_executable())

    def _unicode_filename(self, filename, conversion_func=i18n.to_unicode):
        unicode_name = conversion_func(filename)
        safe_name = self._replace_invalid_filesystem_chars(unicode_name)
        # As it turns out, unzip will try to interpret filenames as glob...
        for c in '[*?':
            filename = filename.replace(c, '[' + c + ']')
        # Won't work on Windows...
        filename = filename.replace('\\', '\\\\')
        self.unicode_mapping[safe_name] = filename
        return safe_name

# vim: expandtab:sw=4:ts=4

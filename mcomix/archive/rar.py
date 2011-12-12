# -*- coding: utf-8 -*-

""" RAR archive extractor. """

from mcomix import process
from mcomix.archive import archive_base
from mcomix.archive import rarfile

# Filled on-demand by RarExecArchive
_rar_executable = -1

class RarExecArchive(archive_base.ExternalExecutableArchive):
    """ RAR file extractor using the unrar/rar executable. """

    def _get_executable(self):
        return RarExecArchive._find_unrar_executable()

    def _get_list_arguments(self):
        return [u'vb', u'-p-', u'--']

    def _get_extract_arguments(self):
        return [u'p', u'-inul', u'-p-', u'--']

    @staticmethod
    def _find_unrar_executable():
        """ Tries to start rar/unrar, and returns either 'rar' or 'unrar' if
        one of them was started successfully.
        Returns None if neither could be started. """
        global _rar_executable
        if _rar_executable != -1:
            return _rar_executable
        else:
            for command in (u'unrar', u'rar'):
                proc = process.Process([command])
                fd = proc.spawn()
                if fd is not None:
                    fd.close()
                    _rar_executable = command
                    return command

            _rar_executable = None
            return None

    @staticmethod
    def is_available():
        return bool(RarExecArchive._find_unrar_executable())

if rarfile.UnrarDll.is_available():
    RarArchive = rarfile.UnrarDll
else:
    RarArchive = RarExecArchive

# vim: expandtab:sw=4:ts=4

# -*- encoding: utf-8 -*-

""" RAR archive extractor. """

import process
import archive_base

class RarExecArchive(archive_base.ExternalExecutableArchive):
    """ RAR file extractor using the unrar/rar executable. """

    def _get_executable(self):
        return _executable

    def _get_list_arguments(self):
        return [u'vb', u'--']

    def _get_extract_arguments(self):
        return [u'p', u'-inul', u'-p-', u'--']

    @staticmethod
    def _find_unrar_executable():
        """ Tries to start rar/unrar, and returns either 'rar' or 'unrar' if
        one of them was started successfully.
        Returns None if neither could be started. """
        for command in (u'rar', u'unrar'):
            proc = process.Process([command])
            fd = proc.spawn()
            if fd is not None:
                fd.close()
                return command

        return None

_executable = RarExecArchive._find_unrar_executable()

# vim: expandtab:sw=4:ts=4

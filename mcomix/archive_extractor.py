"""archive_extractor.py - Archive extraction class."""
from __future__ import with_statement

import os
import threading

from mcomix import archive_tools
from mcomix import constants
from mcomix import callback
from mcomix import log
from mcomix.preferences import prefs
from mcomix.worker_thread import WorkerThread

class Extractor:

    """Extractor is a threaded class for extracting different archive formats.

    The Extractor can be loaded with paths to archives (currently ZIP, tar,
    or RAR archives) and a path to a destination directory. Once an archive
    has been set it is possible to filter out the files to be extracted and
    set the order in which they should be extracted. The extraction can
    then be started in a new thread in which files are extracted one by one,
    and a signal is sent on a condition after each extraction, so that it is
    possible for other threads to wait on specific files to be ready.

    Note: Support for gzip/bzip2 compressed tar archives is limited, see
    set_files() for more info.
    """

    def __init__(self):
        self._setupped = False

    def setup(self, src, dst, type=None):
        """Setup the extractor with archive <src> and destination dir <dst>.
        Return a threading.Condition related to the is_ready() method, or
        None if the format of <src> isn't supported.
        """
        self._src = src
        self._dst = dst
        self._type = type or archive_tools.archive_mime_type(src)
        self._files = []
        self._extracted = {}
        self._archive = archive_tools.get_archive_handler(src)
        if self._archive is None:
            msg = _('Non-supported archive format: %s') % os.path.basename(src)
            log.warning(msg)
            raise ArchiveException(msg)

        self._files = self._archive.list_contents()
        self._setupped = True
        self._started = False
        self._condition = threading.Condition()
        if self._archive.support_concurrent_extractions:
            max_threads = prefs['max extract threads']
        else:
            max_threads = 1
        self._extract_thread = WorkerThread(self._extract_file,
                                            max_threads=max_threads,
                                            unique_orders=True)
        return self._condition

    def get_files(self):
        """Return a list of names of all the files the extractor is currently
        set for extracting. After a call to setup() this is by default all
        files found in the archive. The paths in the list are relative to
        the archive root and are not absolute for the files once extracted.
        """
        with self._condition:
            return self._files[:]

    def get_directory(self):
        """Returns the root extraction directory of this extractor."""
        return self._dst

    def set_files(self, files):
        """Set the files that the extractor should extract from the archive in
        the order of extraction. Normally one would get the list of all files
        in the archive using get_files(), then filter and/or permute this
        list before sending it back using set_files().

        Note: Random access on gzip or bzip2 compressed tar archives is
        no good idea. These formats are supported *only* for backwards
        compability. They are fine formats for some purposes, but should
        not be used for scanned comic books. So, we cheat and ignore the
        ordering applied with this method on such archives.
        """
        with self._condition:
            if self._type in (constants.GZIP, constants.BZIP2):
                self._files = [x for x in self._files if x in files]
            else:
                self._files = files
            self._files = [f for f in files if f not in self._extracted]
            if self._started:
                self.extract()

    def is_ready(self, name):
        """Return True if the file <name> in the extractor's file list
        (as set by set_files()) is fully extracted.
        """
        with self._condition:
            return self._extracted.get(name, False)

    def get_mime_type(self):
        """Return the mime type name of the extractor's current archive."""
        return self._type

    def stop(self):
        """Signal the extractor to stop extracting and kill the extracting
        thread. Blocks until the extracting thread has terminated.
        """
        if self._setupped:
            self._extract_thread.stop()
            self.setupped = False
            self.started = False

    def extract(self):
        """Start extracting the files in the file list one by one using a
        new thread. Every time a new file is extracted a notify() will be
        signalled on the Condition that was returned by setup().
        """
        self._started = True
        self._extract_thread.clear_orders()
        self._extract_thread.extend_orders(self._files)

    @callback.Callback
    def file_extracted(self, extractor, filename):
        """ Called whenever a new file is extracted and ready. """
        pass

    def close(self):
        """Close any open file objects, need only be called manually if the
        extract() method isn't called.
        """
        self.stop()
        if self._archive:
            self._archive.close()

    def _extract_file(self, name):
        """Extract the file named <name> to the destination directory,
        mark the file as "ready", then signal a notify() on the Condition
        returned by setup().
        """

        try:
            dst_path = os.path.join(self._dst, name)
            log.debug(u'Extracting "%s" to "%s"', name, dst_path)
            self._archive.extract(name, dst_path)

        except Exception, ex:
            # Better to ignore any failed extractions (e.g. from a corrupt
            # archive) than to crash here and leave the main thread in a
            # possible infinite block. Damaged or missing files *should* be
            # handled gracefully by the main program anyway.
            log.error(_('! Extraction error: %s'), ex)

        with self._condition:
            self._files.remove(name)
            self._extracted[name] = True
            self._condition.notifyAll()
        self.file_extracted(self, name)

class ArchiveException(Exception):
    """ Indicate error during extraction operations. """
    pass

# vim: expandtab:sw=4:ts=4

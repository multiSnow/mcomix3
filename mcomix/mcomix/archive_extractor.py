'''archive_extractor.py - Archive extraction class.'''

import os
import threading
import traceback

from mcomix import archive_tools
from mcomix import callback
from mcomix import log
from mcomix.lib import mt
from mcomix.preferences import prefs

class Extractor(object):

    '''Extractor is a threaded class for extracting different archive formats.

    The Extractor can be loaded with paths to archives and a path to a
    destination directory. Once an archive has been set and its contents
    listed, it is possible to filter out the files to be extracted and set the
    order in which they should be extracted.  The extraction can then be
    started in a new thread in which files are extracted one by one, and a
    signal is sent on a condition after each extraction, so that it is possible
    for other threads to wait on specific files to be ready.

    Note: Support for gzip/bzip2 compressed tar archives is limited, see
    set_files() for more info.
    '''

    def __init__(self):
        self._setupped = False
        self._threadpool = mt.ThreadPool(
            name=self.__class__.__name__,
            processes=prefs['max extract threads'] or None)

    def setup(self, src, type=None):
        '''Setup the extractor with archive <src> and destination dir <dst>.
        Return a threading.Condition related to the is_ready() method, or
        None if the format of <src> isn't supported.
        '''
        self._src = src
        self._files = []
        self._extracted = set()
        self._archive = archive_tools.get_recursive_archive_handler(
            src, type=type, prefix='mcomix.extractor.')
        if self._archive is None:
            msg = _('Non-supported archive format: %s') % os.path.basename(src)
            log.warning(msg)
            raise ArchiveException(msg)

        self._dst = self._archive.destdir
        self._contents_listed = False
        self._extract_started = False
        self._condition = threading.Condition()
        self._threadpool.apply_async(
            self._list_contents,callback=self._list_contents_cb,
            error_callback=self._list_contents_errcb)
        self._setupped = True

        return self._condition

    def get_files(self):
        '''Return a list of names of all the files the extractor is currently
        set for extracting. After a call to setup() this is by default all
        files found in the archive. The paths in the list are relative to
        the archive root and are not absolute for the files once extracted.
        '''
        with self._condition:
            if not self._contents_listed:
                return
            return self._files[:]

    def get_directory(self):
        '''Returns the root extraction directory of this extractor.'''
        return self._dst

    def set_files(self, files):
        '''Set the files that the extractor should extract from the archive in
        the order of extraction. Normally one would get the list of all files
        in the archive using get_files(), then filter and/or permute this
        list before sending it back using set_files().

        Note: Random access on gzip or bzip2 compressed tar archives is
        no good idea. These formats are supported *only* for backwards
        compability. They are fine formats for some purposes, but should
        not be used for scanned comic books. So, we cheat and ignore the
        ordering applied with this method on such archives.
        '''
        with self._condition:
            if not self._contents_listed:
                return
            self._files[:] = [f for f in files if f not in self._extracted]
            if not self._files:
                # Nothing to do!
                return
            if self._extract_started:
                self.extract()

    def is_ready(self, name):
        '''Return True if the file <name> in the extractor's file list
        (as set by set_files()) is fully extracted.
        '''
        with self._condition:
            return name in self._extracted

    def stop(self):
        '''Signal the extractor to stop extracting and kill the extracting
        thread. Blocks until the extracting thread has terminated.
        '''
        self._threadpool.terminate()
        self._threadpool.join()
        self._threadpool.renew()
        if self._setupped:
            self._extract_started = False
            self._setupped = False

    def extract(self):
        '''Start extracting the files in the file list one by one using a
        new thread. Every time a new file is extracted a notify() will be
        signalled on the Condition that was returned by setup().
        '''
        with self._condition:
            if not self._contents_listed:
                return
            if not self._extract_started:
                mt = self._archive.support_concurrent_extractions \
                    and not self._archive.is_solid()
                if mt:
                    self._threadpool.ucbmap(
                        self._extract_file,self._files,
                        callback=self._extraction_finished,
                        error_callback=self._extract_files_errcb)
                else:
                    self._threadpool.apply_async(
                        self._extract_all_files,
                        error_callback=self._extract_files_errcb)

    @callback.Callback
    def contents_listed(self, extractor, files):
        ''' Called after the contents of the archive has been listed. '''
        pass

    @callback.Callback
    def file_extracted(self, extractor, filename):
        ''' Called whenever a new file is extracted and ready. '''
        pass

    def close(self):
        '''Close any open file objects, need only be called manually if the
        extract() method isn't called.
        '''
        self.stop()
        if self._archive:
            self._archive.close()

    def _extraction_finished(self, name):
        if self._threadpool.closed:
            return
        with self._condition:
            self._files.remove(name)
            self._extracted.add(name)
            self._condition.notifyAll()
        self.file_extracted(self, name)

    def _extract_all_files(self):
        # With multiple extractions for each pass, some of the files might have
        # already been extracted.
        with self._condition:
            files = list(set(self._files) - self._extracted)

        log.debug('Extracting from "%s" to "%s": "%s"',
                  self._src, self._dst, '", "'.join(files))
        for name in self._archive.iter_extract(files, self._dst):
            self._extraction_finished(name)

    def _extract_file(self, name):
        '''Extract the file named <name> to the destination directory,
        mark the file as "ready", then signal a notify() on the Condition
        returned by setup().
        '''
        log.debug('Extracting from "%s" to "%s": "%s"',
                  self._src, self._dst, name)
        self._archive.extract(name)
        return name

    def _extract_files_errcb(self, name, etype, value, tb):
        # Better to ignore any failed extractions (e.g. from a corrupt
        # archive) than to crash here and leave the main thread in a
        # possible infinite block. Damaged or missing files *should* be
        # handled gracefully by the main program anyway.
        log.error(_('! Extraction error: %s'), value)
        log.debug('Traceback:\n%s',
                  ''.join(traceback.format_tb(tb)).strip())

    def _list_contents(self):
        return [filename for filename in self._archive.iter_contents()]

    def _list_contents_cb(self, files):
        with self._condition:
            self._files[:] = files
            self._contents_listed = True
        self.contents_listed(self, files)

    def _list_contents_errcb(self, name, etype, value, tb):
        log.error(_('! Extraction error: %s'), value)
        log.debug('Traceback:\n%s',
                  ''.join(traceback.format_tb(tb)).strip())

class ArchiveException(Exception):
    ''' Indicate error during extraction operations. '''
    pass

# vim: expandtab:sw=4:ts=4

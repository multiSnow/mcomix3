"""archive_extractor.py - Archive extraction class."""

import sys
import os
import threading
import gtk
import archive_tools
import constants


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
        self._stop = False
        self._extract_thread = None
        self._condition = threading.Condition()

        self._archive = archive_tools.get_archive_handler(src)

        if self._archive:
            self._files = self._archive.list_contents()
            self._setupped = True
            return self._condition
        else:
            print _('! Non-supported archive format: %s') % os.path.splitext(src)[1][1:]

            #dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_WARNING,
            #    gtk.BUTTONS_CLOSE, _("Could not find file extractor!"))

            #dialog.format_secondary_markup(
            #    _("You need a matching extractor to read files of type ") + \
            #    os.path.splitext(src)[1][1:].upper())
            #dialog.run()
            #dialog.destroy()
            return None

    def get_files(self):
        """Return a list of names of all the files the extractor is currently
        set for extracting. After a call to setup() this is by default all
        files found in the archive. The paths in the list are relative to
        the archive root and are not absolute for the files once extracted.
        """
        return self._files[:]

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
        if self._type in (constants.GZIP, constants.BZIP2):
            self._files = [x for x in self._files if x in files]
        else:
            self._files = files

    def is_ready(self, name):
        """Return True if the file <name> in the extractor's file list
        (as set by set_files()) is fully extracted.
        """
        return self._extracted.get(name, False)

    def get_mime_type(self):
        """Return the mime type name of the extractor's current archive."""
        return self._type

    def stop(self):
        """Signal the extractor to stop extracting and kill the extracting
        thread. Blocks until the extracting thread has terminated.
        """
        self._stop = True

        if self._setupped:
            self._extract_thread.join()
            self.setupped = False

    def extract(self):
        """Start extracting the files in the file list one by one using a
        new thread. Every time a new file is extracted a notify() will be
        signalled on the Condition that was returned by setup().
        """
        self._extract_thread = threading.Thread(target=self._thread_extract)
        self._extract_thread.setDaemon(False)
        self._extract_thread.start()

    def close(self):
        """Close any open file objects, need only be called manually if the
        extract() method isn't called.
        """
        if self._archive:
            self._archive.close()

    def _thread_extract(self):
        """Extract the files in the file list one by one."""
        for name in self._files:
            self._extract_file(name)

        self.close()

    def _extract_file(self, name):
        """Extract the file named <name> to the destination directory,
        mark the file as "ready", then signal a notify() on the Condition
        returned by setup().
        """
        if self._stop:
            self.close()
            sys.exit(0)

        try:
            dst_path = os.path.join(self._dst, name)
            self._archive.extract(name, dst_path)

        except Exception, ex:
            # Better to ignore any failed extractions (e.g. from a corrupt
            # archive) than to crash here and leave the main thread in a
            # possible infinite block. Damaged or missing files *should* be
            # handled gracefully by the main program anyway.
            print _('! Extraction error: '), str(ex)

        self._condition.acquire()
        self._extracted[name] = True
        self._condition.notify()
        self._condition.release()

# vim: expandtab:sw=4:ts=4

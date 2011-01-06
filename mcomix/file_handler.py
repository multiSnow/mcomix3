"""file_handler.py - File handler that takes care of opening archives and images."""

import os
import shutil
import locale
import tempfile
import threading
import re
import gtk
import archive_extractor
import archive_tools
import encoding
import image_tools
import tools
from preferences import prefs
import constants
import cPickle

class FileHandler:

    """The FileHandler keeps track of images, pages, caches and reads files.

    When the Filehandler's methods refer to pages, they are indexed from 1,
    i.e. the first page is page 1 etc.

    Other modules should *never* read directly from the files pointed to by
    paths given by the FileHandler's methods. The files are not even
    guaranteed to exist at all times since the extraction of archives is
    threaded.
    """

    def __init__(self, window):
        self.file_loaded = False
        self.archive_type = None
        self.first_wanted = 0
        self.last_wanted = 1
        self._current_file = None

        self._window = window
        self._base_path = None
        self._tmp_dir = tempfile.mkdtemp(prefix='mcomix.', suffix=os.sep)
        self._stop_cacheing = False
        self._image_files = []
        self._current_image_index = None
        self._comment_files = []
        self._raw_pixbufs = {}
        self._name_table = {}
        self._extractor = archive_extractor.Extractor()
        self._condition = None
        self._image_re = constants.SUPPORTED_IMAGE_REGEX
        self.update_comment_extensions()

    def refresh_file(self, start_page=1):
        current_file = self._current_file
        self.open_file(current_file)

    def open_file(self, path, start_page=1):
        """Open the file pointed to by <path>.

        If <start_page> is not set we set the current
        page to 1 (first page), if it is set we set the current page to the
        value of <start_page>. If <start_page> is non-positive it means the
        last image.

        Return True if the file is successfully loaded.
        """

        # If the given <path> is invalid we update the statusbar.
        if os.path.isdir(path):
            self._window.statusbar.set_message(
                _('Could not open %s: Is a directory.') % path)
            return False

        if not os.path.isfile(path):
            self._window.statusbar.set_message(
                _('Could not open %s: No such file.') % path)
            return False

        if not os.access(path, os.R_OK):
            self._window.statusbar.set_message(
                _('Could not open %s: Permission denied.') % path)
            return False

        self.archive_type = archive_tools.archive_mime_type(path)

        if self.archive_type is None and not image_tools.is_image_file(path):
            self._window.statusbar.set_message(
                _('Could not open %s: Unknown file type.') % path)
            return False

        # We close the previously opened file.
        if self.file_loaded:
            self.close_file()

        while gtk.events_pending():
            gtk.main_iteration(False)

        self._current_file = path

        result = False

        # If <path> is an archive we create an Extractor for it and set the
        # files in it with file endings indicating image files or comments
        # as the ones to be extracted.
        if self.archive_type is not None:

            self._base_path = path
            self._condition = self._extractor.setup(path, self._tmp_dir, self.archive_type)

            if self._condition != None:

                files = self._extractor.get_files()
                image_files = [image for image in files
                    if self._image_re.search(image)
                    # Remove MacOS meta files from image list
                    and not '__MACOSX' in os.path.normpath(image).split(os.sep)]

                tools.alphanumeric_sort(image_files)
                self._image_files = \
                    [os.path.join(self._tmp_dir, f) for f in image_files]
                comment_files = filter(self._comment_re.search, files)
                self._comment_files = \
                    [os.path.join(self._tmp_dir, f) for f in comment_files]

                for name, full_path in zip(image_files, self._image_files):
                    self._name_table[full_path] = name

                for name, full_path in zip(comment_files, self._comment_files):
                    self._name_table[full_path] = name

                num_of_pages = len(self._image_files)

                if start_page < 0:

                    if self._window.is_double_page:
                        self._current_image_index = num_of_pages - 2
                    else:
                        self._current_image_index = num_of_pages - 1

                else:
                    self._current_image_index = start_page - 1

                self._current_image_index = max(0, self._current_image_index)

                depth = self._window.is_double_page and 2 or 1

                priority_ordering = (
                    range(self._current_image_index,
                        self._current_image_index + depth * 2) +
                    range(self._current_image_index - depth,
                        self._current_image_index)[::-1])

                priority_ordering = [image_files[p] for p in priority_ordering
                    if 0 <= p <= num_of_pages - 1]

                for i, name in enumerate(priority_ordering):
                    image_files.remove(name)
                    image_files.insert(i, name)

                self._extractor.set_files(image_files + comment_files)
                self._extractor.extract()

        # If <path> is an image we scan its directory for more images.
        else:

            self._base_path = os.path.dirname(path)

            for f in os.listdir(self._base_path):

                fpath = os.path.join(self._base_path, f)

                if image_tools.is_image_file(fpath):
                    self._image_files.append(fpath)

            self._image_files.sort(locale.strcoll)
            self._current_image_index = self._image_files.index(path)

        if not self._image_files:

            self._window.statusbar.set_message(_("No images in '%s'") %
                os.path.basename(path))
            self.file_loaded = False

            result = False
            self._window.uimanager.set_sensitivities()

        else:
            self.file_loaded = True
            self._window.imagehandler._image_files = self._image_files
            self._window.imagehandler._current_image_index = self._current_image_index
            self._window.imagehandler._base_path = self._base_path
            self._window.imagehandler._current_file = path
            self._window.imagehandler._name_table = self._name_table

            self._window.imagehandler.do_cacheing()
            self._window.scroll_to_fixed(horiz='startfirst', vert='top')

            self._window.uimanager.set_sensitivities()
            self._window.thumbnailsidebar.load_thumbnails()
            self._window.uimanager.set_sensitivities()

            self.write_fileinfo_file()

            result = True

        tools.alphanumeric_sort(self._comment_files)

        self._window.uimanager.recent.add(path)

        return result

    def close_file(self, *args):
        """Run tasks for "closing" the currently opened file(s)."""
        self.file_loaded = False
        self._current_file = None
        self._base_path = None
        self._stop_cacheing = True
        self._image_files = []
        self._current_image_index = None
        self._comment_files = []
        self._name_table.clear()
        self._window.clear()
        self._window.uimanager.set_sensitivities()
        self._extractor.stop()
        self.thread_delete(self._tmp_dir)
        self._tmp_dir = tempfile.mkdtemp(prefix='mcomix.', suffix=os.sep)
        self._window.imagehandler.close()
        self._window.thumbnailsidebar.clear()
        constants.RUN_GARBAGE_COLLECTOR

    def cleanup(self):
        """Run clean-up tasks. Should be called prior to exit."""
        self._extractor.stop()
        self.thread_delete(self._tmp_dir)
        self._stop_cacheing = True

    def get_number_of_comments(self):
        """Return the number of comments in the current archive."""
        return len(self._comment_files)

    def get_comment_text(self, num):
        """Return the text in comment <num> or None if comment <num> is not
        readable.
        """
        self._wait_on_comment(num)
        try:
            fd = open(self._comment_files[num - 1], 'rb')
            text = fd.read()
            fd.close()
        except Exception:
            text = None
        return text

    def get_comment_name(self, num):
        """Return the filename of comment <num>."""
        return self._comment_files[num - 1]

    def update_comment_extensions(self):
        """Update the regular expression used to filter out comments in
        archives by their filename.
        """
        exts = '|'.join(prefs['comment extensions'])
        self._comment_re = re.compile(r'\.(%s)\s*$' % exts, re.I)

    def get_path_to_page(self, page=None):
        """Return the full path to the image file for <page>, or the current
        page if <page> is None.
        """
        if page is None:
            if self._current_image_index < len(self._image_files):
                return self._image_files[self._current_image_index]
            else:
                return None

        if page - 1 < len(self._image_files):
            return self._image_files[page - 1]
        else:
            return None

    def get_path_to_base(self):
        """Return the full path to the current base (path to archive or
        image directory.)
        """
        return self._base_path

    def get_base_filename(self):
        """Return the filename of the current base (archive filename or
        directory name).
        """
        return os.path.basename(self.get_path_to_base())

    def get_pretty_current_filename(self):
        """Return a string with the name of the currently viewed file that is
        suitable for printing.
        """
        if self.archive_type is not None:
            name = os.path.basename(self._base_path)
        else:
            name = os.path.join(os.path.basename(self._base_path),
                os.path.basename(self._image_files[self._current_image_index]))
        return encoding.to_unicode(name)

    def _open_next_archive(self, *args):
        """Open the archive that comes directly after the currently loaded
        archive in that archive's directory listing, sorted alphabetically.
        """
        if self.archive_type is not None:

            arch_dir = os.path.dirname(self._base_path)

            if arch_dir == None:
                return

            files = os.listdir(arch_dir)
            files.sort(locale.strcoll)

            try:
                current_index = files.index(os.path.basename(self._base_path))
            except ValueError:
                return

            for f in files[current_index + 1:]:
                path = os.path.join(arch_dir, f)
                if archive_tools.archive_mime_type(path) is not None:
                    self.close_file()
                    self._window.imagehandler.close()
                    self._window.scroll_to_fixed(horiz='startfirst', vert='top')
                    self.open_file(path)
                    return

    def _open_previous_archive(self, *args):
        """Open the archive that comes directly before the currently loaded
        archive in that archive's directory listing, sorted alphabetically.
        """
        if self.archive_type is not None:

            if self._base_path == None:
                return

            arch_dir = os.path.dirname(self._base_path)
            files = os.listdir(arch_dir)
            files.sort(locale.strcoll)

            try:
                current_index = files.index(os.path.basename(self._base_path))
            except ValueError:
                return

            for f in reversed(files[:current_index]):
                path = os.path.join(arch_dir, f)
                if archive_tools.archive_mime_type(path) is not None:
                    self.close_file()
                    self._window.imagehandler.close()
                    self._window.scroll_to_fixed(horiz='endsecond', vert='bottom')
                    self.open_file(path, -1)

                    return

    def _wait_on_page(self, page):
        """Block the running (main) thread until the file corresponding to
        image <page> has been fully extracted.
        """
        path = self._window.imagehandler.get_path_to_page(page)
        self._wait_on_file(path)

    def _wait_on_comment(self, num):
        """Block the running (main) thread until the file corresponding to
        comment <num> has been fully extracted.
        """
        path = self._comment_files[num - 1]
        self._wait_on_file(path)

    def _wait_on_file(self, path):
        """Block the running (main) thread if the file <path> is from an
        archive and has not yet been extracted. Return when the file is
        ready.
        """
        if self.archive_type == None or path == None:
            return

        try:
            name = self._name_table[path]
            self._condition.acquire()
            while not self._extractor.is_ready(name):
                self._condition.wait()
            self._condition.release()
        except Exception:
            return

    def thread_delete(self, path):
        """Start a threaded removal of the directory tree rooted at <path>.
        This is to avoid long blockings when removing large temporary dirs.
        """
        del_thread = threading.Thread(target=shutil.rmtree, args=(path, True))
        del_thread.setDaemon(False)
        del_thread.start()

    def write_fileinfo_file(self):
        """Write current open file information."""

        if self.file_loaded:
            config = open(constants.FILEINFO_PICKLE_PATH, 'wb')

            if self.archive_type != None:
                current_file_info = [self._current_file, self._window.imagehandler._current_image_index]
            else:
                current_file_info = [self._image_files[self._window.imagehandler._current_image_index], 0]

            cPickle.dump(current_file_info, config, cPickle.HIGHEST_PROTOCOL)

            config.close()

    def read_fileinfo_file(self):
        """Read last loaded file info from disk."""

        fileinfo = None

        if os.path.isfile(constants.FILEINFO_PICKLE_PATH):
            config = None
            try:
                config = open(constants.FILEINFO_PICKLE_PATH, 'rb')

                fileinfo = cPickle.load(config)

                config.close()

            except Exception:
                print _('! Corrupt preferences file "%s", deleting...') % constants.FILEINFO_PICKLE_PATH
                if config is not None:
                    config.close()
                os.remove(constants.FILEINFO_PICKLE_PATH)

        return fileinfo


# vim: expandtab:sw=4:ts=4

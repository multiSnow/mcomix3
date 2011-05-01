"""file_handler.py - File handler that takes care of opening archives and images."""

import os
import shutil
import tempfile
import threading
import re
import gtk
import archive_extractor
import archive_tools
import image_tools
import tools
from preferences import prefs
import constants
import cPickle
import file_provider

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
        self._tmp_dir = tempfile.mkdtemp(prefix=u'mcomix.', suffix=os.sep)
        self._stop_cacheing = False
        self._image_files = []
        self._current_image_index = None
        self._comment_files = []
        self._raw_pixbufs = {}
        self._name_table = {}
        self._extractor = archive_extractor.Extractor()
        self._condition = None
        self._image_re = constants.SUPPORTED_IMAGE_REGEX
        self._file_provider = None
        self.update_comment_extensions()

    def refresh_file(self, *args, **kwargs):
        current_file = os.path.abspath(self._window.imagehandler.get_real_path())
        self.open_file(current_file, keep_fileprovider=True)

    def open_file(self, path, start_page=1, keep_fileprovider=False):
        """Open the file pointed to by <path>.

        If <start_page> is not set we set the current
        page to 1 (first page), if it is set we set the current page to the
        value of <start_page>. If <start_page> is non-positive it means the
        last image.

        Return True if the file is successfully loaded.
        """

        if isinstance(path, list) and len(path) == 0:
            # This is a programming error and does not need translation.
            assert False, "Tried to open an empty list of files."

        elif isinstance(path, list) and len(path) > 0:
            # A list of files was passed - open only these files.
            if self._file_provider is None or not keep_fileprovider:
                self._file_provider = file_provider.get_file_provider(path)

            path = path[0]
        else:
            # A single file was passed - use Comix' classic open mode
            # and open all files in its directory.
            if self._file_provider is None or not keep_fileprovider:
                self._file_provider = file_provider.get_file_provider([ path ])

        if not os.path.exists(path):
            self._window.statusbar.set_message(
                _('Could not open %s: No such file.') % path)
            return False

        if not os.access(path, os.R_OK):
            self._window.statusbar.set_message(
                _('Could not open %s: Permission denied.') % path)
            return False

        filelist = self._file_provider.list_files()
        archive_type = archive_tools.archive_mime_type(path)

        if archive_type is None and len(filelist) == 0:
            self._window.statusbar.set_message(_("No images in '%s'") % path)
            return False

        if archive_type is None and not image_tools.is_image_file(path) and len(filelist) == 0:
            self._window.statusbar.set_message(
                _('Could not open %s: Unknown file type.') % path)
            return False

        # We close the previously opened file.
        if self.file_loaded:
            self.close_file()

        # Catch up on UI events before actually starting to open the file(s).
        while gtk.events_pending():
            gtk.main_iteration(False)

        self._current_file = os.path.abspath(path)
        self.archive_type = archive_type
        self._stop_cacheing = False

        result = False

        # If <path> is an archive we create an Extractor for it and set the
        # files in it with file endings indicating image files or comments
        # as the ones to be extracted.
        if self.archive_type is not None:

            self._base_path = self._current_file
            self._condition = self._extractor.setup(self._base_path, self._tmp_dir, self.archive_type)

            if self._condition != None:

                files = self._extractor.get_files()
                image_files = [image for image in files
                    if self._image_re.search(image)
                    # Remove MacOS meta files from image list
                    and not u'__MACOSX' in os.path.normpath(image).split(os.sep)]

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

            self._base_path = self._file_provider.get_directory()
            self._image_files = filelist
            # Paths in file provider's list are always absolute
            absolute_path = os.path.abspath(path)
            if absolute_path in self._image_files:
                self._current_image_index = self._image_files.index(absolute_path)
            else:
                self._current_image_index = 0

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
            self._window.imagehandler._current_file = self._current_file
            self._window.imagehandler._name_table = self._name_table

            self._window.imagehandler.do_cacheing()
            self._window.scroll_to_fixed(horiz='startfirst', vert='top')

            self._window.uimanager.set_sensitivities()
            self._window.thumbnailsidebar.load_thumbnails()
            self._window.uimanager.set_sensitivities()

            self.write_fileinfo_file()

            result = True

        tools.alphanumeric_sort(self._comment_files)

        self._window.uimanager.recent.add(self._current_file)
        self._window.draw_image()

        return result

    def close_file(self, *args):
        """Run tasks for "closing" the currently opened file(s)."""
        self.file_loaded = False
        self.archive_type = None
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
        if self._condition:
            self._condition.acquire()
            self._condition.notifyAll()
            self._condition.release()
        self.thread_delete(self._tmp_dir)
        self._tmp_dir = tempfile.mkdtemp(prefix=u'mcomix.', suffix=os.sep)
        self._window.imagehandler.close()
        self._window.thumbnailsidebar.clear()
        tools.garbage_collect()

    def cleanup(self):
        """Run clean-up tasks. Should be called prior to exit."""
        self.thread_delete(self._tmp_dir)
        self._stop_cacheing = True
        self._extractor.stop()
        if self._condition:
            self._condition.acquire()
            self._condition.notifyAll()
            self._condition.release()

    def get_number_of_comments(self):
        """Return the number of comments in the current archive."""
        return len(self._comment_files)

    def get_comment_text(self, num):
        """Return the text in comment <num> or None if comment <num> is not
        readable.
        """
        self._wait_on_comment(num)
        try:
            fd = open(self._comment_files[num - 1], 'r')
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
        if self.archive_type is not None:
            return self._base_path
        else:
            img_index = self._window.imagehandler._current_image_index
            file = self._window.imagehandler._image_files[img_index]
            return os.path.dirname(file)

    def get_base_filename(self):
        """Return the filename of the current base (archive filename or
        directory name).
        """
        return os.path.basename(self.get_path_to_base())

    def get_pretty_current_filename(self):
        """Return a string with the name of the currently viewed file that is
        suitable for printing.
        """

        return self._window.imagehandler.get_pretty_current_filename()

    def _open_next_archive(self, *args):
        """Open the archive that comes directly after the currently loaded
        archive in that archive's directory listing, sorted alphabetically.
        Returns True if a new archive was opened, False otherwise.
        """
        if self.archive_type is not None:

            files = self._file_provider.list_files(file_provider.FileProvider.ARCHIVES)
            absolute_path = os.path.abspath(self._base_path)
            if absolute_path not in files: return
            current_index = files.index(absolute_path)

            for path in files[current_index + 1:]:
                if archive_tools.archive_mime_type(path) is not None:
                    self.close_file()
                    self._window.imagehandler.close()
                    self._window.scroll_to_fixed(horiz='startfirst', vert='top')
                    self.open_file(path, keep_fileprovider=True)
                    return True

        return False

    def _open_previous_archive(self, *args):
        """Open the archive that comes directly before the currently loaded
        archive in that archive's directory listing, sorted alphabetically.
        Returns True if a new archive was opened, False otherwise.
        """
        if self.archive_type is not None:

            files = self._file_provider.list_files(file_provider.FileProvider.ARCHIVES)
            absolute_path = os.path.abspath(self._base_path)
            if absolute_path not in files: return
            current_index = files.index(absolute_path)

            for path in reversed(files[:current_index]):
                if archive_tools.archive_mime_type(path) is not None:
                    self.close_file()
                    self._window.imagehandler.close()
                    self._window.scroll_to_fixed(horiz='endsecond', vert='bottom')
                    self.open_file(path, -1, keep_fileprovider=True)
                    return True

        return False

    def open_next_directory(self, *args):
        """ Opens the next sibling directory of the current file, as specified by
        file provider. Returns True if a new directory was opened and files found. """

        if self.archive_type is not None:
            listmode = file_provider.FileProvider.ARCHIVES
        else:
            listmode = file_provider.FileProvider.IMAGES

        current_dir = self._file_provider.get_directory()
        while self._file_provider.next_directory():
            files = self._file_provider.list_files(listmode)

            if len(files) > 0:
                self.close_file()
                self._window.imagehandler.close()
                self._window.scroll_to_fixed(horiz='startfirst', vert='top')
                self.open_file(files[0], keep_fileprovider=True)
                return True

        # Restore current directory if no files were found
        self._file_provider.set_directory(current_dir)
        return False

    def open_previous_directory(self, *args):
        """ Opens the previous sibling directory of the current file, as specified by
        file provider. Returns True if a new directory was opened and files found. """

        if self.archive_type is not None:
            listmode = file_provider.FileProvider.ARCHIVES
        else:
            listmode = file_provider.FileProvider.IMAGES

        current_dir = self._file_provider.get_directory()
        while self._file_provider.previous_directory():
            files = self._file_provider.list_files(listmode)

            if len(files) > 0:
                self.close_file()
                self._window.imagehandler.close()
                self._window.scroll_to_fixed(horiz='endsecond', vert='bottom')
                self.open_file(files[-1], -1, keep_fileprovider=True)
                return True

        # Restore current directory if no files were found
        self._file_provider.set_directory(current_dir)
        return False

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
            while not self._extractor.is_ready(name) and not self._stop_cacheing:
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
                print_( _('! Corrupt preferences file "%s", deleting...') % constants.FILEINFO_PICKLE_PATH )
                if config is not None:
                    config.close()
                os.remove(constants.FILEINFO_PICKLE_PATH)

        return fileinfo


# vim: expandtab:sw=4:ts=4

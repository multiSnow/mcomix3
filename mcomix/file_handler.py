"""file_handler.py - File handler that takes care of opening archives and images."""

import os
import shutil
import tempfile
import threading
import re
import cPickle
import gtk

from mcomix.preferences import prefs
from mcomix import archive_extractor
from mcomix import archive_tools
from mcomix import image_tools
from mcomix import icons
from mcomix import tools
from mcomix import constants
from mcomix import file_provider
from mcomix import callback
from mcomix import log
from mcomix import last_read_page
from mcomix import message_dialog
from mcomix.library import backend


class FileHandler(object):

    """The FileHandler keeps track of the actual files/archives opened.

    While ImageHandler takes care of pages/images, this class provides
    the raw file names for archive members and image files, extracts
    archives, and lists directories for image files.
    """

    def __init__(self, window):
        #: Indicates if files/archives are currently loaded.
        self.file_loaded = False
        #: Indicate if files/archives load has failed.
        self.file_load_failed = False
        #: None if current file is not an archive, or unrecognized format.
        self.archive_type = None

        #: Either path to the current archive, or first file in image list.
        #: This is B{not} the path to the currently open page.
        self._current_file = None
        #: Reference to L{MainWindow}.
        self._window = window
        #: Path to opened archive file, or directory containing current images.
        self._base_path = None
        #: Temporary directory used for extracting archives.
        self._tmp_dir = tempfile.mkdtemp(prefix=u'mcomix.', suffix=os.sep)
        #: If C{True}, no longer wait for files to get extracted.
        self._stop_waiting = False
        #: List of comment files inside of the currently opened archive.
        self._comment_files = []
        #: Mapping of absolute paths to archive path names.
        self._name_table = {}
        #: Archive extractor.
        self._extractor = archive_extractor.Extractor()
        #: Condition to wait on when extracting archives and waiting on files.
        self._condition = None
        #: Provides a list of available files/archives in the open directory.
        self._file_provider = None
        #: Keeps track of the last read page in archives
        self.last_read_page = last_read_page.LastReadPage(backend.LibraryBackend())
        #: Regexp used for determining which archive files are images.
        self._image_re = constants.SUPPORTED_IMAGE_REGEX
        #: Regexp used for determining which archive files are comment files.
        self._comment_re = None
        self.update_comment_extensions()
        #: Forces call to window.draw_image (if loading is delayed by user interaction)
        self._must_call_draw = False

        self.last_read_page.set_enabled(bool(prefs['store recent file info']))

    def refresh_file(self, *args, **kwargs):
        """ Closes the current file(s)/archive and reloads them. """
        if self.file_loaded:
            current_file = os.path.abspath(self._window.imagehandler.get_real_path())
            if self.archive_type is not None:
                start_page = self._window.imagehandler.get_current_page()
            else:
                start_page = 0
            self.open_file(current_file, start_page, keep_fileprovider=True)

    def open_file(self, path, start_page=0, keep_fileprovider=False):
        """Open the file pointed to by <path>.

        If <start_page> is not set we set the current
        page to 1 (first page), if it is set we set the current page to the
        value of <start_page>. If <start_page> is non-positive it means the
        last image.

        Return True if the file is successfully loaded.
        """

        try:
            path = self._initialize_fileprovider(path, keep_fileprovider)
        except ValueError, ex:
            self._window.statusbar.set_message(unicode(ex))
            self._window.osd.show(unicode(ex))
            return False

        if os.path.exists(path) and os.access(path, os.R_OK):
            filelist = self._file_provider.list_files()
            archive_type = archive_tools.archive_mime_type(path)
        else:
            filelist = []
            archive_type = None

        error_message = self._check_for_error_message(path, filelist, archive_type)
        if error_message:
            self._window.statusbar.set_message(error_message)
            self._window.osd.show(error_message)
            return False

        # We close the previously opened file.
        if self.file_loaded:
            self.close_file()

        # Catch up on UI events before actually starting to open the file(s).
        while gtk.events_pending():
            gtk.main_iteration(False)

        self.archive_type = archive_type
        self._current_file = os.path.abspath(path)
        self._stop_waiting = False

        result = False
        image_files = []
        current_image_index = 0

        # Actually open the file(s)/archive passed in path.
        if self.archive_type is not None:
            try:
                image_files, current_image_index = \
                    self._open_archive(self._current_file, start_page)
            except Exception, ex:
                self.file_loaded = False
                self._window.statusbar.set_message(unicode(ex))
                self._window.osd.show(unicode(ex))
                self._window.uimanager.set_sensitivities()
                return False

            # Update status bar
            archive_list = self._file_provider.list_files(
                file_provider.FileProvider.ARCHIVES)
            if self._current_file in archive_list:
                current_index = archive_list.index(self._current_file)
            else:
                current_index = 0

            self._window.statusbar.set_file_number(current_index + 1,
                len(archive_list))
        else:
            image_files, current_image_index = \
                self._open_image_files(filelist, self._current_file)

            # Update status bar (0 disables file numbers for images)
            self._window.statusbar.set_file_number(0, 0)

        if not image_files:
            self.file_loaded = False
            self.file_load_failed = True
            msg = _("No images in '%s'") % os.path.basename(path)
            self._window.statusbar.set_message(msg)
            self._window.osd.show(msg)

            result = False
            self._window.uimanager.set_sensitivities()

        else:
            self.file_loaded = True
            self.file_load_failed = False
            self._window.imagehandler._image_files = image_files
            self._window.imagehandler._current_image_index = current_image_index
            self._window.imagehandler._base_path = self._base_path
            self._window.imagehandler._current_file = self._current_file
            self._window.imagehandler._name_table = self._name_table

            self._window.imagehandler.do_cacheing()
            self._window.scroll_to_predefined((constants.SCROLL_TO_START,) * 2,
                constants.FIRST_INDEX)

            self._window.uimanager.set_sensitivities()
            self._window.thumbnailsidebar.load_thumbnails()
            self._window.uimanager.set_sensitivities()

            self.write_fileinfo_file()

            # If no extraction is required, mark all files as available instantly.
            if self.archive_type is None:
                self.file_available(filelist)

            result = True

        tools.alphanumeric_sort(self._comment_files)

        self._window.uimanager.recent.add(self._current_file)

        if self._must_call_draw:
            self._must_call_draw = False
            self._window.draw_image()

        self.file_opened()
        return result

    @callback.Callback
    def file_opened(self):
        """ Called when a new set of files has successfully been opened. """
        pass

    @callback.Callback
    def close_file(self, *args):
        """Run tasks for "closing" the currently opened file(s)."""
        self.update_last_read_page()
        self.file_loaded = False
        self.archive_type = None
        self._current_file = None
        self._base_path = None
        self._stop_waiting = True
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
        self._window.set_icon_list(*icons.mcomix_icons())
        tools.garbage_collect()

    def _initialize_fileprovider(self, path, keep_fileprovider):
        """ Creates the L{file_provider.FileProvider} for C{path}.

        If C{path} is a list, assumes that only the files in the list
        should be available. If C{path} is a string, assume that it is
        either a directory or an image file, and all files in that directory
        should be opened.

        @param path: List of file names, or single file/directory as string.
        @param keep_fileprovider: If C{True}, no new provider is constructed.
        @return: If C{path} was a list, returns the first list element.
            Otherwise, C{path} is not modified."""

        if isinstance(path, list) and len(path) == 0:
            # This is a programming error and does not need translation.
            assert False, "Tried to open an empty list of files."

        elif isinstance(path, list) and len(path) > 0:
            # A list of files was passed - open only these files.
            if self._file_provider is None or not keep_fileprovider:
                self._file_provider = file_provider.get_file_provider(path)

            return path[0]
        else:
            # A single file was passed - use Comix' classic open mode
            # and open all files in its directory.
            if self._file_provider is None or not keep_fileprovider:
                self._file_provider = file_provider.get_file_provider([ path ])

            return path

    def _check_for_error_message(self, path, filelist, archive_type):
        """ Checks for various error that could occur when opening C{path}.

        @param path: Path to file that should be opened.
        @param filelist: List of files in the directory of C{path}.
        @param archive_type: Archive type, if C{path} is an archive.
        @return: An appropriate error string, or C{None} if no error was found.
        """
        if not os.path.exists(path):
            return _('Could not open %s: No such file.') % path

        elif not os.access(path, os.R_OK):
            return _('Could not open %s: Permission denied.') % path

        elif archive_type is None and len(filelist) == 0:
            return _("No images in '%s'") % path

        elif (archive_type is None and
            not image_tools.is_image_file(path) and
            len(filelist) == 0):
            return _('Could not open %s: Unknown file type.') % path

        else:
            return None

    def _open_archive(self, path, start_page):
        """ Opens the archive passed in C{path}.

        Creates an L{archive_extractor.Extractor} and extracts all images
        found within the archive.

        @return: A tuple containing C{(image_files, image_index)}. """


        self._base_path = path
        try:
            self._condition = self._extractor.setup(self._base_path,
                                                self._tmp_dir,
                                                self.archive_type)
        except Exception:
            self._condition = None
            raise

        if self._condition != None:

            files = self._extractor.get_files()
            archive_images = [image for image in files
                if self._image_re.search(image)
                # Remove MacOS meta files from image list
                and not u'__MACOSX' in os.path.normpath(image).split(os.sep)]

            archive_images = self._sort_archive_images(archive_images)
            image_files = [ os.path.join(self._tmp_dir, f)
                            for f in archive_images ]

            comment_files = filter(self._comment_re.search, files)
            self._comment_files = [ os.path.join(self._tmp_dir, f)
                                    for f in comment_files ]

            # Allow managing sub-archives by keeping archives based on extension
            archive_files = filter(
                    archive_tools.get_supported_archive_regex().search, files)
            archive_files_paths = [ os.path.join(self._tmp_dir, f)
                                    for f in archive_files ]

            for name, full_path in zip(archive_images, image_files):
                self._name_table[full_path] = name

            for name, full_path in zip(comment_files, self._comment_files):
                self._name_table[full_path] = name

            for name, full_path in zip(archive_files, archive_files_paths):
                self._name_table[full_path] = name

            # Determine current archive image index.
            current_image_index = self._get_index_for_page(start_page,
                len(image_files), path)

            # Sort files to determine extraction order.
            self._sort_archive_files(archive_images, current_image_index)

            self._extractor.set_files(archive_images + comment_files + archive_files)
            self._extractor.file_extracted += self._extracted_file
            self._extractor.extract()

            # Manage subarchive through recursion
            if archive_files:
                has_subarchive = False

                # For each potential archive, change the current extractor,
                # extract recursively, and restore the internal extractor.
                for f in archive_files_paths:
                    if not self._extractor.is_ready(f):
                        self._wait_on_file(f)

                    if archive_tools.archive_mime_type(f) is not None:
                        # save self data
                        state = self._save_state()
                        # Setup temporary data
                        self._extractor = archive_extractor.Extractor()
                        self._tmp_dir = os.path.join(self._tmp_dir,
                            os.path.basename(f) + u'.dir')
                        if not os.path.exists(self._tmp_dir):
                            os.mkdir(self._tmp_dir)
                        self._condition = self._extractor.setup(self._base_path,
                                                self._tmp_dir,
                                                self.archive_type)
                        self._extractor.file_extracted += self._extracted_file
                        add_images, dummy_idx = self._open_archive(f, 1) # recursion here
                        # Since it's recursive, we do not want to loose the way to ensure
                        # that the file was extracted, so too bad but it will be a lil' slower.
                        for image in add_images:
                            self._wait_on_file(image)
                        image_files.extend(add_images)
                        self._extractor.stop()
                        self._extractor.close()
                        # restore self data
                        self._restore_state(state)
                        has_subarchive = True

                # Allows to avoid any behaviour changes if there was no subarchive..
                if has_subarchive:
                    # Mark additional files as extracted
                    self._comment_files = \
                        filter(self._comment_re.search, image_files)
                    tmp_image_files = \
                        filter(self._image_re.search, image_files)
                    self._name_table.clear()
                    for full_path in tmp_image_files + self._comment_files:
                        self._name_table[full_path] = os.path.basename(full_path)
                        # This trick here allows to avoid indefinite waiting on
                        # the sub-extracted files.
                        self._extractor._extracted[os.path.basename(full_path)] = True
                    # set those files instead of image_files for the return
                    image_files = tmp_image_files

            # Image index may have changed after additional files were extracted.
            current_image_index = self._get_index_for_page(start_page,
                len(image_files), path, confirm=True)

            return image_files, current_image_index

        else:
            # No condition was returned from the Extractor, i.e. invalid archive.
            return [], 0

    def _sort_archive_images(self, filelist):
        """ Sorts the image list passed in C{filelist} based on the sorting
        preference option, and returns the newly sorted list. """
        filelist = list(filelist)  # Create a copy of the list

        if prefs['sort archive by'] == constants.SORT_NAME:
            tools.alphanumeric_sort(filelist)
        elif prefs['sort archive by'] == constants.SORT_NAME_LITERAL:
            filelist.sort()
        else:
            # No sorting
            pass

        if prefs['sort archive order'] == constants.SORT_DESCENDING:
            filelist.reverse()

        return filelist

    def _save_state(self):
        """ Saves the FileHandler's internal state and returns it as dict object,
        which can be loaded by L{_restore_state}. """

        state = {}
        for var in ('_extractor', '_base_path', '_tmp_dir', '_condition',
                '_comment_files'):
            state[var] = getattr(self, var)

        return state

    def _restore_state(self, state):
        """ Restores the state previously saved by L{_save_state}. """

        for key, value in state.iteritems():
            setattr(self, key, value)

    def _get_index_for_page(self, start_page, num_of_pages, path, confirm=False):
        """ Returns the page that should be displayed for an archive.
        @param start_page: If -1, show last page. If 0, show either first page
                           or last read page. If > 0, show C{start_page}.
        @param num_of_pages: Page count.
        @param path: Archive path.
        """
        if start_page < 0 and self._window.is_double_page:
            current_image_index = num_of_pages - 2
        elif start_page < 0 and not self._window.is_double_page:
            current_image_index = num_of_pages - 1
        elif start_page == 0:
            if confirm:
                current_image_index = self._get_last_read_page(path) - 1
            else:
                current_image_index = (self.last_read_page.get_page(path) or 1) - 1
        else:
            current_image_index = start_page - 1

        return min(max(0, current_image_index), num_of_pages - 1)

    def _get_last_read_page(self, path):
        """ If the user read an archive previously, ask to continue from
        that time, or from page 1. This method returns a page index, that is,
        index + 1. """
        if (isinstance(path, list) and len(path) > 0
            and isinstance(path[0], (str, unicode))):
            path = path[0]

        last_read_page = self.last_read_page.get_page(path)
        if last_read_page is not None:
            read_date = self.last_read_page.get_date(path)

            dialog = message_dialog.MessageDialog(self._window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                gtk.BUTTONS_YES_NO)
            dialog.set_should_remember_choice('resume-from-last-read-page',
                (gtk.RESPONSE_YES, gtk.RESPONSE_NO))
            dialog.set_text(
                (_('Continue reading from page %d?') % last_read_page),
                _('You stopped reading here on %(date)s, %(time)s. '
                'If you choose "Yes", reading will resume on page %(page)d. Otherwise, '
                'the first page will be loaded.') % {'date': read_date.date().strftime("%x"),
                    'time': read_date.time().strftime("%X"), 'page': last_read_page})
            result = dialog.run()

            self._must_call_draw = True

            if result == gtk.RESPONSE_YES:
                return last_read_page
            else:
                return 1
        else:
            return 1

    def _sort_archive_files(self, archive_images, current_image_index):
        """ Sorts the list C{archive_images} in place based on a priority order
        algorithm. """

        depth = self._window.is_double_page and 2 or 1

        priority_ordering = (
            range(current_image_index,
                current_image_index + depth * 2) +
            range(current_image_index - depth,
                current_image_index)[::-1])

        priority_ordering = [archive_images[p] for p in priority_ordering
            if 0 <= p <= len(archive_images) - 1]

        for i, name in enumerate(priority_ordering):
            archive_images.remove(name)
            archive_images.insert(i, name)


    def _open_image_files(self, filelist, image_path):
        """ Opens all files passed in C{filelist}.

        If C{image_path} is found in C{filelist}, the current page will be set
        to its index within C{filelist}.

        @return: Tuple of C{(image_files, image_index)}
        """

        self._base_path = self._file_provider.get_directory()

        if image_path in filelist:
            current_image_index = filelist.index(image_path)
        else:
            current_image_index = 0

        return filelist, current_image_index

    def cleanup(self):
        """Run clean-up tasks. Should be called prior to exit."""
        self.thread_delete(self._tmp_dir)
        self._stop_waiting = True
        self._extractor.stop()
        if self._condition:
            self._condition.acquire()
            self._condition.notifyAll()
            self._condition.release()

        self.update_last_read_page()

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

    def get_path_to_base(self):
        """Return the full path to the current base (path to archive or
        image directory.)
        """
        if self.archive_type is not None:
            return self._base_path
        elif self._window.imagehandler._image_files:
            img_index = self._window.imagehandler._current_image_index
            filename = self._window.imagehandler._image_files[img_index]
            return os.path.dirname(filename)
        else:
            return None

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
                    self._window.scroll_to_predefined(
                        (constants.SCROLL_TO_START,) * 2, constants.FIRST_INDEX)
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
                    self._window.scroll_to_predefined(
                        (constants.SCROLL_TO_END,) * 2, constants.LAST_INDEX)
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
                self._window.scroll_to_predefined(
                    (constants.SCROLL_TO_START,) * 2, constants.FIRST_INDEX)
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
                self._window.scroll_to_predefined(
                    (constants.SCROLL_TO_END,) * 2, constants.LAST_INDEX)
                self.open_file(files[-1], -1, keep_fileprovider=True)
                return True

        # Restore current directory if no files were found
        self._file_provider.set_directory(current_dir)
        return False

    def file_is_available(self, filepath):
        """ Returns True if the file specified by "filepath" is available
        for reading, i.e. extracted to harddisk. """

        if self.archive_type is not None:
            self._condition.acquire()
            ready = self._extractor.is_ready(self._name_table[filepath])
            self._condition.release()
            return ready

        elif filepath is None:
            return False

        elif os.path.isfile(filepath):
            return True

        else:
            return False

    @callback.Callback
    def file_available(self, filepaths):
        """ Called every time a new file from the Filehandler's opened
        files becomes available. C{filepaths} is a list of now available files.
        """
        pass

    def _extracted_file(self, extractor, name):
        """ Called when the extractor finishes extracting the file at
        <name>. This name is relative to the temporary directory
        the files were extracted to. """
        filepath = os.path.join(extractor.get_directory(), name)
        self.file_available([filepath])

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
            while not self._extractor.is_ready(name) and not self._stop_waiting:
                self._condition.wait()
            self._condition.release()
        except Exception, ex:
            log.error(u'Waiting on extraction of "%s" failed: %s', path, ex)
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

            path = self._window.imagehandler.get_real_path()
            page_index = self._window.imagehandler.get_current_page() - 1
            current_file_info = [ path, page_index ]

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

            except Exception, ex:
                log.error(_('! Corrupt preferences file "%s", deleting...'),
                        constants.FILEINFO_PICKLE_PATH )
                log.info(u'Error was: %s', ex)
                if config is not None:
                    config.close()
                os.remove(constants.FILEINFO_PICKLE_PATH)

        return fileinfo

    def update_last_read_page(self):
        """ Stores the currently viewed page. """
        if self.archive_type is None or not self.file_loaded:
            return

        archive_path = self.get_path_to_base()
        page = self._window.imagehandler.get_current_page()
        # Do not store first page (first page is default
        # behaviour and would waste space unnecessarily)
        try:
            if page == 1:
                self.last_read_page.clear_page(archive_path)
            else:
                self.last_read_page.set_page(archive_path, page)
        except ValueError:
            # The book no longer exists in the library and has been deleted
            pass


# vim: expandtab:sw=4:ts=4

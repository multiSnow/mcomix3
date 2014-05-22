"""image_handler.py - Image handler that takes care of cacheing and giving out images."""

import os
import threading
import gtk
import Queue

from mcomix.preferences import prefs
from mcomix import i18n
from mcomix import tools
from mcomix import image_tools
from mcomix import thumbnail_tools
from mcomix import constants
from mcomix import callback
from mcomix import log
from mcomix.worker_thread import WorkerThread

class ImageHandler:

    """The FileHandler keeps track of images, pages, caches and reads files.

    When the Filehandler's methods refer to pages, they are indexed from 1,
    i.e. the first page is page 1 etc.

    Other modules should *never* read directly from the files pointed to by
    paths given by the FileHandler's methods. The files are not even
    guaranteed to exist at all times since the extraction of archives is
    threaded.
    """

    def __init__(self, window):

        #: Reference to main window
        self._window = window

        #: Caching thread
        self._thread = WorkerThread(self._cache_pixbuf, sort_orders=True)

        #: Archive path, if currently opened file is archive
        self._base_path = None
        #: List of image file names, either from extraction or directory
        self._image_files = None
        #: Index of current page
        self._current_image_index = None
        #: Set of images reading for decoding (i.e. already extracted)
        self._available_images = set()
        #: List of pixbufs we want to cache
        self._wanted_pixbufs = []
        #: Pixbuf map from page > Pixbuf
        self._raw_pixbufs = {}
        #: How many pages to keep in cache
        self._cache_pages = prefs['max pages to cache']

        #: Advance only one page instead of two in double page mode
        self.force_single_step = False

        self._window.filehandler.file_available += self._file_available

    def _get_pixbuf(self, index):
        """Return the pixbuf indexed by <index> from cache.
        Pixbufs not found in cache are fetched from disk first.
        """
        pixbuf = constants.MISSING_IMAGE_ICON

        if index not in self._raw_pixbufs:
            self._wait_on_page(index + 1)

            try:
                pixbuf = image_tools.load_pixbuf(self._image_files[index])
                self._raw_pixbufs[index] = pixbuf
                tools.garbage_collect()
            except Exception, e:
                self._raw_pixbufs[index] = constants.MISSING_IMAGE_ICON
                log.error('Could not load pixbuf for page %u: %r', index + 1, e)
        else:
            try:
                pixbuf = self._raw_pixbufs[index]
            except Exception:
                pass

        return pixbuf

    def get_pixbufs(self, number_of_bufs):
        """Returns number_of_bufs pixbufs for the image(s) that should be
        currently displayed. This method might fetch images from disk, so make
        sure that number_of_bufs is as small as possible.
        """
        result = []
        for i in range(number_of_bufs):
            result.append(self._get_pixbuf(self._current_image_index + i))
        return result

    def get_pixbuf_auto_background(self, number_of_bufs): # XXX limited to at most 2 pages
        """ Returns an automatically calculated background color
        for the current page(s). """

        pixbufs = self.get_pixbufs(number_of_bufs)

        if len(pixbufs) == 1:
            auto_bg = image_tools.get_most_common_edge_colour(pixbufs[0])
        elif len(pixbufs) == 2:
            left, right = pixbufs
            if self._window.is_manga_mode:
                left, right = right, left

            auto_bg = image_tools.get_most_common_edge_colour((left, right))
        else:
            assert False, 'Unexpected pixbuf count'

        return auto_bg

    def do_cacheing(self):
        """Make sure that the correct pixbufs are stored in cache. These
        are (in the current implementation) the current image(s), and
        if cacheing is enabled, also the one or two pixbufs before and
        after the current page. All other pixbufs are deleted and garbage
        collected directly in order to save memory.
        """
        if not self._window.filehandler.file_loaded:
            return

        # Flush caching orders.
        self._thread.clear_orders()
        # Get list of wanted pixbufs.
        wanted_pixbufs = self._ask_for_pages(self.get_current_page())
        if -1 != self._cache_pages:
            # We're not caching everything, remove old pixbufs.
            for index in set(self._raw_pixbufs) - set(wanted_pixbufs):
                del self._raw_pixbufs[index]
        log.debug('Caching page(s) %s', ' '.join([str(index + 1) for index in wanted_pixbufs]))
        self._wanted_pixbufs = wanted_pixbufs
        # Start caching available images not already in cache.
        wanted_pixbufs = [index for index in wanted_pixbufs
                          if index in self._available_images and not index in self._raw_pixbufs]
        orders = [(priority, index) for priority, index in enumerate(wanted_pixbufs)]
        if len(orders) > 0:
            self._thread.extend_orders(orders)

    def _cache_pixbuf(self, wanted):
        priority, index = wanted
        log.debug('Caching page %u', index + 1)
        self._get_pixbuf(index)

    def next_page(self):
        """Set up filehandler to the next page. Return the new page number.
        """
        if not self._window.filehandler.file_loaded and self._window.filehandler.archive_type is None:
            return False

        viewed = self._window.displayed_double() and 2 or 1

        if self.get_current_page() + viewed > self.get_number_of_pages():

            archive_open = self._window.filehandler.archive_type is not None
            next_archive_opened = False
            if (self._window.slideshow.is_running() and \
                prefs['slideshow can go to next archive']) or \
                prefs['auto open next archive']:
                next_archive_opened = self._window.filehandler._open_next_archive()

            # If "Auto open next archive" is disabled, do not go to the next
            # directory if current file was an archive.
            if not next_archive_opened and \
                prefs['auto open next directory'] and \
                (not archive_open or prefs['auto open next archive']):
                self._window.filehandler.open_next_directory()

            return False

        self._current_image_index += self._get_forward_step_length()

        return self.get_current_page()

    def previous_page(self):
        """Set up filehandler to the previous page. Return the new page number.
        """
        if not self._window.filehandler.file_loaded and self._window.filehandler.archive_type is None:
            return False

        if self.get_current_page() <= 1:

            archive_open = self._window.filehandler.archive_type is not None
            previous_archive_opened = False
            if (self._window.slideshow.is_running() and \
                prefs['slideshow can go to next archive']) or \
                prefs['auto open next archive']:
                previous_archive_opened = self._window.filehandler._open_previous_archive()

            # If "Auto open next archive" is disabled, do not go to the previous
            # directory if current file was an archive.
            if not previous_archive_opened and \
                prefs['auto open next directory'] and \
                (not archive_open or prefs['auto open next archive']):
                self._window.filehandler.open_previous_directory()

            return False

        step = self._get_backward_step_length()
        step = min(self._current_image_index, step)
        self._current_image_index -= step

        if (step == 2 and self.get_virtual_double_page()):
            self._current_image_index += 1

        return self.get_current_page()

    def first_page(self):
        """Set up filehandler to the first page. Return the new page number.
        """
        if not self._window.filehandler.file_loaded:
            return False
        self._current_image_index = 0
        return self.get_current_page()

    def last_page(self):
        """Set up filehandler to the last page. Return the new page number.
        """
        if not self._window.filehandler.file_loaded:
            return False
        offset = self._window.is_double_page and 2 or 1
        offset = min(self.get_number_of_pages(), offset)
        self._current_image_index = self.get_number_of_pages() - offset
        if (offset == 2 and self.get_virtual_double_page()):
            self._current_image_index += 1
        return self.get_current_page()

    def set_page(self, page_num):
        """Set up filehandler to the page <page_num>. Return the new page number.
        """
        if not 0 < page_num <= self.get_number_of_pages():
            return False

        self._current_image_index = page_num - 1
        self.do_cacheing()

        return self.get_current_page()

    def get_virtual_double_page(self):
        """Return True if the current state warrants use of virtual
        double page mode (i.e. if double page mode is on, the corresponding
        preference is set, and one of the two images that should normally
        be displayed has a width that exceeds its height), or if currently
        on the first page.
        """
        if (self.get_current_page() == 1 and
            prefs['virtual double page for fitting images'] & constants.SHOW_DOUBLE_AS_ONE_TITLE and
            self._window.filehandler.archive_type is not None):
            return True

        if (not self._window.is_double_page or
          not prefs['virtual double page for fitting images'] & constants.SHOW_DOUBLE_AS_ONE_WIDE or
          self.get_current_page() == self.get_number_of_pages()):
            return False

        page1 = self._get_pixbuf(self._current_image_index)
        if page1.get_width() > page1.get_height():
            return True
        page2 = self._get_pixbuf(self._current_image_index + 1)
        if page2.get_width() > page2.get_height():
            return True
        return False

    def get_real_path(self):
        """Return the "real" path to the currently viewed file, i.e. the
        full path to the archive or the full path to the currently
        viewed image.
        """
        if self._window.filehandler.archive_type is not None:
            return self._window.filehandler.get_path_to_base()
        return self.get_path_to_page()

    def close(self, *args):
        """Run tasks for "closing" the currently opened file(s)."""

        self.first_wanted = 0
        self.last_wanted = 1

        self.cleanup()
        self._base_path = None
        self._image_files = []
        self._current_image_index = None
        self._available_images.clear()
        self._raw_pixbufs.clear()
        self._cache_pages = prefs['max pages to cache']

        tools.garbage_collect()

    def cleanup(self):
        """Run clean-up tasks. Should be called prior to exit."""
        self._thread.stop()

    def page_is_available(self, page=None):
        """ Returns True if <page> is available and calls to get_pixbufs
        would not block. If <page> is None, the current page(s) are assumed. """

        if page is None:
            current_page = self.get_current_page()
            if self._window.displayed_double():
                pages = [ current_page, current_page + 1 ]
            else:
                pages = [ current_page ]
        else:
            pages = [ page ]

        for page in pages:
            path = self.get_path_to_page(page)
            if not self._window.filehandler.file_is_available(path):
                return False

        return True

    @callback.Callback
    def page_available(self, page):
        """ Called whenever a new page becomes available, i.e. the corresponding
        file has been extracted. """
        log.debug('Page %u is available', page)
        index = page - 1
        assert index not in self._available_images
        self._available_images.add(index)
        # Check if we need to cache it.
        priority = None
        if index in self._wanted_pixbufs:
            # In the list of wanted pixbufs.
            priority = self._wanted_pixbufs.index(index)
        elif -1 == self._cache_pages:
            # We're caching everything.
            priority = self.get_number_of_pages()
        if priority is not None:
            self._thread.append_order((priority, index))

    def _file_available(self, filepaths):
        """ Called by the filehandler when a new file becomes available. """
        # Find the page that corresponds to <filepath>
        if not self._image_files:
            return

        available = sorted(filepaths)
        for i, imgpath in enumerate(self._image_files):
            if tools.bin_search(available, imgpath) >= 0:
                self.page_available(i + 1)

    def is_last_page(self):
        """Return True if at the last page."""
        if self._window.displayed_double():
            return self.get_current_page() + 1 >= self.get_number_of_pages()
        else:
            return self.get_current_page() == self.get_number_of_pages()

    def get_number_of_pages(self):
        """Return the number of pages in the current archive/directory."""
        if self._image_files is not None:
            return len(self._image_files)
        else:
            return 0

    def get_current_page(self):
        """Return the current page number (starting from 1), or 0 if no file is loaded."""
        if self._current_image_index is not None:
            return self._current_image_index + 1
        else:
            return 0

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

    def get_page_filename(self, page=None, double=False):
        """Return the filename of the <page>, or the filename of the
        currently viewed page if <page> is None. If <double> is True, return
        a tuple (p, p') where p is the filename of <page> (or the current
        page) and p' is the filename of the page after.
        """
        if page is None:
            page = self._current_image_index + 1

        first_path = self.get_path_to_page(page)
        if first_path == None:
            return None

        if double:
            second_path = self.get_path_to_page(page + 1)

            if second_path != None:
                first = os.path.basename(first_path)
                second = os.path.basename(second_path)
            else:
                return None

            return first, second

        return os.path.basename(first_path)

    def get_pretty_current_filename(self):
        """Return a string with the name of the currently viewed file that is
        suitable for printing.
        """
        if self._window.filehandler.archive_type is not None:
            name = os.path.basename(self._base_path)
        elif self._image_files:
            img_file = os.path.abspath(self._image_files[self._current_image_index])
            name = os.path.join(
                os.path.basename(os.path.dirname(img_file)),
                os.path.basename(img_file)
            )
        else:
            name = u''

        return i18n.to_unicode(name)

    def get_size(self, page=None):
        """Return a tuple (width, height) with the size of <page>. If <page>
        is None, return the size of the current page.
        """
        self._wait_on_page(page)

        page_path = self.get_path_to_page(page)

        if page_path != None:
            info = gtk.gdk.pixbuf_get_file_info(page_path)
        else:
            return None

        if info is not None:
            return (info[1], info[2])
        return (0, 0)

    def get_mime_name(self, page=None):
        """Return a string with the name of the mime type of <page>. If
        <page> is None, return the mime type name of the current page.
        """
        self._wait_on_page(page)

        page_path = self.get_path_to_page(page)

        if page_path != None:
            info = gtk.gdk.pixbuf_get_file_info(page_path)
        else:
            return None

        if info is not None:
            return info[0]['name'].upper()
        return _('Unknown filetype')

    def get_thumbnail(self, page=None, width=128, height=128, create=False):
        """Return a thumbnail pixbuf of <page> that fit in a box with
        dimensions <width>x<height>. Return a thumbnail for the current
        page if <page> is None.

        If <create> is True, and <width>x<height> <= 128x128, the
        thumbnail is also stored on disk.
        """
        self._wait_on_page(page)
        path = self.get_path_to_page(page)

        if path == None:
            return constants.MISSING_IMAGE_ICON

        try:
            thumbnailer = thumbnail_tools.Thumbnailer()
            thumbnailer.set_store_on_disk(create)
            thumbnailer.set_size(width, height)
            return thumbnailer.thumbnail(path)
        except Exception:
            return constants.MISSING_IMAGE_ICON

    def _get_forward_step_length(self):
        """Return the step length for switching pages forwards."""
        if self.force_single_step:
            return 1
        elif (prefs['double step in double page mode'] and \
            self._window.displayed_double()):
            return 2
        return 1

    def _get_backward_step_length(self):
        """Return the step length for switching pages backwards."""
        if self.force_single_step:
            return 1
        elif (prefs['double step in double page mode'] and \
            self._window.is_double_page):
            return 2
        return 1

    def _wait_on_page(self, page):
        """Block the running (main) thread until the file corresponding to
        image <page> has been fully extracted.
        """
        index = page - 1
        if index in self._available_images:
            # Already extracted!
            return
        log.debug('Waiting for page %u', page)
        path = self.get_path_to_page(page)
        self._window.filehandler._wait_on_file(path)

    def _ask_for_pages(self, page):
        """Ask for pages around <page> to be given priority extraction.
        """
        files = []
        if self._window.is_double_page:
            page_width = 2
        else:
            page_width = 1
        if 0 == self._cache_pages:
            # Only ask for current page.
            num_pages = page_width
        elif -1 == self._cache_pages:
            # Ask for 10 pages.
            num_pages = min(10, self.get_number_of_pages())
        else:
            num_pages = self._cache_pages
        page_list = [page - 1 - page_width + n for n in xrange(num_pages)]
        # Current and next page first, followed by previous page.
        previous_page = page_list[0:page_width]
        del page_list[0:page_width]
        page_list[2*page_width:2*page_width] = previous_page
        page_list = [index for index in page_list if index >= 0 and index < len(self._image_files)]
        log.debug('Ask for priority extraction around page %u: %s', page, ' '.join([str(n + 1) for n in page_list]))
        for index in page_list:
            if index in self._available_images:
                # Already extracted.
                continue
            files.append(self._image_files[index])
        if len(files) > 0:
            self._window.filehandler._ask_for_files(files)
        return page_list

# vim: expandtab:sw=4:ts=4

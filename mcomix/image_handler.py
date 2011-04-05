"""image_handler.py - Image handler that takes care of cacheing and giving out images."""

import os
import threading
import gtk
import encoding
import tools
import image_tools
from preferences import prefs
import thumbnail_tools
import constants

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

        self.first_wanted = 0
        self.last_wanted = 1
        self._current_file = None
        self.is_cacheing = False

        self._window = window
        self._base_path = None
        self._stop_cacheing = False
        self._image_files = None
        self._current_image_index = None
        self._raw_pixbufs = {}
        self._pixbuf_auto_bgs = {}
        self._name_table = {}
        self.force_single_step = False

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
                self._pixbuf_auto_bgs[index] = image_tools.get_most_common_edge_colour(self._raw_pixbufs[index])
            except Exception:
                self._raw_pixbufs[index] = constants.MISSING_IMAGE_ICON
                self._pixbuf_auto_bgs[index] = [0,0,0]
        else:
            try:
                pixbuf = self._raw_pixbufs[index]
            except Exception:
                pass

        return pixbuf

    def get_pixbufs(self, single=False):
        """Return the pixbuf(s) for the image(s) that should be currently
        displayed, from cache. Return two pixbufs in double-page mode unless
        <single> is True. Pixbufs not found in cache are fetched from
        disk first.
        """
        if not self._window.displayed_double() or single:
            return [self._get_pixbuf(self._current_image_index)]

        return [self._get_pixbuf(self._current_image_index),
                self._get_pixbuf(self._current_image_index + 1)]

    def get_pixbuf_auto_background(self, single=False):

        self._get_pixbuf(self._current_image_index)
        auto_bg = self._pixbuf_auto_bgs[self._current_image_index]

        if self._window.displayed_double() or not single:

            self._get_pixbuf(self._current_image_index + 1)
            second_page_bg = self._pixbuf_auto_bgs[self._current_image_index + 1]

            auto_bg[0] = (auto_bg[0] + second_page_bg[0]) / 2
            auto_bg[1] = (auto_bg[1] + second_page_bg[1]) / 2
            auto_bg[2] = (auto_bg[2] + second_page_bg[2]) / 2

        return auto_bg

    def do_cacheing(self):
        """Make sure that the correct pixbufs are stored in cache. These
        are (in the current implementation) the current image(s), and
        if cacheing is enabled, also the one or two pixbufs before and
        after the current page. All other pixbufs are deleted and garbage
        collected directly in order to save memory.
        """
        if not self._window.filehandler.file_loaded or self.is_cacheing:
            return

        self.is_cacheing = True
        self._stop_cacheing = False

        # Get list of wanted pixbufs.
        first_wanted = self._current_image_index
        last_wanted = first_wanted + 1
        last_wanted += 1

        if prefs['max pages to cache'] != 0:
            first_wanted -= self._get_backward_step_length()
            last_wanted += self._get_forward_step_length()

            # if the max pages to cache is -1 then cache
            # the entire comic book
            if prefs['max pages to cache'] == -1 or self.get_number_of_pages() <= prefs['max pages to cache']:
                first_wanted = 0
                last_wanted = self.get_number_of_pages()

            elif self.get_number_of_pages() > prefs['max pages to cache']:

                # only cache the max number of pages to cache
                half_cache = (prefs[ 'max pages to cache' ] / 2) - 1
                first_wanted = max(0, first_wanted - half_cache)
                last_wanted = min(self.get_number_of_pages() - 1, \
                                last_wanted + (prefs['max pages to cache'] - (last_wanted - first_wanted)) )

                if (last_wanted - first_wanted) < prefs['max pages to cache']:
                    if last_wanted == self.get_number_of_pages() - 1:
                        first_wanted -= prefs['max pages to cache'] - (last_wanted - first_wanted)

        first_wanted = max(0, first_wanted)
        last_wanted = min(self.get_number_of_pages() - 1, last_wanted)

        # if the pages to be put into cache have not changed then there is nothing
        # to do and no pages would be released
        if ((self.first_wanted == first_wanted) and (self.last_wanted == last_wanted)):
            self.is_cacheing = False
            return
        else:
            self.first_wanted = first_wanted
            self.last_wanted = last_wanted

        wanted_pixbufs = range(first_wanted, last_wanted)

        # Remove old pixbufs.
        for page in set(self._raw_pixbufs) - set(wanted_pixbufs):
            del self._raw_pixbufs[page]

        self.thread_cache_new_pixbufs(wanted_pixbufs)

    def thread_cache_new_pixbufs(self, wanted_pixbufs):
        """Start threaded cache loading.
        """
        cache_thread = threading.Thread(target=self.cache_new_pixbufs, args=(wanted_pixbufs,))
        cache_thread.setDaemon(False)
        cache_thread.start()

    def cache_new_pixbufs(self, wanted_pixbufs):
        """Cache new pixbufs if they are not already cached.
        """
        for wanted in wanted_pixbufs:

            if not self._stop_cacheing:
                self._get_pixbuf(wanted)
            else:
                break

        self.is_cacheing = False

    def next_page(self):
        """Set up filehandler to the next page. Return True if this results
        in a new page.
        """
        if not self._window.filehandler.file_loaded and self._window.filehandler.archive_type is None:
            return False

        old_page = self.get_current_page()
        viewed = self._window.displayed_double() and 2 or 1

        if self.get_current_page() + viewed > self.get_number_of_pages():
            if self._window.filehandler.archive_type is not None:

                if (self._window.slideshow.is_running() and \
                    prefs['slideshow can go to next archive']) or \
                    prefs['auto open next archive']:
                    self._window.filehandler._open_next_archive()

            return False

        self._current_image_index += self._get_forward_step_length()

        return self.get_current_page()

    def previous_page(self):
        """Set up filehandler to the previous page. Return True if this
        results in a new page.
        """
        if not self._window.filehandler.file_loaded and self._window.filehandler.archive_type is None:
            return False

        if self.get_current_page() <= 1:

            if self._window.filehandler.archive_type is not None:

                if (self._window.slideshow.is_running() and \
                    prefs['slideshow can go to next archive']) or \
                    prefs['auto open next archive']:
                    self._window.filehandler._open_previous_archive()

            return False

        old_page = self.get_current_page()
        step = self._get_backward_step_length()
        step = min(self._current_image_index, step)
        self._current_image_index -= step

        if (step == 2 and self.get_virtual_double_page()):
            self._current_image_index += 1

        return self.get_current_page()

    def first_page(self):
        """Set up filehandler to the first page. Return True if this
        results in a new page.
        """
        if not self._window.filehandler.file_loaded:
            return False
        old_page = self.get_current_page()
        self._current_image_index = 0
        return self.get_current_page()

    def last_page(self):
        """Set up filehandler to the last page. Return True if this results
        in a new page.
        """
        if not self._window.filehandler.file_loaded:
            return False
        old_page = self.get_current_page()
        offset = self._window.is_double_page and 2 or 1
        offset = min(self.get_number_of_pages(), offset)
        self._current_image_index = self.get_number_of_pages() - offset
        if (offset == 2 and self.get_virtual_double_page()):
            self._current_image_index += 1
        return self.get_current_page()

    def set_page(self, page_num):
        """Set up filehandler to the page <page_num>. Return True if this
        results in a new page.
        """
        if not 0 < page_num <= self.get_number_of_pages():
            return False

        old_page = self.get_current_page()
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
            self._window.filehandler.archive_type is not None):
            return True

        if (not self._window.is_double_page or
          not prefs['no double page for wide images'] or
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
        self._current_file = None

        self._base_path = None
        self._stop_cacheing = False
        self._image_files = []
        self._current_image_index = None
        self._raw_pixbufs.clear()
        self._name_table.clear()
        self.is_cacheing = False

        tools.garbage_collect()

    def cleanup(self):
        """Run clean-up tasks. Should be called prior to exit."""
        self._stop_cacheing = True

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
        else:
            name = os.path.join(os.path.basename(self._base_path),
                os.path.basename(self._image_files[self._current_image_index]))
        return encoding.to_unicode(name)

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
            thumbnailer = thumbnail_tools.Thumbnailer(store_on_disk=create)
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
        path = self.get_path_to_page(page)
        self._window.filehandler._wait_on_file(path)

# vim: expandtab:sw=4:ts=4

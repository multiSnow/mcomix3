'''image_handler.py - Image handler that takes care of cacheing and giving out images.'''

import os
import traceback

from mcomix.preferences import prefs
from mcomix import i18n
from mcomix import tools
from mcomix import image_tools
from mcomix import thumbnail_tools
from mcomix import constants
from mcomix import callback
from mcomix import log
from mcomix.lib import mt

class ImageHandler(object):

    '''The FileHandler keeps track of images, pages, caches and reads files.

    When the Filehandler's methods refer to pages, they are indexed from 1,
    i.e. the first page is page 1 etc.

    Other modules should *never* read directly from the files pointed to by
    paths given by the FileHandler's methods. The files are not even
    guaranteed to exist at all times since the extraction of archives is
    threaded.
    '''

    def __init__(self, window):

        #: Reference to main window
        self._window = window

        #: Caching thread
        self._thread = mt.ThreadPool(name='image')
        self._lock = mt.Lock()
        self._buf_lock = mt.Lock()

        #: Archive path, if currently opened file is archive
        self._base_path = None
        #: List of image file names, either from extraction or directory
        self._image_files = []
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

        self._window.filehandler.file_available += self._file_available

    def _get_pixbuf(self, index):
        '''Return the pixbuf indexed by <index> from cache.
        Pixbufs not found in cache are fetched from disk first.
        '''
        with self._buf_lock:
            try:
                return self._raw_pixbufs[index]
            except KeyError:
                pass

        self._wait_on_page(index + 1)
        try:
            pixbuf = image_tools.load_pixbuf(self._image_files[index])
            tools.garbage_collect()
        except Exception as e:
            log.error('Could not load pixbuf for page %u: %r', index + 1, e)
            pixbuf = image_tools.MISSING_IMAGE_ICON

        with self._buf_lock:
            self._raw_pixbufs[index] = pixbuf
        return pixbuf

    def get_pixbufs(self, number_of_bufs):
        '''Returns number_of_bufs pixbufs for the image(s) that should be
        currently displayed. This method might fetch images from disk, so make
        sure that number_of_bufs is as small as possible.
        '''
        result = []
        for i in range(number_of_bufs):
            result.append(self._get_pixbuf(self._current_image_index + i))
        return result

    def get_pixbuf_auto_background(self, number_of_bufs): # XXX limited to at most 2 pages
        ''' Returns an automatically calculated background color
        for the current page(s). '''

        pixbufs = self.get_pixbufs(number_of_bufs)

        if len(pixbufs) == 1:
            auto_bg = image_tools.get_most_common_edge_color(pixbufs[0])
        elif len(pixbufs) == 2:
            left, right = pixbufs
            if self._window.is_manga_mode:
                left, right = right, left

            auto_bg = image_tools.get_most_common_edge_color((left, right))
        else:
            assert False, 'Unexpected pixbuf count'

        return auto_bg

    def do_cacheing(self):
        '''Make sure that the correct pixbufs are stored in cache. These
        are (in the current implementation) the current image(s), and
        if cacheing is enabled, also the one or two pixbufs before and
        after the current page. All other pixbufs are deleted and garbage
        collected directly in order to save memory.
        '''

        if not self._lock.acquire(blocking=False):
            return
        try:
            if not self._window.filehandler.file_loaded:
                return

            # Get list of wanted pixbufs.
            wanted_pixbufs = self._ask_for_pages(self.get_current_page())
            if -1 != self._cache_pages:
                # We're not caching everything, remove old pixbufs.
                for index in set(self._raw_pixbufs) - set(wanted_pixbufs):
                    del self._raw_pixbufs[index]
            log.debug('Caching page(s) %s',
                      ' '.join([str(index + 1) for index in wanted_pixbufs]))
            self._wanted_pixbufs = wanted_pixbufs
            # Start caching available images not already in cache.
            wanted_pixbufs = [index for index in wanted_pixbufs
                              if index in self._available_images and not index in self._raw_pixbufs]
            self._thread.map_async(self._cache_pixbuf, wanted_pixbufs)
        finally:
            self._lock.release()

    def _cache_pixbuf(self, index):
        log.debug('Caching page %u', index + 1)
        self._get_pixbuf(index)

    def set_page(self, page_num):
        '''Set up filehandler to the page <page_num>.
        '''
        assert 0 < page_num <= self.get_number_of_pages()
        self._current_image_index = page_num - 1
        self.do_cacheing()

    def set_image_files(self, files):
        # Set list of image file names
        self._image_files[:] = files

    def get_image_files(self):
        # Get list of image file names
        return self._image_files.copy()

    def clear_image_files(self):
        # Clear list of image file names
        self._image_files.clear()

    def clear_raw_pixbufs(self):
        # Clear map of page > Pixbuf
        self._raw_pixbufs.clear()

    def get_current_path(self):
        # Get current image path
        try:
            return self._image_files[self._current_image_index]
        except IndexError:
            return ''

    def get_virtual_double_page(self, page=None):
        '''Return True if the current state warrants use of virtual
        double page mode (i.e. if double page mode is on, the corresponding
        preference is set, and one of the two images that should normally
        be displayed has a width that exceeds its height), or if currently
        on the first page.
        '''
        if page == None:
            page = self.get_current_page()

        if (page == 1 and
            prefs['virtual double page for fitting images'] & constants.SHOW_DOUBLE_AS_ONE_TITLE and
            self._window.filehandler.archive_type is not None):
            return True

        if (not prefs['default double page'] or
            not prefs['virtual double page for fitting images'] & constants.SHOW_DOUBLE_AS_ONE_WIDE or
            page == self.get_number_of_pages()):
            return False

        for page in (page, page + 1):
            if not self.page_is_available(page):
                return False
            pixbuf = self._get_pixbuf(page - 1)
            width, height = pixbuf.get_width(), pixbuf.get_height()
            if prefs['auto rotate from exif']:
                rotation = image_tools.get_implied_rotation(pixbuf)
                assert rotation in (0, 90, 180, 270)
                if rotation in (90, 270):
                    width, height = height, width
            if width > height:
                return True

        return False

    def get_real_path(self):
        '''Return the "real" path to the currently viewed file, i.e. the
        full path to the archive or the full path to the currently
        viewed image.
        '''
        if self._window.filehandler.archive_type is not None:
            return self._window.filehandler.get_path_to_base()
        return self.get_path_to_page()

    def cleanup(self):
        '''Run clean-up tasks. Should be called prior to exit.'''

        self.first_wanted = 0
        self.last_wanted = 1

        self._thread.renew()
        self._base_path = None
        self._image_files.clear()
        self._current_image_index = None
        self._available_images.clear()
        self._raw_pixbufs.clear()
        self._cache_pages = prefs['max pages to cache']

    def page_is_available(self, page=None):
        ''' Returns True if <page> is available and calls to get_pixbufs
        would not block. If <page> is None, the current page(s) are assumed. '''

        if page is None:
            current_page = self.get_current_page()
            if not current_page:
                # Current 'book' has no page.
                return False
            index_list = [ current_page - 1 ]
            if self._window.displayed_double() and current_page < len(self._image_files):
                index_list.append(current_page)
        else:
            index_list = [ page - 1 ]

        for index in index_list:
            if not index in self._available_images:
                return False

        return True

    @callback.Callback
    def page_available(self, page):
        ''' Called whenever a new page becomes available, i.e. the corresponding
        file has been extracted. '''
        log.debug('Page %u is available', page)
        index = page - 1
        assert index not in self._available_images
        self._available_images.add(index)
        # Check if we need to cache it.
        if index in self._wanted_pixbufs or -1 == self._cache_pages:
            self._thread.apply_async(
                self._cache_pixbuf,(index,))

    def _file_available(self, filepaths):
        ''' Called by the filehandler when a new file becomes available. '''
        # Find the page that corresponds to <filepath>
        if not self._image_files:
            return

        available = sorted(filepaths)
        for i, imgpath in enumerate(self._image_files):
            if tools.bin_search(available, imgpath) >= 0:
                self.page_available(i + 1)

    def get_number_of_pages(self):
        '''Return the number of pages in the current archive/directory.'''
        return len(self._image_files)

    def get_current_page(self):
        '''Return the current page number (starting from 1), or 0 if no file is loaded.'''
        if self._current_image_index is not None:
            return self._current_image_index + 1
        else:
            return 0

    def get_path_to_page(self, page=None):
        '''Return the full path to the image file for <page>, or the current
        page if <page> is None.
        '''
        if page is None:
            index = self._current_image_index
        else:
            index = page - 1

        if isinstance(index, int) and 0 <= index < len(self._image_files):
            return self._image_files[index]
        else:
            return None

    def get_page_filename(self, page=None, double=False, manga=False):
        '''Return the filename of the <page>, or the filename of the
        currently viewed page if <page> is None. If <double> is True, return
        a tuple (p, p') where p is the filename of <page> (or the current
        page) and p' is the filename of the page after.
        '''
        if not self.page_is_available():
            return ('', '') if double else ''

        def get_fname(page):
            path = self.get_path_to_page(page)
            return '' if path is None else os.path.basename(path)

        if page is None:
            page = self.get_current_page()

        first = get_fname(page)

        if double:
            second = get_fname(page + 1)
            return (second, first) if manga else (first, second)

        return first

    def get_page_filesize(self, page=None, double=False, manga=False):
        '''Return the filesize of the <page>, or the filesize of the
        currently viewed page if <page> is None. If <double> is True, return
        a tuple (s, s') where s is the filesize of <page> (or the current
        page) and s' is the filesize of the page after.
        '''
        if not self.page_is_available():
            return ('-1','-1') if double else '-1'

        def get_fsize(page):
            path = self.get_path_to_page(page)
            try:
                fsize = 0 if path is None else os.stat(path).st_size
            except OSError:
                fsize = 0
            return tools.format_byte_size(fsize)

        if page is None:
            page = self.get_current_page()

        first = get_fsize(page)

        if double:
            second = get_fsize(page + 1)
            return (second, first) if manga else (first, second)

        return first

    def get_pretty_current_filename(self):
        '''Return a string with the name of the currently viewed file that is
        suitable for printing.
        '''
        if self._window.filehandler.archive_type is not None:
            return i18n.to_unicode(os.path.basename(self._base_path))

        img_file = os.path.abspath(self.get_current_path())
        if not img_file:
            return ''

        name = os.path.join(*tools.splitpath(img_file)[-2:])
        return i18n.to_unicode(name)

    def get_size(self, page=None):
        '''Return a tuple (width, height) with the size of <page>. If <page>
        is None, return the size of the current page.
        '''
        self._wait_on_page(page)

        page_path = self.get_path_to_page(page)
        if page_path is None:
            return (0, 0)

        format, width, height = image_tools.get_image_info(page_path)
        return (width, height)

    def get_mime_name(self, page=None):
        '''Return a string with the name of the mime type of <page>. If
        <page> is None, return the mime type name of the current page.
        '''
        self._wait_on_page(page)

        page_path = self.get_path_to_page(page)
        if page_path is None:
            return None

        format, width, height = image_tools.get_image_info(page_path)
        return format

    def get_thumbnail(self, page=None, width=128, height=128, create=False,
                      nowait=False):
        '''Return a thumbnail pixbuf of <page> that fit in a box with
        dimensions <width>x<height>. Return a thumbnail for the current
        page if <page> is None.

        If <create> is True, and <width>x<height> <= 128x128, the
        thumbnail is also stored on disk.

        If <nowait> is True, don't wait for <page> to be available.
        '''
        if not self._wait_on_page(page, check_only=nowait):
            # Page is not available!
            return None
        path = self.get_path_to_page(page)

        if path == None:
            return None

        try:
            thumbnailer = thumbnail_tools.Thumbnailer(store_on_disk=create,
                                                      size=(width, height))
            return thumbnailer.thumbnail(path)
        except Exception:
            log.debug('Failed to create thumbnail for image "%s":\n%s',
                      path, traceback.format_exc())
            return image_tools.MISSING_IMAGE_ICON

    def _wait_on_page(self, page, check_only=False):
        '''Block the running (main) thread until the file corresponding to
        image <page> has been fully extracted.

        If <check_only> is True, only check (and return status), don't wait.
        '''
        if page is None:
            index = self._current_image_index
        else:
            index = page - 1
        if index in self._available_images:
            # Already extracted!
            return True
        if check_only:
            # Asked for check only...
            return False

        log.debug('Waiting for page %u', page)
        path = self.get_path_to_page(page)
        self._window.filehandler._wait_on_file(path)
        return True

    def _ask_for_pages(self, page):
        '''Ask for pages around <page> to be given priority extraction.
        '''
        total_pages=range(self.get_number_of_pages())

        num_pages = self._cache_pages
        if num_pages < 0:
            # default to 10 pages
            num_pages = min(10, len(total_pages))

        page -= 1
        harf = num_pages // 2 - 1
        start = max(0, page - harf)
        end = start + num_pages
        page_list = list(total_pages[start:end])
        if end > len(total_pages):
            start = page_list[0] - (num_pages - len(page_list))
            page_list.extend(range(max(0, start), page_list[0]))
        page_list.sort()

        # move page before now to the end
        pos = page_list.index(page)
        head = page_list[:pos]
        page_list[:] = page_list[pos:]
        page_list.extend(reversed(head))

        log.debug('Ask for priority extraction around page %u: %s',
                  page + 1, ' '.join([str(n + 1) for n in page_list]))

        files = [self._image_files[index]
                 for index in page_list
                 if index not in self._available_images]

        if files:
            self._window.filehandler._ask_for_files(files)

        return page_list

# vim: expandtab:sw=4:ts=4

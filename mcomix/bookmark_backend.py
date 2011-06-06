"""bookmark_backend.py - Bookmarks handler."""

import os
import cPickle
import gtk
import operator

import constants
import log
import bookmark_menu_item
import callback
import datetime

class __BookmarksStore:

    """The _BookmarksStore is a backend for both the bookmarks menu and dialog.
    Changes in the _BookmarksStore are mirrored in both.
    """

    def __init__(self):
        self._initialized = False
        self._window = None
        self._file_handler = None
        self._image_handler = None
        self._bookmarks = []

        if os.path.isfile(constants.BOOKMARK_PICKLE_PATH):

            try:
                fd = open(constants.BOOKMARK_PICKLE_PATH, 'rb')
                version = cPickle.load(fd)
                packs = cPickle.load(fd)

                for pack in packs:
                    # Handle old bookmarks without date_added attribute
                    if len(pack) == 5:
                        pack = pack + (datetime.datetime.now(),)

                    self.add_bookmark_by_values(*pack)

                fd.close()

            except Exception:
                log.error(_('! Could not parse bookmarks file %s'),
                          constants.BOOKMARK_PICKLE_PATH)
                log.error(_('! Deleting corrupt bookmarks file.'))
                fd.close()
                os.remove(constants.BOOKMARK_PICKLE_PATH)
                self.clear_bookmarks()

    def initialize(self, window):
        """ Initializes references to the main window and file/image handlers. """
        if not self._initialized:
            self._window = window
            self._file_handler = window.filehandler
            self._image_handler = window.imagehandler
            self._initialized = True

            # Update already loaded bookmarks with window and file handler information
            for bookmark in self._bookmarks:
                bookmark._window = window
                bookmark._file_handler = window.filehandler

    def add_bookmark_by_values(self, name, path, page, numpages, archive_type, date_added):
        """Create a bookmark and add it to the list."""
        bookmark = bookmark_menu_item._Bookmark(self._window, self._file_handler,
            name, path, page, numpages, archive_type, date_added)

        self.add_bookmark(bookmark)

    @callback.Callback
    def add_bookmark(self, bookmark):
        """Add the <bookmark> to the list."""
        self._bookmarks.append(bookmark)

    @callback.Callback
    def remove_bookmark(self, bookmark):
        """Remove the <bookmark> from the list."""
        self._bookmarks.remove(bookmark)

    def add_current_to_bookmarks(self):
        """Add the currently viewed page to the list."""
        name = self._image_handler.get_pretty_current_filename()
        path = self._image_handler.get_real_path()
        page = self._image_handler.get_current_page()
        numpages = self._image_handler.get_number_of_pages()
        archive_type = self._file_handler.archive_type
        date_added = datetime.datetime.now()

        same_file_bookmarks = []

        for bookmark in self._bookmarks:
            if bookmark.same_path(path):
                if bookmark.same_page(page):
                    # Do not create identical bookmarks
                    return
                else:
                    same_file_bookmarks.append(bookmark)

        # If the same file was already bookmarked, ask to replace
        # the existing bookmarks before deleting them.
        if len(same_file_bookmarks) > 0:
            response = self._should_replace_bookmarks(same_file_bookmarks, page)

            # Delete old bookmarks
            if response == gtk.RESPONSE_YES:
                for bookmark in same_file_bookmarks:
                    self.remove_bookmark(bookmark)
            # Perform no action
            elif response == gtk.RESPONSE_CANCEL:
                return

        self.add_bookmark_by_values(name, path, page, numpages,
            archive_type, date_added)

    def _should_replace_bookmarks(self, old_bookmarks, new_page):
        """ Present a confirmation dialog to replace old bookmarks.

        @return RESPONSE_YES to create replace bookmarks,
            RESPONSE_NO to create a new bookmark, RESPONSE_CANCEL to abort creating
            a new bookmark.
        """

        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                gtk.BUTTONS_YES_NO)
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.set_default_response(gtk.RESPONSE_YES)

        pages = map(str, sorted(map(operator.attrgetter('_page'), old_bookmarks)))
        dialog.set_markup('<span weight="bold" size="larger">' +
            _('Replace existing bookmarks on page %s?') % ", ".join(pages) +
            '</span>')
        dialog.format_secondary_markup(
            _('The current book already contains marked pages. '
              'Do you want to replace them with a new bookmark on page %d? ') % new_page +
            '\n\n' +
            _('Selecting "No" will create a new bookmark without affecting the other bookmarks.')
        )
        dialog.show_all()
        result = dialog.run()
        dialog.destroy()

        return result

    def clear_bookmarks(self):
        """Remove all bookmarks from the list."""

        while not self.is_empty():
            self.remove_bookmark(self._bookmarks[-1])

    def get_bookmarks(self):
        """Return all the bookmarks in the list."""
        return self._bookmarks

    def is_empty(self):
        """Return True if the bookmark list is empty."""
        return len(self._bookmarks) == 0

    def write_bookmarks_file(self):
        """Store relevant bookmark info in the mcomix directory."""
        fd = open(constants.BOOKMARK_PICKLE_PATH, 'wb')
        cPickle.dump(constants.VERSION, fd, cPickle.HIGHEST_PROTOCOL)

        packs = [bookmark.pack() for bookmark in self._bookmarks]
        cPickle.dump(packs, fd, cPickle.HIGHEST_PROTOCOL)
        fd.close()

# Singleton instance of the bookmarks store.
BookmarksStore = __BookmarksStore()

# vim: expandtab:sw=4:ts=4

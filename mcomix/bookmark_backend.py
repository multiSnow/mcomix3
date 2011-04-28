"""bookmark_backend.py - Bookmarks handler."""

import os
import cPickle
import constants
import bookmark_menu_item
import callback

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
                    self.add_bookmark_by_values(*pack)

                fd.close()

            except Exception:
                print_( _('! Could not parse bookmarks file %s') % constants.BOOKMARK_PICKLE_PATH )
                print_( _('! Deleting corrupt bookmarks file.') )
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

    def add_bookmark_by_values(self, name, path, page, numpages, archive_type):
        """Create a bookmark and add it to the store."""
        bookmark = bookmark_menu_item._Bookmark(self._window, self._file_handler, name, path, page, numpages,
            archive_type)
        self.add_bookmark(bookmark)

    @callback.Callback
    def add_bookmark(self, bookmark):
        """Add the <bookmark> to the store."""
        self._bookmarks.append(bookmark)

    @callback.Callback
    def remove_bookmark(self, bookmark):
        """Remove the <bookmark> from the store."""
        self._bookmarks.remove(bookmark)

    def add_current_to_bookmarks(self):
        """Add the currently viewed file to the store."""
        name = self._image_handler.get_pretty_current_filename()
        path = self._image_handler.get_real_path()
        page = self._image_handler.get_current_page()
        numpages = self._image_handler.get_number_of_pages()
        archive_type = self._file_handler.archive_type

        for bookmark in self._bookmarks:

            if bookmark.same_path(path) and bookmark.same_page(page):
                return

        self.add_bookmark_by_values(name, path, page, numpages,
            archive_type)

    def clear_bookmarks(self):
        """Remove all bookmarks from the store."""

        while not self.is_empty():
            self.remove_bookmark(self._bookmarks[-1])

    def get_bookmarks(self):
        """Return all the bookmarks in the store."""
        return self._bookmarks

    def is_empty(self):
        """Return True if the store is currently empty."""
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

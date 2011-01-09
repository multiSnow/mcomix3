"""bookmark_backend.py - Bookmarks handler."""

import os
import cPickle
import constants
import bookmark_menu_item

class _BookmarksStore:

    """The _BookmarksStore is a backend for both the bookmarks menu and dialog.
    Changes in the _BookmarksStore are mirrored in both.
    """

    def __init__(self, menu, window, file_handler, image_handler):
        self._menu = menu
        self._window = window
        self._file_handler = file_handler
        self._image_handler = image_handler
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

    def add_bookmark_by_values(self, name, path, page, numpages, archive_type):
        """Create a bookmark and add it to the store and the menu."""
        bookmark = bookmark_menu_item._Bookmark(self._window, self._file_handler, name, path, page, numpages,
            archive_type)
        self.add_bookmark(bookmark)

    def add_bookmark(self, bookmark):
        """Add the <bookmark> to the store and the menu."""
        self._bookmarks.append(bookmark)
        self._menu.add_bookmark(bookmark)

    def remove_bookmark(self, bookmark):
        """Remove the <bookmark> from the store and the menu."""
        self._bookmarks.remove(bookmark)
        self._menu.remove_bookmark(bookmark)

    def add_current_to_bookmarks(self):
        """Add the currently viewed file to the store and the menu."""
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
        """Remove all bookmarks from the store and the menu."""

        for bookmark in self._bookmarks:
            self.remove_bookmark(bookmark)

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

# vim: expandtab:sw=4:ts=4

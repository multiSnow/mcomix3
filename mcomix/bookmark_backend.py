"""bookmark_backend.py - Bookmarks handler."""

import os
import cPickle
import gtk
import operator
import datetime

from mcomix.preferences import prefs
from mcomix import constants
from mcomix import log
from mcomix import bookmark_menu_item
from mcomix import callback
from mcomix import i18n

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
            response = prefs['replace bookmark response'] or \
                self._should_replace_bookmarks(same_file_bookmarks, page)

            # Delete old bookmarks
            if response == constants.RESPONSE_REPLACE:
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
                gtk.BUTTONS_NONE)
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(gtk.STOCK_NO, constants.RESPONSE_NEW)
        replace_button = dialog.add_button(gtk.STOCK_YES, constants.RESPONSE_REPLACE)
        dialog.set_default_response(constants.RESPONSE_REPLACE)

        pages = map(str, sorted(map(operator.attrgetter('_page'), old_bookmarks)))
        dialog.set_markup('<span weight="bold" size="larger">' +
            i18n.get_translation().ungettext(
                'Replace existing bookmark on page %s?',
                'Replace existing bookmarks on pages %s?',
                len(pages)
            ) % ", ".join(pages) +
            '</span>')
        dialog.format_secondary_markup(
            _('The current book already contains marked pages. '
              'Do you want to replace them with a new bookmark on page %d? ') % new_page +
            '\n\n' +
            _('Selecting "No" will create a new bookmark without affecting the other bookmarks.')
        )

        checkbox = gtk.CheckButton(_('Do not ask again.'))
        # FIXME: This really shouldn't depend on MessageDialog's internal layout implementation
        labels_box = dialog.get_content_area().get_children()[0].get_children()[1]
        labels_box.pack_end(checkbox, padding=6)

        dialog.show_all()
        replace_button.grab_focus()
        result = dialog.run()
        store_choice = checkbox.get_active()
        dialog.destroy()

        # Remember the selection
        if store_choice and result in (constants.RESPONSE_NEW, constants.RESPONSE_REPLACE):
            prefs['replace bookmark response'] = result

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

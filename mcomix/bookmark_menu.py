"""bookmark_menu.py - Bookmarks menu."""

import gtk

from mcomix import bookmark_backend
from mcomix import bookmark_dialog

class BookmarksMenu(gtk.Menu):

    """BookmarksMenu extends gtk.Menu with convenience methods relating to
    bookmarks. It contains fixed items for adding bookmarks etc. as well
    as dynamic items corresponding to the current bookmarks.
    """

    def __init__(self, ui, window):
        gtk.Menu.__init__(self)

        self._window = window
        self._bookmarks_store = bookmark_backend.BookmarksStore
        self._bookmarks_store.initialize(window)
        self._bookmarks_store.add_bookmark += self.add_bookmark
        self._bookmarks_store.remove_bookmark += self.remove_bookmark

        self._separator = gtk.SeparatorMenuItem()

        self._actiongroup = gtk.ActionGroup('mcomix-bookmarks')
        self._actiongroup.add_actions([
            ('add_bookmark', 'mcomix-add-bookmark', _('Add _Bookmark'),
                '<Control>D', None, self._add_current_to_bookmarks),
            ('edit_bookmarks', None, _('_Edit Bookmarks...'),
                '<Control>B', None, self._edit_bookmarks)])

        action = self._actiongroup.get_action('add_bookmark')
        action.set_accel_group(ui.get_accel_group())

        self.append(action.create_menu_item())
        action = self._actiongroup.get_action('edit_bookmarks')

        action.set_accel_group(ui.get_accel_group())

        self.append(action.create_menu_item())
        self.append(self._separator)

        # Load initial bookmarks from the backend.
        for bookmark in self._bookmarks_store.get_bookmarks():
            self.add_bookmark(bookmark)

        # Prevent calls to show_all accidentally showing the hidden separator.
        self.show_all()
        self.set_no_show_all(True)
        if self._bookmarks_store.is_empty():
            self._separator.hide()

    def add_bookmark(self, bookmark):
        """Add <bookmark> to the menu."""
        bookmark = bookmark.clone()
        self.insert(bookmark, 3)
        bookmark.show()
        self._separator.show()

    def remove_bookmark(self, bookmark):
        """Remove <bookmark> from the menu."""

        # Find the bookmark item corresponding to the passed bookmark
        for menu_bookmark in self.get_children():
            if bookmark == menu_bookmark:
                self.remove(menu_bookmark)
                break

        if self._bookmarks_store.is_empty():
            self._separator.hide()

    def _add_current_to_bookmarks(self, *args):
        """Add the current page to the bookmarks list."""
        self._bookmarks_store.add_current_to_bookmarks()

    def _edit_bookmarks(self, *args):
        """Open the bookmarks dialog."""
        bookmark_dialog._BookmarksDialog(self._window, self._bookmarks_store)

    def set_sensitive(self, loaded):
        """Set the sensitivities of menu items as appropriate if <loaded>
        represents whether a file is currently loaded in the main program
        or not.
        """
        self._actiongroup.get_action('add_bookmark').set_sensitive(loaded)

    def write_bookmarks_file(self):
        """Store relevant bookmark info in the mcomix directory."""
        self._bookmarks_store.write_bookmarks_file()

# vim: expandtab:sw=4:ts=4

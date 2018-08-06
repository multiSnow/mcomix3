"""bookmark_menu.py - Bookmarks menu."""

from gi.repository import Gtk

from mcomix import bookmark_backend
from mcomix import bookmark_dialog

class BookmarksMenu(Gtk.Menu):

    """BookmarksMenu extends Gtk.Menu with convenience methods relating to
    bookmarks. It contains fixed items for adding bookmarks etc. as well
    as dynamic items corresponding to the current bookmarks.
    """

    def __init__(self, ui, window):
        super(BookmarksMenu, self).__init__()

        self._window = window
        self._bookmarks_store = bookmark_backend.BookmarksStore
        self._bookmarks_store.initialize(window)

        self._actiongroup = Gtk.ActionGroup('mcomix-bookmarks')
        self._actiongroup.add_actions([
            ('add_bookmark', 'mcomix-add-bookmark', _('Add _Bookmark'),
                '<Control>D', None, self._add_current_to_bookmarks),
            ('edit_bookmarks', None, _('_Edit Bookmarks...'),
                '<Control>B', None, self._edit_bookmarks)])
        
        action = self._actiongroup.get_action('add_bookmark')
        action.set_accel_group(ui.get_accel_group())
        self.add_button = action.create_menu_item()
        self.append(self.add_button)

        action = self._actiongroup.get_action('edit_bookmarks')
        action.set_accel_group(ui.get_accel_group())
        self.edit_button = action.create_menu_item()
        self.append(self.edit_button)

        # Re-create the bookmarks menu if one was added/removed
        self._create_bookmark_menuitems()
        self._bookmarks_store.add_bookmark += lambda bookmark: self._create_bookmark_menuitems()
        self._bookmarks_store.remove_bookmark += lambda bookmark: self._create_bookmark_menuitems()

        self.show_all()

    def _create_bookmark_menuitems(self):
        # Delete all old menu entries
        for item in self.get_children():
            if item not in (self.add_button, self.edit_button):
                self.remove(item)

        bookmarks = self._bookmarks_store.get_bookmarks()

        # Add separator
        if bookmarks:
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            self.append(separator)

        # Add new bookmarks
        for bookmark in bookmarks:
            self.add_bookmark(bookmark)

    def add_bookmark(self, bookmark):
        """Add <bookmark> to the menu."""
        bookmark = bookmark.clone()
        bookmark.show()
        self.insert(bookmark, 3)

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

# vim: expandtab:sw=4:ts=4

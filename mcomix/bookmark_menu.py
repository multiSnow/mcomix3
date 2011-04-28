"""bookmark_menu.py - Bookmarks menu."""

import gtk
import bookmark_backend
import bookmark_dialog

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
            ('add_bookmark', 'mcomix-add-bookmark', _('_Add bookmark'),
                '<Control>d', None, self._add_current_to_bookmarks),
            ('edit_bookmarks', None, _('_Edit bookmarks...'),
                '<Control>b', None, self._edit_bookmarks),
            ('clear_bookmarks', gtk.STOCK_CLEAR, _('_Clear bookmarks'),
                None, None, self._clear_bookmarks)])

        action = self._actiongroup.get_action('add_bookmark')
        action.set_accel_group(ui.get_accel_group())

        self.append(action.create_menu_item())
        action = self._actiongroup.get_action('edit_bookmarks')

        action.set_accel_group(ui.get_accel_group())

        self.append(action.create_menu_item())
        self.append(self._separator)
        self.append(gtk.SeparatorMenuItem())

        action = self._actiongroup.get_action('clear_bookmarks')
        action.set_accel_group(ui.get_accel_group())
        self.append(action.create_menu_item())

        # Load initial bookmarks from the backend.
        for bookmark in self._bookmarks_store.get_bookmarks():
            self.add_bookmark(bookmark)
        self._update_clear_bookmarks_sensitivity()

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

        self._update_clear_bookmarks_sensitivity()

    def remove_bookmark(self, bookmark):
        """Remove <bookmark> from the menu."""

        # Find the bookmark item corresponding to the passed bookmark
        for menu_bookmark in self.get_children():
            if bookmark == menu_bookmark:
                self.remove(menu_bookmark)
                break

        if self._bookmarks_store.is_empty():
            self._separator.hide()

        self._update_clear_bookmarks_sensitivity()

    def _add_current_to_bookmarks(self, *args):
        """Add the currently viewed file to the bookmarks."""
        self._bookmarks_store.add_current_to_bookmarks()

    def _edit_bookmarks(self, *args):
        """Open the bookmarks dialog."""
        bookmark_dialog._BookmarksDialog(self._window, self._bookmarks_store)

    def _clear_bookmarks(self, *args):
        """Remove all bookmarks, if the user presses 'Yes' in a confirmation
        dialog.
        """
        choice_dialog = gtk.MessageDialog(self._window, 0,
            gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
            _('Clear all bookmarks?'))

        choice_dialog.format_secondary_text(
            _('All stored bookmarks will be removed. Are you sure that you want to continue?'))

        response = choice_dialog.run()
        choice_dialog.destroy()

        if response == gtk.RESPONSE_YES:
            self._bookmarks_store.clear_bookmarks()

    def _update_clear_bookmarks_sensitivity(self):
        """ Enables or disables the "Clear bookmarks" menu item based on how many
        bookmarks are actually available. """

        enabled = not self._bookmarks_store.is_empty()
        self._actiongroup.get_action('clear_bookmarks').set_sensitive(enabled)

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

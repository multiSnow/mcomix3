"""library_control_area.py - The window in the library that contains buttons
and displays info."""

import gtk
import gobject

from mcomix.library.watchlist import WatchListDialog


class _ControlArea(gtk.HBox):

    """The _ControlArea is the bottom area of the library window where
    information is displayed and controls such as buttons reside.
    """

    def __init__(self, library):
        gtk.HBox.__init__(self, False, 12)

        self._library = library
        self.set_border_width(10)

        label = gtk.Label(_('_Search:'))
        label.set_use_underline(True)
        self.pack_start(label, expand=False)

        search_entry = gtk.Entry()
        label.set_mnemonic_widget(search_entry)
        search_entry.set_size_request(400, -1)
        search_entry.connect('activate', self._filter_books)
        search_entry.set_tooltip_text(
            _('Display only those books that have the specified text string in'
              ' their full path. The search is not case sensitive.'))
        self.pack_start(search_entry, expand=False)

        self._open_button = gtk.Button(None, gtk.STOCK_OPEN)
        self._open_button.connect('clicked',
            self._library.book_area.open_selected_book)
        self._open_button.set_tooltip_text(_('Open the selected book.'))
        self._open_button.set_sensitive(False)
        self.pack_end(self._open_button, False, False)

        watchlist_button = gtk.Button(_("_Watch list"))
        watchlist_button.set_image(
            gtk.image_new_from_stock(gtk.STOCK_FIND, gtk.ICON_SIZE_BUTTON))
        watchlist_button.connect('clicked',
            lambda *args: WatchListDialog(self._library))
        watchlist_button.set_tooltip_text(
            _('Open the watchlist management dialog.'))
        self.pack_end(watchlist_button, expand=False)

    def update_info(self, selected):
        """Update the info box using the currently <selected> books from
        the _BookArea.
        """

        if len(selected) > 0:
            self._open_button.set_sensitive(True)
        else:
            self._open_button.set_sensitive(False)

    def _filter_books(self, entry, *args):
        """Display only the books in the current collection whose paths
        contain the string in the gtk.Entry. The string is not
        case-sensitive.
        """
        self._library.filter_string = entry.get_text().decode('utf-8')
        if not self._library.filter_string:
            self._library.filter_string = None
        collection = self._library.collection_area.get_current_collection()
        gobject.idle_add(self._library.book_area.display_covers, collection)

# vim: expandtab:sw=4:ts=4

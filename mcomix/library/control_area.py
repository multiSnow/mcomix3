"""library_control_area.py - The window in the library that contains buttons
and displays info."""

import os
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Pango

from mcomix import i18n
from mcomix import labels
from mcomix.library.watchlist import WatchListDialog

# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1


class _ControlArea(Gtk.HBox):

    """The _ControlArea is the bottom area of the library window where
    information is displayed and controls such as buttons reside.
    """

    def __init__(self, library):
        super(_ControlArea, self).__init__(False, 12)

        self._library = library
        self.set_border_width(10)

        borderbox = Gtk.Frame()
        borderbox.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        borderbox.set_size_request(350, -1)

        insidebox = Gtk.EventBox()
        insidebox.set_border_width(1)
        insidebox.set_state(Gtk.StateType.ACTIVE)

        infobox = Gtk.VBox(homogeneous=False, spacing=5)
        infobox.set_border_width(10)
        self.pack_start(borderbox, True, True, 0)
        borderbox.add(insidebox)
        insidebox.add(infobox)

        self._namelabel = labels.BoldLabel()
        self._namelabel.set_alignment(0, 0.5)
        self._namelabel.set_selectable(True)
        self._namelabel.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        infobox.pack_start(self._namelabel, False, False, 0)

        self._filelabel = Gtk.Label()
        self._filelabel.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._filelabel.set_alignment(0, 0.5)
        infobox.pack_start(self._filelabel, False, False, 0)

        self._dirlabel = Gtk.Label()
        self._dirlabel.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._dirlabel.set_alignment(0, 0.5)
        self._dirlabel.set_selectable(True)
        infobox.pack_start(self._dirlabel, False, False, 0)

        vbox = Gtk.VBox(homogeneous=False, spacing=10)
        vbox.set_size_request(350, -1)
        self.pack_start(vbox, False, False, 0)

        # First line of controls, containing the search box
        hbox = Gtk.HBox(homogeneous=False)
        vbox.pack_start(hbox, True, True, 0)

        label = Gtk.Label(label=_('_Search:'))
        label.set_use_underline(True)
        hbox.pack_start(label, False, False, 0)
        search_entry = Gtk.Entry()
        search_entry.connect('activate', self._filter_books)
        search_entry.set_tooltip_text(
            _('Display only those books that have the specified text string '
              'in their full path. The search is not case sensitive.'))
        hbox.pack_start(search_entry, True, True, 6)
        label.set_mnemonic_widget(search_entry)

        # Last line of controls, containing buttons like 'Open'
        hbox = Gtk.HBox(homogeneous=False, spacing=10)
        vbox.pack_end(hbox, True, True, 0)

        watchlist_button = Gtk.Button(label=_("_Watch list"), use_underline=True)
        watchlist_button.set_always_show_image(True)
        watchlist_button.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_FIND, Gtk.IconSize.BUTTON))
        watchlist_button.set_image_position(Gtk.PositionType.LEFT)
        watchlist_button.connect('clicked',
            lambda *args: WatchListDialog(self._library))
        watchlist_button.set_tooltip_text(
            _('Open the watchlist management dialog.'))
        hbox.pack_start(watchlist_button, True, True, 0)

        self._open_button = Gtk.Button(label=_("_Open list"), use_underline=True)
        self._open_button.set_always_show_image(True)
        self._open_button.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_OPEN, Gtk.IconSize.BUTTON))
        self._open_button.set_image_position(Gtk.PositionType.LEFT)
        self._open_button.connect('clicked',
            self._library.book_area.open_selected_book)
        self._open_button.set_tooltip_text(_('Open the selected book.'))
        self._open_button.set_sensitive(False)
        hbox.pack_end(self._open_button, True, True, 0)

    def update_info(self, selected):
        """Update the info box using the currently <selected> books from
        the _BookArea.
        """

        if selected:
            book_id = self._library.book_area.get_book_at_path(selected[0])
            book = self._library.backend.get_book_by_id(book_id)
        else:
            book = None

        if book:
            name = book.name
            dir_path = os.path.dirname(book.path)
            pages = book.pages
            size = book.size
            last_page = book.get_last_read_page()
            last_date = book.get_last_read_date()
        else:
            name = dir_path = pages = size = last_page = last_date = None

        if len(selected) > 0:
            self._open_button.set_sensitive(True)
        else:
            self._open_button.set_sensitive(False)

        if name is not None:
            self._namelabel.set_text(i18n.to_unicode(name))
            self._namelabel.set_tooltip_text(i18n.to_unicode(name))
        else:
            self._namelabel.set_text('')
            self._namelabel.set_has_tooltip(False)

        infotext = []

        if last_page is not None and pages is not None and last_page != pages:
            infotext.append('%s %d/%d' % (_('Page'), last_page, pages))
        elif pages is not None:
            infotext.append(_('%d pages') % pages)

        if size is not None:
            infotext.append('%.1f MiB' % (size / 1048576.0))

        if (pages is not None and last_page is not None and
            last_date is not None and last_page == pages):
            infotext.append(_('Finished reading on %(date)s, %(time)s') % {
                'date': last_date.strftime('%x'),
                'time': last_date.strftime('%X') })

        self._filelabel.set_text(', '.join(infotext))

        if dir_path is not None:
            self._dirlabel.set_text(i18n.to_unicode(dir_path))
        else:
            self._dirlabel.set_text('')

    def _filter_books(self, entry, *args):
        """Display only the books in the current collection whose paths
        contain the string in the Gtk.Entry. The string is not
        case-sensitive.
        """
        self._library.filter_string = entry.get_text().decode('utf-8')
        if not self._library.filter_string:
            self._library.filter_string = None
        collection = self._library.collection_area.get_current_collection()
        GLib.idle_add(self._library.book_area.display_covers, collection)

# vim: expandtab:sw=4:ts=4

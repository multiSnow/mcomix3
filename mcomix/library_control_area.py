"""library_control_area.py - The window in the library that contains buttons
and displays info."""

import os
import gtk
import gobject
import pango
import i18n
import labels
import strings
import constants
from preferences import prefs

# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1

class _ControlArea(gtk.HBox):

    """The _ControlArea is the bottom area of the library window where
    information is displayed and controls such as buttons reside.
    """

    def __init__(self, library):
        gtk.HBox.__init__(self, False, 12)

        self._library = library
        self.set_border_width(10)

        borderbox = gtk.EventBox()
        borderbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#333'))
        borderbox.set_size_request(350, -1)

        insidebox = gtk.EventBox()
        insidebox.set_border_width(1)
        insidebox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#ddb'))

        infobox = gtk.VBox(False, 5)
        infobox.set_border_width(10)
        self.pack_start(borderbox, False, False)
        borderbox.add(insidebox)
        insidebox.add(infobox)

        self._namelabel = labels.BoldLabel()
        self._namelabel.set_alignment(0, 0.5)
        self._namelabel.set_selectable(True)
        self._namelabel.set_line_wrap(True)
        self._namelabel.set_line_wrap_mode(pango.WRAP_CHAR)
        infobox.pack_start(self._namelabel, False, False)

        self._pageslabel = gtk.Label()
        self._pageslabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self._pageslabel.set_alignment(0, 0.5)
        infobox.pack_start(self._pageslabel, False, False)

        self._filelabel = gtk.Label()
        self._filelabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self._filelabel.set_alignment(0, 0.5)
        infobox.pack_start(self._filelabel, False, False)

        self._dirlabel = gtk.Label()
        self._dirlabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self._dirlabel.set_alignment(0, 0.5)
        self._dirlabel.set_selectable(True)
        infobox.pack_start(self._dirlabel, False, False)

        vbox = gtk.VBox(False, 10)
        self.pack_start(vbox, True, True)

        # First line of controls, containing search box and library cover size.
        hbox = gtk.HBox(False)
        vbox.pack_start(hbox, False, False)

        label = gtk.Label('%s:' % _('_Search'))
        label.set_use_underline(True)
        hbox.pack_start(label, False, False)
        search_entry = gtk.Entry()
        search_entry.connect('activate', self._filter_books)
        search_entry.set_tooltip_text(
            _('Display only those books that have the specified text string in their full path. The search is not case sensitive.'))
        hbox.pack_start(search_entry, True, True, 6)
        label.set_mnemonic_widget(search_entry)

        # TODO enable generic consistent kebindings for zoom in/zoom out/zoom 100.
        label = gtk.Label('%s:' % _('Cover si_ze'))
        label.set_use_underline(True)

        hbox.pack_start(label, False, False, 6)
        adjustment = gtk.Adjustment(prefs['library cover size'], 20, constants.MAX_LIBRARY_COVER_SIZE, 10,
            50, 0)
        cover_size_scale = gtk.HScale(adjustment)
        cover_size_scale.set_size_request(150, -1)
        cover_size_scale.set_draw_value(False)
        cover_size_scale.connect('value_changed', self._change_cover_size)
        label.set_mnemonic_widget(cover_size_scale)
        hbox.pack_start(cover_size_scale, False, False)

        # Second line of controls, containing book sort order.
        hbox = gtk.HBox(False)
        vbox.pack_start(hbox, False, False)
        label = gtk.Label('%s:'% _('Sort order'))
        label.set_alignment(1, 0.5)
        hbox.pack_start(label, True, True, 6)

        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)
        for text, sortkey in ((_('Book name'), constants.SORT_NAME),
                (_('Full path'), constants.SORT_PATH),
                (_('File size'), constants.SORT_SIZE)):
            model.append((text, sortkey))

        self._sort_box = sort_box = gtk.ComboBox(model)
        # Determine default box selection based on preferences.
        iter = model.get_iter_first()
        index = 0
        while iter:
            if model.get_value(iter, 1) == prefs['lib sort key']:
                sort_box.set_active(index)
                break
            else:
                index += 1
                iter = model.iter_next(iter)

        sort_box.connect('changed', self._change_sort)
        cell = gtk.CellRendererText()
        sort_box.pack_start(cell, True)
        sort_box.add_attribute(cell, 'text', 0)
        hbox.pack_start(sort_box, False, False)

        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)
        for text, sortorder in (
                (_('Ascending'), constants.RESPONSE_SORT_ASCENDING),
                (_('Descending'), constants.RESPONSE_SORT_DESCENDING)):
            model.append((text, sortorder))

        self._sortorder_box = sortorder_box = gtk.ComboBox(model)
        # Determine default box selection based on preferences.
        iter = model.get_iter_first()
        index = 0
        while iter:
            if model.get_value(iter, 1) == prefs['lib sort order']:
                sortorder_box.set_active(index)
                break
            else:
                index += 1
                iter = model.iter_next(iter)

        sortorder_box.connect('changed', self._change_sort)
        cell = gtk.CellRendererText()
        sortorder_box.pack_start(cell, True)
        sortorder_box.add_attribute(cell, 'text', 0)
        hbox.pack_start(sortorder_box, False, False)

        # Add empty box to fill space between upper controls and buttons.
        vbox.pack_start(gtk.HBox(), True, True)

        # Last line of controls, containing buttons like 'Open'
        hbox = gtk.HBox(False, 10)
        vbox.pack_start(hbox, False, False)

        self._open_button = gtk.Button(None, gtk.STOCK_OPEN)
        self._open_button.connect('clicked',
            self._library.book_area.open_selected_book)
        self._open_button.set_tooltip_text(_('Open the selected book.'))
        self._open_button.set_sensitive(False)
        hbox.pack_end(self._open_button, False, False)

    def update_info(self, selected):
        """Update the info box using the currently <selected> books from
        the _BookArea.
        """

        if selected:

            book = self._library.book_area.get_book_at_path(selected[0])
            name = self._library.backend.get_book_name(book)
            dir_path = os.path.dirname(
                self._library.backend.get_book_path(book))
            format = self._library.backend.get_book_format(book)
            pages = self._library.backend.get_book_pages(book)
            size = self._library.backend.get_book_size(book)

        else:
            name = dir_path = format = pages = size = None

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

        if pages is not None:
            self._pageslabel.set_text(_('%d pages') % pages)
        else:
            self._pageslabel.set_text('')

        if format is not None and size is not None:
            self._filelabel.set_text('%s, %s' % (strings.ARCHIVE_DESCRIPTIONS[format],
                '%.1f MiB' % (size / 1048576.0)))
        else:
            self._filelabel.set_text('')

        if dir_path is not None:
            self._dirlabel.set_text(i18n.to_unicode(dir_path))
        else:
            self._dirlabel.set_text('')

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

    def _change_cover_size(self, scale):
        """Change the size of the covers in the _BookArea."""
        prefs['library cover size'] = int(scale.get_value())
        collection = self._library.collection_area.get_current_collection()
        gobject.idle_add(self._library.book_area.display_covers, collection)

    def _change_sort(self, combobox, *args):
        """ Changes the books' sorting. """
        active = self._sort_box.get_active()
        if active > -1:
            iter = self._sort_box.get_model().get_iter(active)
            sortkey = self._sort_box.get_model().get_value(iter, 1)
        else:
            sortkey = constants.SORT_PATH

        active = self._sortorder_box.get_active()
        if active > -1:
            iter = self._sortorder_box.get_model().get_iter(active)
            sortorder = self._sortorder_box.get_model().get_value(iter, 1)
        else:
            sortorder = constants.RESPONSE_SORT_ASCENDING

        prefs['lib sort key'] = sortkey
        prefs['lib sort order'] = sortorder

        # Map sort order constants to GTK's own constants
        if sortorder == constants.RESPONSE_SORT_ASCENDING:
            sortorder = gtk.SORT_ASCENDING
        else:
            sortorder = gtk.SORT_DESCENDING

        self._library.book_area.sort_books(sortkey, sortorder)

# vim: expandtab:sw=4:ts=4

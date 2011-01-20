"""library_control_area.py - The window in the library that contains buttons
and displays info."""

import os
import gtk
import gobject
import pango
import encoding
import file_chooser_library_dialog
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
        self._namelabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self._namelabel.set_alignment(0, 0.5)
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
        infobox.pack_start(self._dirlabel, False, False)

        vbox = gtk.VBox(False, 10)
        self.pack_start(vbox, True, True)
        hbox = gtk.HBox(False)
        vbox.pack_start(hbox, False, False)

        label = gtk.Label('%s:' % _('Search'))
        hbox.pack_start(label, False, False)
        search_entry = gtk.Entry()
        search_entry.connect('activate', self._filter_books)
        search_entry.set_tooltip_text(
            _('Display only those books that have the specified text string in their full path. The search is not case sensitive.'))
        hbox.pack_start(search_entry, True, True, 6)

        label = gtk.Label('%s:' % _('Cover size'))
        hbox.pack_start(label, False, False, 6)
        adjustment = gtk.Adjustment(prefs['library cover size'], 20, constants.MAX_LIBRARY_COVER_SIZE, 1,
            10, 0)
        cover_size_scale = gtk.HScale(adjustment)
        cover_size_scale.set_size_request(150, -1)
        cover_size_scale.set_draw_value(False)
        cover_size_scale.connect('value_changed', self._change_cover_size)
        hbox.pack_start(cover_size_scale, False, False)
        vbox.pack_start(gtk.HBox(), True, True)

        hbox = gtk.HBox(False, 10)
        vbox.pack_start(hbox, False, False)
        add_book_button = gtk.Button(_('Add books'))
        add_book_button.set_image(gtk.image_new_from_stock(
            gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON))
        add_book_button.connect('clicked', self._add_books)
        add_book_button.set_tooltip_text(_('Add more books to the library.'))
        hbox.pack_start(add_book_button, False, False)

        add_collection_button = gtk.Button(_('Add folder'))
        add_collection_button.connect('clicked', self._add_collection)
        add_collection_button.set_image(gtk.image_new_from_stock(
            gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON))
        add_collection_button.set_tooltip_text(
            _('Add a new empty collection.'))
        hbox.pack_start(add_collection_button, False, False)

        clean_button = gtk.Button(_('Clean library'))
        clean_button.connect('clicked', self._clean_library)
        clean_button.set_image(gtk.image_new_from_stock(
            gtk.STOCK_CLEAR, gtk.ICON_SIZE_BUTTON))
        clean_button.set_tooltip_text(
            _('Removes no longer existing books from the library.'))
        hbox.pack_start(clean_button, False, False)

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
        self._open_button.set_sensitive(False)

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

        if len(selected) == 1:
            self._open_button.set_sensitive(True)

        if name is not None:
            self._namelabel.set_text(encoding.to_unicode(name))
            self._namelabel.set_tooltip_text(encoding.to_unicode(name))
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
            self._dirlabel.set_text(encoding.to_unicode(dir_path))
        else:
            self._dirlabel.set_text('')

    def _add_books(self, *args):
        """Open up a filechooser dialog from which books can be added to
        the library.
        """
        file_chooser_library_dialog.open_library_filechooser_dialog(self._library)

    def _add_collection(self, *args):
        """Add a new collection to the library, through a dialog."""
        add_dialog = gtk.MessageDialog(None, 0, gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_OK_CANCEL, _('Add new collection?'))
        add_dialog.format_secondary_text(
            _('Please enter a name for the new collection.'))
        add_dialog.set_default_response(gtk.RESPONSE_OK)

        box = gtk.HBox() # To get nice line-ups with the padding.
        add_dialog.vbox.pack_start(box)
        entry = gtk.Entry()
        entry.set_text(_('New collection'))
        entry.set_activates_default(True)
        box.pack_start(entry, True, True, 6)
        box.show_all()

        response = add_dialog.run()
        name = entry.get_text()
        add_dialog.destroy()
        if response == gtk.RESPONSE_OK and name:
            if self._library.backend.add_collection(name):
                collection = self._library.backend.get_collection_by_name(name)
                prefs['last library collection'] = collection
                self._library.collection_area.display_collections()
            else:
                message = _("Could not add a new collection called '%s'.") % (
                    name)
                if (self._library.backend.get_collection_by_name(name)
                  is not None):
                    message = '%s %s' % (message,
                        _('A collection by that name already exists.'))
                self._library.set_status_message(message)

    def _clean_library(self, *args):
        """ Check all books in the library, removing those that no longer exist. """
        dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
            gtk.MESSAGE_WARNING, gtk.BUTTONS_OK_CANCEL,
            _("Do you want to remove non-existent books from the library?"))
        dialog.format_secondary_text(
            _("Books that appear in your library, but no longer exist at their original path, will be removed from the library. This clears books that have been moved or deleted outside of MComix."))
        response = dialog.run()
        dialog.destroy()

        if response == gtk.RESPONSE_OK:
            removed = self._library.backend.clean_collection()

            if removed > 0:
                collection = self._library.collection_area.get_current_collection()
                gobject.idle_add(self._library.book_area.display_covers, collection)

    def _filter_books(self, entry, *args):
        """Display only the books in the current collection whose paths
        contain the string in the gtk.Entry. The string is not
        case-sensitive.
        """
        self._library.filter_string = entry.get_text()
        if not self._library.filter_string:
            self._library.filter_string = None
        collection = self._library.collection_area.get_current_collection()
        gobject.idle_add(self._library.book_area.display_covers, collection)

    def _change_cover_size(self, scale):
        """Change the size of the covers in the _BookArea."""
        prefs['library cover size'] = int(scale.get_value())
        collection = self._library.collection_area.get_current_collection()
        gobject.idle_add(self._library.book_area.display_covers, collection)

# vim: expandtab:sw=4:ts=4

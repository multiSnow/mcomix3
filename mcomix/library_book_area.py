"""library_book_area.py - The window of the library that displays the covers of books."""

import os
import urllib
import gtk
import Image
import ImageDraw
from preferences import prefs
import image_tools
import constants

_dialog = None

# The "All books" collection is not a real collection stored in the library, but is represented by this ID in the
# library's TreeModels.
_COLLECTION_ALL = -1

class _BookArea(gtk.ScrolledWindow):

    """The _BookArea is the central area in the library where the book
    covers are displayed.
    """

    def __init__(self, library):
        gtk.ScrolledWindow.__init__(self)

        self._library = library
        self._stop_update = False
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf, int) # (Cover, ID).
        self._iconview = gtk.IconView(self._liststore)
        self._iconview.set_pixbuf_column(0)
        self._iconview.connect('item_activated', self._book_activated)
        self._iconview.connect('selection_changed', self._selection_changed)
        self._iconview.connect_after('drag_begin', self._drag_begin)
        self._iconview.connect('drag_data_get', self._drag_data_get)
        self._iconview.connect('drag_data_received', self._drag_data_received)
        self._iconview.connect('button_press_event', self._button_press)
        self._iconview.connect('key_press_event', self._key_press)
        self._iconview.modify_base(gtk.STATE_NORMAL, gtk.gdk.Color()) # Black.
        self._iconview.enable_model_drag_source(0,
            [('book', gtk.TARGET_SAME_APP, constants.LIBRARY_DRAG_EXTERNAL_ID)],
            gtk.gdk.ACTION_MOVE)
        self._iconview.drag_dest_set(gtk.DEST_DEFAULT_ALL,
            [('text/uri-list', 0, constants.LIBRARY_DRAG_EXTERNAL_ID)],
            gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self._iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.add(self._iconview)

        self._ui_manager = gtk.UIManager()

        ui_description = """
        <ui>
            <popup name="Popup">
                <menuitem action="open" />
                <menuitem action="open_nowinclose" />
                <separator />
                <menuitem action="remove from collection" />
                <menuitem action="remove from library" />
                <menuitem action="completely remove" />
            </popup>
        </ui>
        """

        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = gtk.ActionGroup('mcomix-library-book-area')
        actiongroup.add_actions([
            ('open', gtk.STOCK_OPEN, _('_Open'), None, None,
                self.open_selected_book),
            ('open_nowinclose', gtk.STOCK_OPEN, 
                _('Open _without closing library'), None, None,
                self.open_selected_book_noclose),
            ('remove from collection', gtk.STOCK_REMOVE,
                _('Remove from this _collection'), None, None,
                self._remove_books_from_collection),
            ('remove from library', gtk.STOCK_DELETE,
                _('Remove from the _library'), None, None,
                self._remove_books_from_library),
            ('completely remove', gtk.STOCK_DELETE,
                _('Completey _remove'), None, None,
                self._completely_remove_book)
                ])

        self._ui_manager.insert_action_group(actiongroup, 0)

    def close(self):
        """Run clean-up tasks for the _BookArea prior to closing."""

        # We must unselect all or we will trigger selection_changed events
        # when closing with multiple books selected.
        self._iconview.unselect_all()
        # We must (for some reason) explicitly clear the ListStore in
        # order to not leak memory.
        self._liststore.clear()

    def display_covers(self, collection):
        """Display the books in <collection> in the IconView."""

        self._stop_update = False # To handle new re-entry during update.
        self._liststore.clear()

        if collection == _COLLECTION_ALL: # The "All" collection is virtual.
            collection = None

        for i, book in enumerate(self._library.backend.get_books_in_collection(
          collection, self._library.filter_string)):
            self._add_book(book)
            while gtk.events_pending():
                gtk.main_iteration(False)

            if self._stop_update:
                return

        self._stop_update = True

    def stop_update(self):
        """Signal that the updating of book covers should stop."""
        self._stop_update = True

    def remove_book_at_path(self, path):
        """Remove the book at <path> from the ListStore (and thus from
        the _BookArea).
        """
        iterator = self._liststore.get_iter(path)
        self._liststore.remove(iterator)

    def get_book_at_path(self, path):
        """Return the book ID corresponding to the IconView <path>."""
        iterator = self._liststore.get_iter(path)
        return self._liststore.get_value(iterator, 1)

    def get_book_path(self, book):
        """Return the <path> to the book from the ListStore.
        """
        return self._liststore.get_iter(book)

    def open_selected_book(self, *args):
        """Open the currently selected book."""
        selected = self._iconview.get_selected_items()
        if not selected:
            return
        path = selected[0]
        self._book_activated(self._iconview, path, False)

    def open_selected_book_noclose(self, *args):
        """Open the currently selected book, keeping the library open."""
        selected = self._iconview.get_selected_items()
        if not selected:
            return
        path = selected[0]
        self._book_activated(self._iconview, path, True)

    def _add_book(self, book):
        """Add the <book> to the ListStore (and thus to the _BookArea)."""

        pixbuf = self._library.backend.get_book_cover(book)

        if pixbuf is None:
            pixbuf = constants.MISSING_IMAGE_ICON

        # The ratio (0.67) is just above the normal aspect ratio for books.
        pixbuf = image_tools.fit_in_rectangle(pixbuf,
            int(0.67 * prefs['library cover size']),
            prefs['library cover size'], True)
        pixbuf = image_tools.add_border(pixbuf, 1, 0xFFFFFFFF)
        self._liststore.append([pixbuf, book])

    def _book_activated(self, iconview, path, keep_library_open=False):
        """Open the book at the (liststore) <path>."""
        book = self.get_book_at_path(path)
        self._library.open_book(book, keep_library_open=keep_library_open)

    def _selection_changed(self, iconview):
        """Update the displayed info in the _ControlArea when a new book
        is selected.
        """
        selected = iconview.get_selected_items()
        self._library.control_area.update_info(selected)

    def _remove_books_from_collection(self, *args):
        """Remove the currently selected book(s) from the current collection,
        and thus also from the _BookArea.
        """
        collection = self._library.collection_area.get_current_collection()
        if collection == _COLLECTION_ALL:
            return
        selected = self._iconview.get_selected_items()
        for path in selected:
            book = self.get_book_at_path(path)
            self._library.backend.remove_book_from_collection(book, collection)
            self.remove_book_at_path(path)
        coll_name = self._library.backend.get_collection_name(collection)
        self._library.set_status_message(
            _("Removed %(num)d book(s) from '%(collection)s'.") %
            {'num': len(selected), 'collection': coll_name})

    def _remove_books_from_library(self, request_response=True, *args):
        """Remove the currently selected book(s) from the library, and thus
        also from the _BookArea, if the user clicks 'Yes' in a dialog.
        """

        if request_response:
            choice_dialog = gtk.MessageDialog(self._library, 0,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
                _('Remove books from the library?'))
            choice_dialog.format_secondary_text(
                _('The selected books will be removed from the library (but the original files will be untouched). Are you sure that you want to continue?'))
            response = choice_dialog.run()
            choice_dialog.destroy()

        if not request_response or (request_response and response == gtk.RESPONSE_YES):
            selected = self._iconview.get_selected_items()

            for path in selected:
                book = self.get_book_at_path(path)
                self._library.backend.remove_book(book)
                self.remove_book_at_path(path)

            self._library.set_status_message(
                _('Removed %d book(s) from the library.') % len(selected))

    def _completely_remove_book(self, request_response=True, *args):
        """Remove the currently selected book(s) from the library and the
        hard drive, if the user clicks 'Yes' in a dialog.
        """

        if request_response:

            choice_dialog = gtk.MessageDialog(self._library, 0,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
                _('Remove books from the library?'))
            choice_dialog.format_secondary_text(
                _('The selected books will be removed from the library and permanently deleted. Are you sure that you want to continue?'))
            response = choice_dialog.run()
            choice_dialog.destroy()

        # if no request is needed or the user has told us they definitely want to delete the book
        if not request_response or (request_response and response == gtk.RESPONSE_YES):

            self._remove_books_from_library(False)

            # get the array of currently selected books in the book window
            selected_books = self._iconview.get_selected_items()

            for book in selected_books:

                # find the database id and path for each selected book
                book_id = self._library.book_area.get_book_at_path(book)
                book_path = self._library.backend.get_book_path(book_id)

                try:
                    # try to delete the book.
                    # this can throw an exception if the path points to folder instead
                    # of a single file
                    os.remove(book_path)

                except Exception:

                    print _('! Could not remove file "%s"') % book_path

                while gtk.events_pending():
                    gtk.main_iteration(False)


    def _button_press(self, iconview, event):
        """Handle mouse button presses on the _BookArea."""
        path = iconview.get_path_at_pos(int(event.x), int(event.y))
        if path is None:
            return
        # For some reason we don't always get an item_activated event when
        # double-clicking on an icon, so we handle it explicitly here.
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self._book_activated(iconview, path)
        if event.button == 3:
            if not iconview.path_is_selected(path):
                iconview.unselect_all()
                iconview.select_path(path)
            if len(iconview.get_selected_items()) > 1:
                self._ui_manager.get_action('/Popup/open').set_sensitive(False)
            else:
                self._ui_manager.get_action('/Popup/open').set_sensitive(True)
            if (self._library.collection_area.get_current_collection() ==
              _COLLECTION_ALL):
                self._ui_manager.get_action(
                    '/Popup/remove from collection').set_sensitive(False)
            else:
                self._ui_manager.get_action(
                    '/Popup/remove from collection').set_sensitive(True)
            self._ui_manager.get_widget('/Popup').popup(None, None, None,
                event.button, event.time)

    def _key_press(self, iconview, event):
        """Handle key presses on the _BookArea."""
        if event.keyval == gtk.keysyms.Delete:
            self._remove_books_from_collection()

    def _drag_begin(self, iconview, context):
        """Create a cursor image for drag-n-drop from the library.

        This method relies on implementation details regarding PIL's
        drawing functions and default font to produce good looking results.
        If those are changed in a future release of PIL, this method might
        produce bad looking output (e.g. non-centered text).

        It's also used with connect_after() to overwrite the cursor
        automatically created when using enable_model_drag_source(), so in
        essence it's a hack, but at least it works.
        """
        icon_path = iconview.get_cursor()[0]
        num_books = len(iconview.get_selected_items())
        book = self.get_book_at_path(icon_path)

        cover = self._library.backend.get_book_cover(book)
        if cover is None:
            cover = constants.MISSING_IMAGE_ICON

        cover = cover.scale_simple(max(0, cover.get_width() // 2),
            max(0, cover.get_height() // 2), gtk.gdk.INTERP_TILES)
        cover = image_tools.add_border(cover, 1, 0xFFFFFFFF)
        cover = image_tools.add_border(cover, 1)

        if num_books > 1:
            cover_width = cover.get_width()
            cover_height = cover.get_height()
            pointer = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
                max(30, cover_width + 15), max(30, cover_height + 10))
            pointer.fill(0x00000000)
            cover.composite(pointer, 0, 0, cover_width, cover_height, 0, 0,
            1, 1, gtk.gdk.INTERP_TILES, 255)
            im = Image.new('RGBA', (30, 30), 0x00000000)
            draw = ImageDraw.Draw(im)
            draw.polygon(
                (8, 0, 20, 0, 28, 8, 28, 20, 20, 28, 8, 28, 0, 20, 0, 8),
                fill=(0, 0, 0), outline=(0, 0, 0))
            draw.polygon(
                (8, 1, 20, 1, 27, 8, 27, 20, 20, 27, 8, 27, 1, 20, 1, 8),
                fill=(128, 0, 0), outline=(255, 255, 255))
            text = str(num_books)
            draw.text((15 - (6 * len(text) // 2), 9), text,
                fill=(255, 255, 255))
            circle = image_tools.pil_to_pixbuf(im)
            circle.composite(pointer, max(0, cover_width - 15),
                max(0, cover_height - 20), 30, 30, max(0, cover_width - 15),
                max(0, cover_height - 20), 1, 1, gtk.gdk.INTERP_TILES, 255)
        else:
            pointer = cover

        context.set_icon_pixbuf(pointer, -5, -5)

    def _drag_data_get(self, iconview, context, selection, *args):
        """Fill the SelectionData with (iconview) paths for the dragged books
        formatted as a string with each path separated by a comma.
        """
        paths = iconview.get_selected_items()
        text = ','.join([str(path[0]) for path in paths])
        selection.set('text/plain', 8, text)

    def _drag_data_received(self, widget, context, x, y, data, *args):
        """Handle drag-n-drop events ending on the book area (i.e. from
        external apps like the file manager).
        """
        uris = data.get_uris()
        if not uris:
            return
        paths = []
        for uri in uris:
            if uri.startswith('file://localhost/'):  # Correctly formatted.
                uri = uri[16:]
            elif uri.startswith('file:///'):  # Nautilus etc.
                uri = uri[7:]
            elif uri.startswith('file:/'):  # Xffm etc.
                uri = uri[5:]
            path = urllib.url2pathname(uri)
            paths.append(path)
        collection = self._library.collection_area.get_current_collection()
        collection_name = self._library.backend.get_collection_name(collection)
        self._library.add_books(paths, collection_name)

# vim: expandtab:sw=4:ts=4

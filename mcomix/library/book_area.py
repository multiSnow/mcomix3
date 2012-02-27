"""library_book_area.py - The window of the library that displays the covers of books."""

import os
import urllib
import Queue
import threading
import itertools
import gtk
import gobject
import Image
import ImageDraw

from mcomix.preferences import prefs
from mcomix import file_chooser_library_dialog
from mcomix import image_tools
from mcomix import constants
from mcomix import portability
from mcomix import callback
from mcomix import i18n
from mcomix import status
from mcomix import log
from mcomix.library.pixbuf_cache import get_pixbuf_cache

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
        self._cache = get_pixbuf_cache()
        self._stop_update = False
        self._thumbnail_threads = None

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        # Store Cover, book ID, book path, book size, date added to library
        # The SORT_ constants must correspond to the correct column here,
        # i.e. SORT_SIZE must be 3, since 3 is the size column in the ListStore.
        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf,
                gobject.TYPE_INT, gobject.TYPE_STRING, gobject.TYPE_INT64,
                gobject.TYPE_STRING)
        self._liststore.set_sort_func(constants.SORT_NAME, self._sort_by_name, None)
        self._liststore.connect('row-inserted', self._icon_added)
        self._iconview = gtk.IconView(self._liststore)
        self._iconview.set_pixbuf_column(0)
        self._iconview.connect('item_activated', self._book_activated)
        self._iconview.connect('selection_changed', self._selection_changed)
        self._iconview.connect_after('drag_begin', self._drag_begin)
        self._iconview.connect('drag_data_get', self._drag_data_get)
        self._iconview.connect('drag_data_received', self._drag_data_received)
        self._iconview.connect('button_press_event', self._button_press)
        self._iconview.connect('key_press_event', self._key_press)
        self._iconview.connect('popup_menu', self._popup_menu)
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
        self._tooltipstatus = status.TooltipStatusHelper(self._ui_manager,
            self._library.get_status_bar())

        ui_description = """
        <ui>
            <popup name="library books">
                <menuitem action="_title" />
                <separator />
                <menuitem action="open" />
                <menuitem action="open keep library" />
                <separator />
                <menuitem action="add" />
                <separator />
                <menuitem action="remove from collection" />
                <menuitem action="remove from library" />
                <menuitem action="completely remove" />
                <separator />
                <menuitem action="copy to clipboard" />
                <separator />
                <menu action="sort">
                    <menuitem action="by name" />
                    <menuitem action="by path" />
                    <menuitem action="by size" />
                    <menuitem action="by date added" />
                    <separator />
                    <menuitem action="ascending" />
                    <menuitem action="descending" />
                </menu>
                <menu action="cover size">
                    <menuitem action="huge" />
                    <menuitem action="large" />
                    <menuitem action="normal" />
                    <menuitem action="small" />
                    <menuitem action="tiny" />
                    <separator />
                    <menuitem action="custom" />
                </menu>
            </popup>
        </ui>
        """

        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = gtk.ActionGroup('mcomix-library-book-area')
        # General book actions
        actiongroup.add_actions([
            ('_title', None, _('Library books'), None, None,
                None),
            ('open', gtk.STOCK_OPEN, _('_Open'), None,
                _('Opens the selected books for viewing.'),
                self.open_selected_book),
            ('open keep library', gtk.STOCK_OPEN,
                _('Open _without closing library'), None,
                _('Opens the selected books, but keeps the library window open.'),
                self.open_selected_book_noclose),
            ('add', gtk.STOCK_ADD, _('_Add...'), '<Ctrl><Shift>a',
                _('Add more books to the library.'),
                lambda *args: file_chooser_library_dialog.open_library_filechooser_dialog(self._library)),
            ('remove from collection', gtk.STOCK_REMOVE,
                _('Remove from this _collection'), None,
                _('Removes the selected books from the current collection.'),
                self._remove_books_from_collection),
            ('remove from library', gtk.STOCK_REMOVE,
                _('Remove from the _library'), None,
                _('Completely removes the selected books from the library.'),
                self._remove_books_from_library),
            ('completely remove', gtk.STOCK_DELETE,
                _('_Remove and delete from disk'), None,
                _('Deletes the selected books from disk.'),
                self._completely_remove_book),
            ('copy to clipboard', gtk.STOCK_COPY,
                _('_Copy'), None,
                _('Copies the selected book\'s path to clipboard.'),
                self._copy_selected),
            ('sort', None, _('_Sort'), None,
                _('Changes the sort order of the library.'), None),
            ('cover size', None, _('Cover si_ze'), None,
                _('Changes the book cover size.'), None)
       ])
        # Sorting the view
        actiongroup.add_radio_actions([
            ('by name', None, _('Book name'), None, None, constants.SORT_NAME),
            ('by path', None, _('Full path'), None, None, constants.SORT_PATH),
            ('by size', None, _('File size'), None, None, constants.SORT_SIZE),
            ('by date added', None, _('Date added'), None, None, constants.SORT_LAST_MODIFIED)],
            prefs['lib sort key'], self._sort_changed)
        actiongroup.add_radio_actions([
            ('ascending', gtk.STOCK_SORT_ASCENDING, _('Ascending'), None, None,
                constants.SORT_ASCENDING),
            ('descending', gtk.STOCK_SORT_DESCENDING, _('Descending'), None, None,
                constants.SORT_DESCENDING)],
            prefs['lib sort order'], self._sort_changed)

        # Library cover size
        actiongroup.add_radio_actions([
            ('huge', None, _('Huge') + '  (%dpx)' % constants.SIZE_HUGE,
                None, None, constants.SIZE_HUGE),
            ('large', None, _('Large') + '  (%dpx)' % constants.SIZE_LARGE,
                None, None, constants.SIZE_LARGE),
            ('normal', None, _('Normal') + '  (%dpx)' % constants.SIZE_NORMAL,
                None, None, constants.SIZE_NORMAL),
            ('small', None, _('Small') + '  (%dpx)' % constants.SIZE_SMALL,
                None, None, constants.SIZE_SMALL),
            ('tiny', None, _('Tiny') + '  (%dpx)' % constants.SIZE_TINY,
                None, None, constants.SIZE_TINY),
            ('custom', None, _('Custom...'), None, None, 0)],
            prefs['library cover size']
                if prefs['library cover size'] in (constants.SIZE_HUGE,
                    constants.SIZE_LARGE, constants.SIZE_NORMAL,
                    constants.SIZE_SMALL, constants.SIZE_TINY)
                else 0,
            self._book_size_changed)

        self._ui_manager.insert_action_group(actiongroup, 0)
        library.add_accel_group(self._ui_manager.get_accel_group())

    def close(self):
        """Run clean-up tasks for the _BookArea prior to closing."""

        self.stop_update()

        # We must unselect all or we will trigger selection_changed events
        # when closing with multiple books selected.
        self._iconview.unselect_all()
        # We must (for some reason) explicitly clear the ListStore in
        # order to not leak memory.
        self._liststore.clear()

    def display_covers(self, collection_id):
        """Display the books in <collection_id> in the IconView."""

        adjustment = self.get_vadjustment()
        if adjustment:
            adjustment.set_value(0)

        self.stop_update()
        self._liststore.clear()

        collection = self._library.backend.get_collection_by_id(collection_id)

        # Get all books that need to be added.
        # This cannot be executed threaded due to SQLite connections
        # being bound to the thread that created them.
        books = collection.get_books(self._library.filter_string)
        filler = self._get_empty_thumbnail()
        for book in books:

            # Fill the liststore with a filler pixbuf.
            iter = self._liststore.append([filler,
                book.id, book.path.encode('utf-8'), book.size, book.added])

        # Sort the list store based on preferences.
        if prefs['lib sort order'] == constants.SORT_ASCENDING:
            sortorder = gtk.SORT_ASCENDING
        else:
            sortorder = gtk.SORT_DESCENDING
        self.sort_books(prefs['lib sort key'], sortorder)

        # Queue thumbnail loading
        book_queue = Queue.Queue()
        iter = self._liststore.get_iter_first()
        while iter:
            path = self._liststore.get_value(iter, 2)
            wrapper = IterWrapper(iter, self._liststore)
            self._path_about_to_be_removed += wrapper.invalidate
            book_queue.put((wrapper, path.decode('utf-8')))

            iter = self._liststore.iter_next(iter)

        # Start the thumbnail threads.
        self._thumbnail_threads = [ threading.Thread(target=self._pixbuf_worker,
            args=(book_queue,)) for _ in range(prefs['max threads']) ]
        for thread in self._thumbnail_threads:
            thread.setDaemon(True)
            thread.start()

    def stop_update(self):
        """Signal that the updating of book covers should stop."""
        self._stop_update = True

        if self._thumbnail_threads:
            for thread in self._thumbnail_threads:
                thread.join()

        # All update threads should have finished now.
        self._stop_update = False

    def remove_book_at_path(self, path):
        """Remove the book at <path> from the ListStore (and thus from
        the _BookArea).
        """
        self._path_about_to_be_removed(path)
        iterator = self._liststore.get_iter(path)
        filepath = self._liststore.get_value(iterator, 2)
        self._liststore.remove(iterator)
        self._cache.invalidate(filepath)

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
        self._book_activated(self._iconview, selected, False)

    def open_selected_book_noclose(self, *args):
        """Open the currently selected book, keeping the library open."""
        selected = self._iconview.get_selected_items()
        if not selected:
            return
        self._book_activated(self._iconview, selected, True)

    def sort_books(self, sort_key, sort_order=gtk.SORT_ASCENDING):
        """ Orders the list store based on the key passed in C{sort_key}.
        Should be one of the C{SORT_} constants from L{constants}.
        """
        self._liststore.set_sort_column_id(sort_key, sort_order)

    def _sort_changed(self, old, current):
        """ Called whenever the sorting options changed. """
        name = current.get_name()
        if name == 'by name':
            prefs['lib sort key'] = constants.SORT_NAME
        elif name == 'by path':
            prefs['lib sort key'] = constants.SORT_PATH
        elif name == 'by size':
            prefs['lib sort key'] = constants.SORT_SIZE
        elif name == 'by date added':
            prefs['lib sort key'] = constants.SORT_LAST_MODIFIED

        if name == 'ascending':
            prefs['lib sort order'] = constants.SORT_ASCENDING
        elif name == 'descending':
            prefs['lib sort order'] = constants.SORT_DESCENDING

        if prefs['lib sort order'] == constants.SORT_ASCENDING:
            order = gtk.SORT_ASCENDING
        else:
            order = gtk.SORT_DESCENDING

        self.sort_books(prefs['lib sort key'], order)

    def _sort_by_name(self, treemodel, iter1, iter2, user_data):
        """ Compares two books based on their file name without the
        path component. """
        path1 = self._liststore.get_value(iter1, 2)
        path2 = self._liststore.get_value(iter2, 2)

        # Catch None values from liststore
        if path1 is None:
            return 1
        elif path2 is None:
            return -1

        name1 = os.path.split(path1.decode('utf-8'))[1].lower()
        name2 = os.path.split(path2.decode('utf-8'))[1].lower()

        if name1 == name2:
            return 0
        else:
            if name1 < name2:
                return -1
            else:
                return 1

    def _icon_added(self, model, path, iter, *args):
        """ Justifies the alignment of all cell renderers when new data is
        added to the model. """
        # FIXME Setting the alignment for all cells each time something
        # is added seems rather wasteful. Find better way to do this.
        for cell in self._iconview.get_cells():
            cell.set_alignment(0.5, 0.5)

    def _book_size_changed(self, old, current):
        """ Called when library cover size changes. """
        old_size = prefs['library cover size']
        name = current.get_name()
        if name == 'huge':
            prefs['library cover size'] = constants.SIZE_HUGE
        elif name == 'large':
            prefs['library cover size'] = constants.SIZE_LARGE
        elif name == 'normal':
            prefs['library cover size'] = constants.SIZE_NORMAL
        elif name == 'small':
            prefs['library cover size'] = constants.SIZE_SMALL
        elif name == 'tiny':
            prefs['library cover size'] = constants.SIZE_TINY
        elif name == 'custom':
            dialog = gtk.MessageDialog(self._library, gtk.DIALOG_DESTROY_WITH_PARENT,
                    gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
            dialog.set_markup('<span weight="bold" size="larger">' +
                _('Set library cover size') +
                '</span>')

            # Add adjustment scale
            adjustment = gtk.Adjustment(prefs['library cover size'], 20,
                    constants.MAX_LIBRARY_COVER_SIZE, 10, 25, 0)
            cover_size_scale = gtk.HScale(adjustment)
            cover_size_scale.set_size_request(200, -1)
            cover_size_scale.set_digits(0)
            cover_size_scale.set_draw_value(True)
            cover_size_scale.set_value_pos(gtk.POS_LEFT)
            for mark in (constants.SIZE_HUGE, constants.SIZE_LARGE,
                    constants.SIZE_NORMAL, constants.SIZE_SMALL,
                    constants.SIZE_TINY):
                cover_size_scale.add_mark(mark, gtk.POS_TOP, None)

            dialog.get_message_area().pack_end(cover_size_scale)
            dialog.show_all()
            response = dialog.run()
            size = int(adjustment.get_value())
            dialog.destroy()

            if response == gtk.RESPONSE_OK:
                prefs['library cover size'] = size

        if prefs['library cover size'] != old_size:
            self._cache.invalidate_all()
            collection = self._library.collection_area.get_current_collection()
            gobject.idle_add(self.display_covers, collection)

    def _pixbuf_worker(self, books):
        """ Run by a worker thread to generate the thumbnail for a list
        of books. """
        while not self._stop_update and not books.empty():
            try:
                iter, path = books.get_nowait()
            except Queue.Empty:
                break

            pixbuf = self._get_pixbuf(path)
            gobject.idle_add(self._pixbuf_finished, (iter, pixbuf))
            books.task_done()

    def _pixbuf_finished(self, pixbuf_info):
        """ Executed when a pixbuf was created, to actually insert the pixbuf
        into the view store. <pixbuf_info> is a tuple containing (index, pixbuf). """

        iterwrapper, pixbuf = pixbuf_info
        iter = iterwrapper.iter

        if iter and self._liststore.iter_is_valid(iter):
            self._liststore.set(iter, 0, pixbuf)

        # Remove this idle handler.
        return 0

    def _get_pixbuf(self, path):
        """ Get or create the thumbnail for the selected book at <path>. """
        if self._cache.exists(path):
            return self._cache.get(path)
        else:
            pixbuf = self._library.backend.get_book_thumbnail(path) or constants.MISSING_IMAGE_ICON
            # The ratio (0.67) is just above the normal aspect ratio for books.
            pixbuf = image_tools.fit_in_rectangle(pixbuf,
                int(0.67 * prefs['library cover size']),
                prefs['library cover size'], True)
            pixbuf = image_tools.add_border(pixbuf, 1, 0xFFFFFFFF)
            self._cache.add(path, pixbuf)

            return pixbuf

    def _get_empty_thumbnail(self):
        """ Create an empty filler pixmap. """
        pixbuf = gtk.gdk.Pixbuf(colorspace=gtk.gdk.COLORSPACE_RGB,
                has_alpha=True,
                bits_per_sample=8,
                width=int(0.67 * prefs['library cover size']), height=prefs['library cover size'])

        # Make the pixbuf transparent.
        pixbuf.fill(0)

        return pixbuf

    def _book_activated(self, iconview, paths, keep_library_open=False):
        """Open the book at the (liststore) <path>."""
        if not isinstance(paths, list):
            paths = [ paths ]

        books = [ self.get_book_at_path(path) for path in paths ]
        self._library.open_book(books, keep_library_open=keep_library_open)

    def _selection_changed(self, iconview):
        """Update the displayed info in the _ControlArea when a new book
        is selected.
        """
        selected = iconview.get_selected_items()
        self._library.control_area.update_info(selected)

    def _remove_books_from_collection(self, *args):
        """Remove the currently selected books from the current collection,
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

    def _remove_books_from_library(self, *args):
        """Remove the currently selected books from the library, and thus
        also from the _BookArea.
        """

        selected = self._iconview.get_selected_items()

        for path in selected:
            book = self.get_book_at_path(path)
            self._library.backend.remove_book(book)
            self.remove_book_at_path(path)

        msg = i18n.get_translation().ngettext(
            'Removed %d book from the library.',
            'Removed %d books from the library.',
            len(selected))
        self._library.set_status_message(msg % len(selected))

    def _completely_remove_book(self, request_response=True, *args):
        """Remove the currently selected books from the library and the
        hard drive.
        """

        if request_response:

            choice_dialog = gtk.MessageDialog(self._library, 0,
                gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
            choice_dialog.set_markup('<span weight="bold" size="larger">' +
                _('Remove books from the library?') +
                '</span>'
            )
            choice_dialog.format_secondary_text(
                _('The selected books will be removed from the library and '
                  'permanently deleted. Are you sure that you want to continue?')
            )
            choice_dialog.set_default_response(gtk.RESPONSE_YES)
            response = choice_dialog.run()
            choice_dialog.destroy()

        # if no request is needed or the user has told us they definitely want to delete the book
        if not request_response or (request_response and response == gtk.RESPONSE_YES):

            # get the array of currently selected books in the book window
            selected_books = self._iconview.get_selected_items()
            book_ids = [ self.get_book_at_path(book) for book in selected_books ]
            paths = [ self._library.backend.get_book_path(book_id) for book_id in book_ids ]

            # Remove books from library
            self._remove_books_from_library()

            # Remove from the harddisk
            for book_path in paths:
                try:
                    # try to delete the book.
                    # this can throw an exception if the path points to folder instead
                    # of a single file
                    os.remove(book_path)
                except Exception:
                    log.error(_('! Could not remove file "%s"') % book_path)

    def _copy_selected(self, *args):
        """ Copies the currently selected item to clipboard. """
        paths = self._iconview.get_selected_items()
        if len(paths) == 1:
            model = self._iconview.get_model()
            iter = model.get_iter(paths[0])
            path = model.get_value(iter, 2).decode('utf-8')
            pixbuf = model.get_value(iter, 0)

            self._library._window.clipboard.copy(path, pixbuf)

    def _button_press(self, iconview, event):
        """Handle mouse button presses on the _BookArea."""
        path = iconview.get_path_at_pos(int(event.x), int(event.y))

        # For some reason we don't always get an item_activated event when
        # double-clicking on an icon, so we handle it explicitly here.
        if event.type == gtk.gdk._2BUTTON_PRESS and path is not None:
            self._book_activated(iconview, path)

        if event.button == 3:
            if path and not iconview.path_is_selected(path):
                iconview.unselect_all()
                iconview.select_path(path)

            self._popup_book_menu()

    def _popup_book_menu(self):
        """ Shows the book panel popup menu. """

        selected = self._iconview.get_selected_items()
        books_selected = len(selected) > 0
        collection = self._library.collection_area.get_current_collection()
        is_collection_all = collection == _COLLECTION_ALL

        for action in ('open', 'open keep library', 'remove from library', 'completely remove'):
            self._set_sensitive(action, books_selected)

        self._set_sensitive('_title', False)
        self._set_sensitive('add', collection is not None)
        self._set_sensitive('remove from collection', books_selected and not is_collection_all)
        self._set_sensitive('copy to clipboard', len(selected) == 1)

        menu = self._ui_manager.get_widget('/library books')
        menu.popup(None, None, None, 3, gtk.get_current_event_time())

    def _set_sensitive(self, action, sensitive):
        """ Enables the popup menu action <action> based on <sensitive>. """

        control = self._ui_manager.get_action('/library books/' + action)
        control.set_sensitive(sensitive)

    def _key_press(self, iconview, event):
        """Handle key presses on the _BookArea."""
        if event.keyval == gtk.keysyms.Delete:
            self._remove_books_from_collection()

    def _popup_menu(self, iconview):
        """ Called when the menu key is pressed to open the popup menu. """
        self._popup_book_menu()
        return True

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

        uris = [ portability.normalize_uri(uri) for uri in uris ]
        paths = [ urllib.url2pathname(uri).decode('utf-8') for uri in uris ]

        collection = self._library.collection_area.get_current_collection()
        collection_name = self._library.backend.get_collection_name(collection)
        self._library.add_books(paths, collection_name)

    @callback.Callback
    def _path_about_to_be_removed(self, path):
        """ This will be called before a liststore path is about to be removed.
        Used to invalidate the IterWrapper before PyGTK gets a chance to access
        the invalid iterator. """
        pass


class IterWrapper(object):
    """ This is a security wrapper for TreeIterator that gets notified when an
    item is about to be deleted from the TreeControl's list store. It then
    invalidates its iterator to prevent PyGTK from causing a segmentation fault
    by accessing the iterator. """

    def __init__(self, iter, liststore):
        self.iter = iter
        self.liststore = liststore

    def invalidate(self, path):
        if self.iter:
            iter_path = self.liststore.get_path(self.iter)
            if iter_path == path:
                self.iter = None

# vim: expandtab:sw=4:ts=4

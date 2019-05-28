'''library_book_area.py - The window of the library that displays the covers of books.'''

import os
import urllib
from gi.repository import Gdk, GdkPixbuf, Gtk, GLib, GObject
import PIL.Image as Image
import PIL.ImageDraw as ImageDraw

from mcomix.preferences import prefs
from mcomix import thumbnail_view
from mcomix import file_chooser_library_dialog
from mcomix import image_tools
from mcomix import constants
from mcomix import portability
from mcomix import i18n
from mcomix import status
from mcomix import log
from mcomix import message_dialog
from mcomix import tools
from mcomix.library.pixbuf_cache import get_pixbuf_cache

_dialog = None

# The "All books" collection is not a real collection stored in the library, but is represented by this ID in the
# library's TreeModels.
_COLLECTION_ALL = -1


class _BookArea(Gtk.ScrolledWindow):

    '''The _BookArea is the central area in the library where the book
    covers are displayed.
    '''

    # Thumbnail border width in pixels.
    _BORDER_SIZE = 1

    def __init__(self, library):
        super(_BookArea, self).__init__()

        self._library = library
        self._cache = get_pixbuf_cache()

        self._library.backend.book_added_to_collection += self._new_book_added

        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # Store Cover, book ID, book path, book size, date added to library,
        # is thumbnail loaded?

        # The SORT_ constants must correspond to the correct column here,
        # i.e. SORT_SIZE must be 3, since 3 is the size column in the ListStore.
        self._liststore = Gtk.ListStore(GdkPixbuf.Pixbuf,
                GObject.TYPE_INT, GObject.TYPE_STRING, GObject.TYPE_INT64,
                GObject.TYPE_STRING, GObject.TYPE_BOOLEAN)
        self._liststore.set_sort_func(constants.SORT_NAME, self._sort_by_name, None)
        self._liststore.set_sort_func(constants.SORT_PATH, self._sort_by_path, None)
        self.set_sort_order()
        self._iconview = thumbnail_view.ThumbnailIconView(
            self._liststore,
            1, # UID
            0, # pixbuf
            5, # status
        )
        self._iconview.generate_thumbnail = self._get_pixbuf
        self._iconview.connect('item_activated', self._book_activated)
        self._iconview.connect('selection_changed', self._selection_changed)
        self._iconview.connect_after('drag_begin', self._drag_begin)
        self._iconview.connect('drag_data_get', self._drag_data_get)
        self._iconview.connect('drag_data_received', self._drag_data_received)
        self._iconview.connect('button_press_event', self._button_press)
        self._iconview.connect('key_press_event', self._key_press)
        self._iconview.connect('popup_menu', self._popup_menu)
        self._iconview.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new('book', Gtk.TargetFlags.SAME_APP,
                                 constants.LIBRARY_DRAG_EXTERNAL_ID)],
            Gdk.DragAction.MOVE)
        self._iconview.drag_dest_set(
            Gtk.DestDefaults.ALL,
            [Gtk.TargetEntry.new('text/uri-list', 0,
                                 constants.LIBRARY_DRAG_EXTERNAL_ID)],
            Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        self._iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.add(self._iconview)

        self._iconview.set_margin(0)
        self._iconview.set_row_spacing(0)
        self._iconview.set_column_spacing(0)

        self._ui_manager = Gtk.UIManager()
        self._tooltipstatus = status.TooltipStatusHelper(self._ui_manager,
            self._library.get_status_bar())

        ui_description = '''
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
                <separator />
                <menuitem action="copy path to clipboard" />
                <menuitem action="copy cover to clipboard" />
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
        '''

        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = Gtk.ActionGroup(name='mcomix-library-book-area')
        # General book actions
        actiongroup.add_actions([
            ('_title', None, _('Library books'), None, None, None),
            ('open', Gtk.STOCK_OPEN, _('_Open'), None,
             _('Opens the selected books for viewing.'),
             self.open_selected_book),
            ('open keep library', Gtk.STOCK_OPEN,
             _('Open _without closing library'), None,
             _('Opens the selected books, but keeps the library window open.'),
             self.open_selected_book_noclose),
            ('add', Gtk.STOCK_ADD, _('_Add...'), '<Ctrl><Shift>a',
             _('Add more books to the library.'),
             lambda *args: file_chooser_library_dialog.open_library_filechooser_dialog(self._library)),
            ('remove from collection', Gtk.STOCK_REMOVE,
             _('Remove from this _collection'), None,
             _('Removes the selected books from the current collection.'),
             self._remove_books_from_collection),
            ('remove from library', Gtk.STOCK_REMOVE,
             _('Remove from the _library'), None,
             _('Removes the selected books from the library.'),
             self._remove_books_from_library),
            ('copy path to clipboard', Gtk.STOCK_COPY,
             _('_Copy'), None,
             _('Copies the selected book\'s path to clipboard.'),
             self._copy_selected_path),
            ('copy cover to clipboard', '',
             _('_Copy Cover'), None,
             _('Copies the selected book\'s cover to clipboard.'),
             self._copy_selected_cover),
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
            ('by date added', None, _('Date added'), None, None, constants.SORT_LAST_MODIFIED)
        ],
                                      prefs['lib sort key'], self._sort_changed
        )
        actiongroup.add_radio_actions([
            ('ascending', Gtk.STOCK_SORT_ASCENDING, _('Ascending'), None, None,
             constants.SORT_ASCENDING),
            ('descending', Gtk.STOCK_SORT_DESCENDING, _('Descending'), None, None,
             constants.SORT_DESCENDING)
        ],
                                      prefs['lib sort order'], self._sort_changed
        )

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
            ('custom', None, _('Custom...'), None, None, 0)
        ],
                                      prefs['library cover size']
                                      if prefs['library cover size'] in (
                                              constants.SIZE_HUGE,
                                              constants.SIZE_LARGE, constants.SIZE_NORMAL,
                                              constants.SIZE_SMALL, constants.SIZE_TINY
                                      )
                                      else 0,
                                      self._book_size_changed
        )

        self._ui_manager.insert_action_group(actiongroup, 0)
        library.add_accel_group(self._ui_manager.get_accel_group())

    def close(self):
        '''Run clean-up tasks for the _BookArea prior to closing.'''

        self.stop_update()

        # We must unselect all or we will trigger selection_changed events
        # when closing with multiple books selected.
        self._iconview.unselect_all()
        # We must (for some reason) explicitly clear the ListStore in
        # order to not leak memory.
        self._liststore.clear()

    def display_covers(self, collection_id):
        '''Display the books in <collection_id> in the IconView.'''

        adjustment = self.get_vadjustment()
        if adjustment:
            adjustment.set_value(0)

        self.stop_update()
        # Temporarily detach model to speed up updates
        self._iconview.set_model(None)
        self._liststore.clear()

        collection = self._library.backend.get_collection_by_id(collection_id)
        books = collection.get_books(self._library.filter_string)
        self.add_books(books)

        # Re-attach model here
        self._iconview.set_model(self._liststore)

    def stop_update(self):
        '''Signal that the updating of book covers should stop.'''
        self._iconview.stop_update()

    def add_books(self, books):
        ''' Adds new book covers to the icon view.
        @param books: List of L{_Book} instances. '''
        filler = self._get_empty_thumbnail()

        for book in books:
            # Fill the liststore with a filler pixbuf.
            self._liststore.append([filler, book.id,
                                    book.path,
                                    book.size, book.added, False])

    def _new_book_added(self, book, collection):
        ''' Callback function for L{LibraryBackend.book_added}. '''
        if collection is None:
            collection = _COLLECTION_ALL

        if (collection == self._library.collection_area.get_current_collection() or
            self._library.collection_area.get_current_collection() == _COLLECTION_ALL):
            # Make sure not to show a book twice when COLLECTION_ALL is selected
            # and the book is added to another collection, triggering this event.
            if self.is_book_displayed(book):
                return

            # If the current view is filtered, only draw new books that match the filter
            if not (self._library.filter_string and
                    self._library.filter_string.lower() not in book.name.lower()):
                self.add_books([book])

    def is_book_displayed(self, book):
        ''' Returns True when the current view contains the book passed.
        @param book: L{_Book} instance. '''
        if not book:
            return False

        for row in self._liststore:
            if row[1] == book.id:
                return True

        return False

    def remove_book_at_path(self, path):
        '''Remove the book at <path> from the ListStore (and thus from
        the _BookArea).
        '''
        iterator = self._liststore.get_iter(path)
        filepath = self._liststore.get_value(iterator, 2)
        self._liststore.remove(iterator)
        self._cache.invalidate(filepath)

    def get_book_at_path(self, path):
        '''Return the book ID corresponding to the IconView <path>.'''
        iterator = self._liststore.get_iter(path)
        return self._liststore.get_value(iterator, 1)

    def get_book_path(self, book):
        '''Return the <path> to the book from the ListStore.
        '''
        return self._liststore.get_iter(book)

    def open_selected_book(self, *args):
        '''Open the currently selected book.'''
        selected = self._iconview.get_selected_items()
        if not selected:
            return
        self._book_activated(self._iconview, selected, False)

    def open_selected_book_noclose(self, *args):
        '''Open the currently selected book, keeping the library open.'''
        selected = self._iconview.get_selected_items()
        if not selected:
            return
        self._book_activated(self._iconview, selected, True)

    def set_sort_order(self):
        ''' Orders the list store based on the key passed in C{sort_key}.
        Should be one of the C{SORT_} constants from L{constants}.
        '''
        if prefs['lib sort order'] == constants.SORT_ASCENDING:
            sortorder = Gtk.SortType.ASCENDING
        else:
            sortorder = Gtk.SortType.DESCENDING

        self._liststore.set_sort_column_id(prefs['lib sort key'], sortorder)

    def _sort_changed(self, old, current):
        ''' Called whenever the sorting options changed. '''
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

        self.set_sort_order()

    def _sort_by_name(self, treemodel, iter1, iter2, user_data):
        ''' Compares two books based on their file name without the
        path component. '''
        path1 = self._liststore.get_value(iter1, 2)
        path2 = self._liststore.get_value(iter2, 2)

        # Catch None values from liststore
        if path1 is None:
            return 1
        elif path2 is None:
            return -1

        name1 = os.path.split(path1)[1].lower()
        name2 = os.path.split(path2)[1].lower()

        return tools.alphanumeric_compare(name1, name2)

    def _sort_by_path(self, treemodel, iter1, iter2, user_data):
        ''' Compares two books based on their full path, in natural order. '''
        path1 = self._liststore.get_value(iter1, 2)
        path2 = self._liststore.get_value(iter2, 2)
        return tools.alphanumeric_compare(path1, path2)

    def _book_size_changed(self, old, current):
        ''' Called when library cover size changes. '''
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
            dialog = message_dialog.MessageDialog(
                self._library,
                flags=Gtk.DialogFlags.DESTROY_WITH_PARENT,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK)
            dialog.set_auto_destroy(False)
            dialog.set_text(_('Set library cover size'))

            # Add adjustment scale
            adjustment = Gtk.Adjustment(value=prefs['library cover size'], lower=20,
                                        upper=constants.MAX_LIBRARY_COVER_SIZE,
                                        step_increment=10, page_increment=25)
            cover_size_scale = Gtk.HScale(adjustment=adjustment)
            cover_size_scale.set_size_request(200, -1)
            cover_size_scale.set_digits(0)
            cover_size_scale.set_draw_value(True)
            cover_size_scale.set_value_pos(Gtk.PositionType.LEFT)
            for mark in (constants.SIZE_HUGE, constants.SIZE_LARGE,
                         constants.SIZE_NORMAL, constants.SIZE_SMALL,
                         constants.SIZE_TINY):
                cover_size_scale.add_mark(mark, Gtk.PositionType.TOP, None)

            dialog.get_message_area().pack_end(cover_size_scale, True, True, 0)
            response = dialog.run()
            size = int(adjustment.get_value())
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                prefs['library cover size'] = size

        if prefs['library cover size'] != old_size:
            self._cache.invalidate_all()
            collection = self._library.collection_area.get_current_collection()
            GLib.idle_add(self.display_covers, collection)

    def _pixbuf_size(self, border_size=_BORDER_SIZE):
        # Don't forget the extra pixels for the border!
        # The ratio (0.67) is just above the normal aspect ratio for books.
        return (int(0.67 * prefs['library cover size']) + 2 * border_size,
                prefs['library cover size'] + 2 * border_size)

    def _get_pixbuf(self, uid):
        ''' Get or create the thumbnail for the selected book <uid>. '''
        assert isinstance(uid, int)
        book = self._library.backend.get_book_by_id(uid)
        if self._cache.exists(book.path):
            pixbuf = self._cache.get(book.path)
        else:
            width, height = self._pixbuf_size(border_size=0)
            # cover thumbnail of book
            cover = self._library.backend.get_book_thumbnail(book.path)
            if not cover:
                cover = image_tools.MISSING_IMAGE_ICON
            cover = image_tools.fit_in_rectangle(
                cover, width - 2, height - 2, scale_up=True)
            cover = image_tools.add_border(cover, 1, 0xFFFFFFFF)
            src_width, src_height = cover.get_width(), cover.get_height()
            # icon background of book
            pixbuf = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, True, 8, width, height)
            pixbuf.fill(0x00000000) # full transparency
            offset_x = (width - src_width) // 2
            offset_y = (height - src_height) // 2
            cover.copy_area(0, 0, src_width, src_height,
                            pixbuf, offset_x, offset_y)
            self._cache.add(book.path, pixbuf)

        # Display indicator of having finished reading the book.
        # This information isn't cached in the pixbuf cache
        # as it changes frequently.

        # Anything smaller than 50px means that the status icon will not fit
        if prefs['library cover size'] < 50:
            return pixbuf

        last_read_page = book.get_last_read_page()
        if last_read_page is None or last_read_page != book.pages:
            return pixbuf

        # Composite icon on the lower right corner of the book cover pixbuf.
        book_pixbuf = self.render_icon(Gtk.STOCK_APPLY, Gtk.IconSize.LARGE_TOOLBAR)
        translation_x = pixbuf.get_width() - book_pixbuf.get_width() - 1
        translation_y = pixbuf.get_height() - book_pixbuf.get_height() - 1
        book_pixbuf.composite(pixbuf, translation_x, translation_y,
                              book_pixbuf.get_width(), book_pixbuf.get_height(),
                              translation_x, translation_y,
                              1.0, 1.0, GdkPixbuf.InterpType.NEAREST, 0xFF)

        return pixbuf

    def _get_empty_thumbnail(self):
        ''' Create an empty filler pixmap. '''
        width, height = self._pixbuf_size()
        pixbuf = GdkPixbuf.Pixbuf.new(colorspace=GdkPixbuf.Colorspace.RGB,
                                      has_alpha=True,
                                      bits_per_sample=8,
                                      width=width, height=height)

        # Make the pixbuf transparent.
        pixbuf.fill(0)

        return pixbuf

    def _book_activated(self, iconview, paths, keep_library_open=False):
        '''Open the book at the (liststore) <path>.'''
        if not isinstance(paths, list):
            paths = [paths]

        if not keep_library_open:
            # Necessary to prevent a deadlock at exit when trying to "join" the
            # worker thread.
            self.stop_update()
        books = [self.get_book_at_path(path) for path in paths]
        self._library.open_book(books, keep_library_open=keep_library_open)

    def _selection_changed(self, iconview):
        '''Update the displayed info in the _ControlArea when a new book
        is selected.
        '''
        selected = iconview.get_selected_items()
        self._library.control_area.update_info(selected)

    def _remove_books_from_collection(self, *args):
        '''Remove the currently selected books from the current collection,
        and thus also from the _BookArea.
        '''
        collection = self._library.collection_area.get_current_collection()
        if collection == _COLLECTION_ALL:
            return
        selected = self._iconview.get_selected_items()
        self._library.backend.begin_transaction()
        for path in selected:
            book = self.get_book_at_path(path)
            self._library.backend.remove_book_from_collection(book, collection)
            self.remove_book_at_path(path)
        self._library.backend.end_transaction()

        coll_name = self._library.backend.get_collection_name(collection)
        message = i18n.get_translation().ngettext(
            'Removed %(num)d book from "%(collection)s".',
            'Removed %(num)d books from "%(collection)s".',
            len(selected))
        self._library.set_status_message(
            message % {'num': len(selected), 'collection': coll_name})

    def _remove_books_from_library(self, *args):
        '''Remove the currently selected books from the library, and thus
        also from the _BookArea.
        '''

        selected = self._iconview.get_selected_items()
        self._library.backend.begin_transaction()

        for path in selected:
            book = self.get_book_at_path(path)
            self._library.backend.remove_book(book)
            self.remove_book_at_path(path)

        self._library.backend.end_transaction()

        msg = i18n.get_translation().ngettext(
            'Removed %d book from the library.',
            'Removed %d books from the library.',
            len(selected))
        self._library.set_status_message(msg % len(selected))

    def _copy_selected_cover(self, *args):
        ''' Copies the currently selected item's path to clipboard. '''
        paths = self._iconview.get_selected_items()
        if len(paths) == 1:
            model = self._iconview.get_model()
            iter = model.get_iter(paths[0])
            cover_pixbuf = model.get_value(iter, 0)

            self._library._window.clipboard.copy_cover(cover_pixbuf)

    def _copy_selected_path(self, *args):
        ''' Copies the currently selected item to clipboard. '''
        paths = self._iconview.get_selected_items()
        if len(paths) == 1:
            model = self._iconview.get_model()
            iter = model.get_iter(paths[0])
            book_path = model.get_value(iter, 2)

            self._library._window.clipboard.copy_book_path(book_path)

    def _button_press(self, iconview, event):
        '''Handle mouse button presses on the _BookArea.'''
        path = iconview.get_path_at_pos(int(event.x), int(event.y))

        if event.button == 3:
            if path and not iconview.path_is_selected(path):
                iconview.unselect_all()
                iconview.select_path(path)

            self._popup_book_menu()

    def _popup_book_menu(self):
        ''' Shows the book panel popup menu. '''

        selected = self._iconview.get_selected_items()
        books_selected = len(selected) > 0
        collection = self._library.collection_area.get_current_collection()
        is_collection_all = collection == _COLLECTION_ALL

        for action in ('open', 'open keep library', 'remove from library'):
            self._set_sensitive(action, books_selected)

        self._set_sensitive('_title', False)
        self._set_sensitive('add', collection is not None)
        self._set_sensitive('remove from collection', books_selected and not is_collection_all)
        self._set_sensitive('copy path to clipboard', len(selected) == 1)
        self._set_sensitive('copy cover to clipboard', len(selected) == 1)

        menu = self._ui_manager.get_widget('/library books')
        menu.popup(None, None, None, None, 3, Gtk.get_current_event_time())

    def _set_sensitive(self, action, sensitive):
        ''' Enables the popup menu action <action> based on <sensitive>. '''

        control = self._ui_manager.get_action('/library books/' + action)
        control.set_sensitive(sensitive)

    def _key_press(self, iconview, event):
        '''Handle key presses on the _BookArea.'''
        if event.keyval == Gdk.KEY_Delete:
            self._remove_books_from_collection()

    def _popup_menu(self, iconview):
        ''' Called when the menu key is pressed to open the popup menu. '''
        self._popup_book_menu()
        return True

    def _drag_begin(self, iconview, context):
        '''Create a cursor image for drag-n-drop from the library.

        This method relies on implementation details regarding PIL's
        drawing functions and default font to produce good looking results.
        If those are changed in a future release of PIL, this method might
        produce bad looking output (e.g. non-centered text).

        It's also used with connect_after() to overwrite the cursor
        automatically created when using enable_model_drag_source(), so in
        essence it's a hack, but at least it works.
        '''
        icon_path = iconview.get_cursor()[1]
        num_books = len(iconview.get_selected_items())
        book = self.get_book_at_path(icon_path)

        cover = self._library.backend.get_book_cover(book)
        if cover is None:
            cover = image_tools.MISSING_IMAGE_ICON

        cover = cover.scale_simple(max(0, cover.get_width() // 2),
            max(0, cover.get_height() // 2), prefs['scaling quality'])
        cover = image_tools.add_border(cover, 1, 0xFFFFFFFF)
        cover = image_tools.add_border(cover, 1)

        if num_books > 1:
            cover_width = cover.get_width()
            cover_height = cover.get_height()
            pointer = GdkPixbuf.Pixbuf.new(colorspace=GdkPixbuf.Colorspace.RGB,
                                           has_alpha=True, bits_per_sample=8,
                                           width=max(30, cover_width + 15),
                                           height=max(30, cover_height + 10))
            pointer.fill(0x00000000)
            cover.composite(pointer, 0, 0, cover_width, cover_height, 0, 0,
            1, 1, prefs['scaling quality'], 255)
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
            circle.composite(
                pointer, max(0, cover_width - 15),
                max(0, cover_height - 20), 30, 30, max(0, cover_width - 15),
                max(0, cover_height - 20), 1, 1, prefs['scaling quality'], 255)
        else:
            pointer = cover

        Gtk.drag_set_icon_pixbuf(context, pointer, -5, -5)

    def _drag_data_get(self, iconview, context, selection, *args):
        '''Fill the SelectionData with (iconview) paths for the dragged books
        formatted as a string with each path separated by a comma.
        '''
        paths = iconview.get_selected_items()
        text = ','.join([str(path[0]) for path in paths])

        #FIXME
        #tmp workaround for GTK bug, 2018
        #sending as bytearray instead of text
        #see also _drag_data_received in collection_area

        selection.set(selection.get_target(), -1, text.encode())
        #selection.set_text(text, -1)

    def _drag_data_received(self, widget, context, x, y, data, *args):
        '''Handle drag-n-drop events ending on the book area (i.e. from
        external apps like the file manager).
        '''
        uris = data.get_uris()
        if not uris:
            return

        uris = [portability.normalize_uri(uri) for uri in uris]
        paths = [urllib.request.url2pathname(uri) for uri in uris]

        collection = self._library.collection_area.get_current_collection()
        collection_name = self._library.backend.get_collection_name(collection)
        self._library.add_books(paths, collection_name)


# vim: expandtab:sw=4:ts=4

"""library.py - Comic book library."""

import os
import gc
import urllib
from xml.sax.saxutils import escape as xmlescape

import gtk
import gobject
import pango
import Image
import ImageDraw

import archive
import encoding
import filechooser
import labels
import librarybackend
from preferences import prefs
import image

_dialog = None
# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1
_DRAG_EXTERNAL_ID, _DRAG_BOOK_ID, _DRAG_COLLECTION_ID = range(3)


class _LibraryDialog(gtk.Window):
    
    """The library window. Automatically creates and uses a new
    librarybackend.LibraryBackend when opened.
    """

    def __init__(self, file_handler):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.resize(prefs['lib window width'], prefs['lib window height'])
        self.set_title(_('Library'))
        self.connect('delete_event', self.close)
        
        self.filter_string = None
        self._file_handler = file_handler
        self._statusbar = gtk.Statusbar()
        self._statusbar.set_has_resize_grip(True)
        self.backend = librarybackend.LibraryBackend()
        self.book_area = _BookArea(self)
        self.control_area = _ControlArea(self)
        self.collection_area = _CollectionArea(self)
        
        table = gtk.Table(2, 2, False)
        table.attach(self.collection_area, 0, 1, 0, 1, gtk.FILL,
            gtk.EXPAND|gtk.FILL)
        table.attach(self.book_area, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL,
            gtk.EXPAND|gtk.FILL)
        table.attach(self.control_area, 0, 2, 1, 2, gtk.EXPAND|gtk.FILL,
            gtk.FILL)
        table.attach(self._statusbar, 0, 2, 2, 3, gtk.FILL, gtk.FILL)
        self.add(table)
        self.show_all()

    def open_book(self, book):
        """Open the book with ID <book>."""
        path = self.backend.get_book_path(book)
        if path is None:
            return
        self.close()
        self._file_handler.open_file(path)
                
    def set_status_message(self, message):
        """Set a specific message on the statusbar, replacing whatever was
        there earlier.
        """
        self._statusbar.pop(0)
        self._statusbar.push(0, ' %s' % encoding.to_unicode(message))

    def close(self, *args):
        """Close the library and do required cleanup tasks."""
        prefs['lib window width'], prefs['lib window height'] = self.get_size()
        self.book_area.stop_update()
        self.backend.close()
        self.book_area.close()
        filechooser.close_library_filechooser_dialog()
        _close_dialog()

    def add_books(self, paths, collection_name=None):
        """Add the books at <paths> to the library. If <collection_name>
        is not None, it is the name of a (new or existing) collection the
        books should be put in.
        """
        if collection_name is None:
            collection = None
        else:
            collection = self.backend.get_collection_by_name(collection_name)
            if collection is None: # Collection by that name doesn't exist.
                self.backend.add_collection(collection_name)
                collection = self.backend.get_collection_by_name(
                    collection_name)

        _AddBooksProgressDialog(self, paths, collection)
        if collection is not None:
            prefs['last library collection'] = collection
        self.collection_area.display_collections()


class _CollectionArea(gtk.ScrolledWindow):
    
    """The _CollectionArea is the sidebar area in the library where
    different collections are displayed in a tree.
    """
    
    def __init__(self, library):
        gtk.ScrolledWindow.__init__(self)
        self._library = library
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self._treestore = gtk.TreeStore(str, int) # (Name, ID) of collections.
        self._treeview = gtk.TreeView(self._treestore)
        self._treeview.connect('cursor_changed', self._collection_selected)
        self._treeview.connect('drag_data_received', self._drag_data_received)
        self._treeview.connect('drag_motion', self._drag_motion)
        self._treeview.connect_after('drag_begin', self._drag_begin)
        self._treeview.connect('button_press_event', self._button_press)
        self._treeview.connect('key_press_event', self._key_press)
        self._treeview.connect('row_activated', self._expand_or_collapse_row)
        self._treeview.set_headers_visible(False)
        self._treeview.set_rules_hint(True)
        self._set_acceptable_drop(True)
        self._treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
            [('collection', gtk.TARGET_SAME_WIDGET, _DRAG_COLLECTION_ID)],
            gtk.gdk.ACTION_MOVE)
        cellrenderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(None, cellrenderer, markup=0)
        self._treeview.append_column(column)
        self.add(self._treeview)
        
        self._ui_manager = gtk.UIManager()
        ui_description = """
        <ui>
            <popup name="Popup">
                <menuitem action="rename" />
                <menuitem action="duplicate" />
                <separator />
                <menuitem action="remove" />
            </popup>
        </ui>
        """
        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = gtk.ActionGroup('comix-library-collection-area')
        actiongroup.add_actions([
            ('rename', None, _('Rename...'), None, None,
                self._rename_collection),
            ('duplicate', gtk.STOCK_COPY, _('Duplicate collection'), None, None,
                self._duplicate_collection),
            ('remove', gtk.STOCK_REMOVE, _('Remove collection...'), None, None,
                self._remove_collection)])
        self._ui_manager.insert_action_group(actiongroup, 0)
        
        self.display_collections()

    def get_current_collection(self):
        """Return the collection ID for the currently selected collection,
        or None if no collection is selected.
        """
        cursor = self._treeview.get_cursor()
        if cursor is None:
            return
        return self._get_collection_at_path(cursor[0])

    def display_collections(self):
        """Display the library collections by redrawing them from the
        backend data. Should be called on startup or when the collections
        hierarchy has been changed (e.g. after moving, adding, renaming).
        Any row that was expanded before the call will have it's
        corresponding new row also expanded after the call.
        """
        
        def _recursive_add(parent_iter, supercoll):
            for coll in self._library.backend.get_collections_in_collection(
              supercoll):
                name = self._library.backend.get_collection_name(coll)
                child_iter = self._treestore.append(parent_iter,
                    [xmlescape(name), coll])
                _recursive_add(child_iter, coll)

        def _expand_and_select(treestore, path, iterator):
            collection = treestore.get_value(iterator, 1)
            if collection == prefs['last library collection']:
                # Reset to trigger update of book area.
                prefs['last library collection'] = None 
                self._treeview.expand_to_path(path)
                self._treeview.set_cursor(path)
            elif collection in expanded_collections:
                self._treeview.expand_to_path(path) 

        def _expanded_rows_accumulator(treeview, path):
            collection = self._get_collection_at_path(path)
            expanded_collections.append(collection)
        
        expanded_collections = []
        self._treeview.map_expanded_rows(_expanded_rows_accumulator)
        self._treestore.clear()
        self._treestore.append(None, ['<b>%s</b>' % xmlescape(_('All books')),
            _COLLECTION_ALL])
        _recursive_add(None, None)
        self._treestore.foreach(_expand_and_select)

    def _get_collection_at_path(self, path):
        """Return the collection ID of the collection at the (TreeView)
        <path>.
        """
        iterator = self._treestore.get_iter(path)
        return self._treestore.get_value(iterator, 1)

    def _collection_selected(self, treeview):
        """Change the viewed collection (in the _BookArea) to the
        currently selected one in the sidebar, if it has been changed.
        """
        collection = self.get_current_collection()
        if (collection is None or
          collection == prefs['last library collection']):
            return
        prefs['last library collection'] = collection
        gobject.idle_add(self._library.book_area.display_covers, collection)

    def _remove_collection(self, action=None):
        """Remove the currently selected collection from the library, if the
        user answers 'Yes' in a dialog.
        """
        choice_dialog = gtk.MessageDialog(self._library, 0,
            gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
            _('Remove collection from the library?'))
        choice_dialog.format_secondary_text(
            _('The selected collection will be removed from the library (but the books and subcollections in it will remain). Are you sure that you want to continue?'))
        response = choice_dialog.run()
        choice_dialog.destroy()
        if response == gtk.RESPONSE_YES:
            collection = self.get_current_collection()
            self._library.backend.remove_collection(collection)
            prefs['last library collection'] = _COLLECTION_ALL
            self.display_collections()

    def _rename_collection(self, action):
        """Rename the currently selected collection, using a dialog."""
        collection = self.get_current_collection()
        try:
            old_name = self._library.backend.get_collection_name(collection)
        except Exception:
            return
        rename_dialog = gtk.MessageDialog(self._library, 0,
            gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,
            _('Rename collection?'))
        rename_dialog.format_secondary_text(
            _('Please enter a new name for the selected collection.'))
        rename_dialog.set_default_response(gtk.RESPONSE_OK)
        
        box = gtk.HBox() # To get nice line-ups with the padding.
        rename_dialog.vbox.pack_start(box)
        entry = gtk.Entry()
        entry.set_text(old_name)
        entry.set_activates_default(True)
        box.pack_start(entry, True, True, 6)
        box.show_all()
        
        response = rename_dialog.run()
        new_name = entry.get_text()
        rename_dialog.destroy()
        if response == gtk.RESPONSE_OK and new_name:
            if self._library.backend.rename_collection(collection, new_name):
                self.display_collections()
            else:
                message = _("Could not change the name to '%s'.") % new_name
                if (self._library.backend.get_collection_by_name(new_name)
                  is not None):
                    message = '%s %s' % (message,
                        _('A collection by that name already exists.'))
                self._library.set_status_message(message)
    
    def _duplicate_collection(self, action):
        """Duplicate the currently selected collection."""
        collection = self.get_current_collection()
        if self._library.backend.duplicate_collection(collection):
            self.display_collections()
        else:
            self._library.set_status_message(
                _('Could not duplicate collection.'))

    def _button_press(self, treeview, event):
        """Handle mouse button presses on the _CollectionArea."""
        row = treeview.get_path_at_pos(int(event.x), int(event.y))
        if row is None:
            return
        path = row[0]
        if event.button == 3:
            if self._get_collection_at_path(path) == _COLLECTION_ALL:
                sens = False
            else:
                sens = True
            self._ui_manager.get_action('/Popup/rename').set_sensitive(sens)
            self._ui_manager.get_action('/Popup/duplicate').set_sensitive(sens)
            self._ui_manager.get_action('/Popup/remove').set_sensitive(sens)
            self._ui_manager.get_widget('/Popup').popup(None, None, None,
                event.button, event.time)

    def _key_press(self, treeview, event):
        """Handle key presses on the _CollectionArea."""
        if event.keyval == gtk.keysyms.Delete:
            self._remove_collection()

    def _expand_or_collapse_row(self, treeview, path, column):
        """Expand or collapse the activated row."""
        if treeview.row_expanded(path):
            treeview.collapse_row(path)
        else:
            treeview.expand_to_path(path)

    def _drag_data_received(self, treeview, context, x, y, selection, drag_id,
      eventtime):
        """Move books dragged from the _BookArea to the target collection,
        or move some collection into another collection.
        """
        self._library.set_status_message('')
        drop_row = treeview.get_dest_row_at_pos(x, y)
        if drop_row is None: # Drop "after" the last row. 
            dest_path, pos = ((len(self._treestore) - 1,),
                gtk.TREE_VIEW_DROP_AFTER)
        else:
            dest_path, pos = drop_row
        src_collection = self.get_current_collection()
        dest_collection = self._get_collection_at_path(dest_path)
        if drag_id == _DRAG_COLLECTION_ID:
            if pos in (gtk.TREE_VIEW_DROP_BEFORE, gtk.TREE_VIEW_DROP_AFTER):
                dest_collection = self._library.backend.get_supercollection(
                    dest_collection)
            self._library.backend.add_collection_to_collection(
                src_collection, dest_collection)
            self.display_collections()
        elif drag_id == _DRAG_BOOK_ID:
            for path_str in selection.get_text().split(','): # IconView path
                book = self._library.book_area.get_book_at_path(int(path_str))
                self._library.backend.add_book_to_collection(book,
                    dest_collection)
                if src_collection != _COLLECTION_ALL:
                    self._library.backend.remove_book_from_collection(book,
                        src_collection)
                    self._library.book_area.remove_book_at_path(int(path_str))
                
    def _drag_motion(self, treeview, context, x, y, *args):
        """Set the library statusbar text when hovering a drag-n-drop over
        a collection (either books or from the collection area itself).
        Also set the TreeView to accept drops only when we are hovering over
        a valid drop position for the current drop type.

        This isn't pretty, but the details of treeviews and drag-n-drops
        are not pretty to begin with.
        """
        drop_row = treeview.get_dest_row_at_pos(x, y)
        src_collection = self.get_current_collection()
        # Why isn't the drag ID passed along with drag-motion events?
        if context.get_source_widget() is self._treeview: # Moving collection.
            model, src_iter = treeview.get_selection().get_selected()
            if drop_row is None: # Drop "after" the last row.
                dest_path, pos = (len(model) - 1,), gtk.TREE_VIEW_DROP_AFTER
            else:
                dest_path, pos = drop_row
            dest_iter = model.get_iter(dest_path)
            if model.is_ancestor(src_iter, dest_iter): # No cycles!
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            dest_collection = self._get_collection_at_path(dest_path)
            if pos in (gtk.TREE_VIEW_DROP_BEFORE, gtk.TREE_VIEW_DROP_AFTER):
                dest_collection = self._library.backend.get_supercollection(
                    dest_collection)
            if (_COLLECTION_ALL in (src_collection, dest_collection) or
              src_collection == dest_collection):
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            src_name = self._library.backend.get_collection_name(
                src_collection)
            if dest_collection is None:
                dest_name = _('Root')
            else:
                dest_name = self._library.backend.get_collection_name(
                    dest_collection)
            message = (_("Put the collection '%(subcollection)s' in the collection '%(supercollection)s'.") %
                {'subcollection': src_name, 'supercollection': dest_name})
        else: # Moving book(s).
            if drop_row is None:
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            dest_path, pos = drop_row
            if pos in (gtk.TREE_VIEW_DROP_BEFORE, gtk.TREE_VIEW_DROP_AFTER):
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            dest_collection = self._get_collection_at_path(dest_path)
            if (src_collection == dest_collection or
              dest_collection == _COLLECTION_ALL):
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            dest_name = self._library.backend.get_collection_name(
                dest_collection)
            if src_collection == _COLLECTION_ALL:
                message = _("Add books to '%s'.") % dest_name
            else:
                src_name = self._library.backend.get_collection_name(
                    src_collection)
                message = (_("Move books from '%(source collection)s' to '%(destination collection)s'.") % 
                    {'source collection': src_name,
                    'destination collection': dest_name})
        self._set_acceptable_drop(True)
        self._library.set_status_message(message)

    def _set_acceptable_drop(self, acceptable):
        """Set the TreeView to accept drops if <acceptable> is True."""
        if acceptable:
            self._treeview.enable_model_drag_dest(
                [('book', gtk.TARGET_SAME_APP, _DRAG_BOOK_ID),
                ('collection', gtk.TARGET_SAME_WIDGET, _DRAG_COLLECTION_ID)],
                gtk.gdk.ACTION_MOVE)
        else:
            self._treeview.enable_model_drag_dest([], gtk.gdk.ACTION_MOVE)

    def _drag_begin(self, treeview, context):
        """Create a cursor image for drag-n-drop of collections. We use the
        default one (i.e. the row with text), but put the hotspot in the
        top left corner so that one can actually see where one is dropping,
        which unfortunately isn't the default case.
        """
        path = treeview.get_cursor()[0]
        pixmap = treeview.create_row_drag_icon(path)
        # context.set_icon_pixmap() seems to cause crashes, so we do a
        # quick and dirty conversion to pixbuf.
        pointer = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
            *pixmap.get_size())
        pointer = pointer.get_from_drawable(pixmap, treeview.get_colormap(),
            0, 0, 0, 0, *pixmap.get_size())
        context.set_icon_pixbuf(pointer, -5, -5)


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
            [('book', gtk.TARGET_SAME_APP, _DRAG_BOOK_ID)],
            gtk.gdk.ACTION_MOVE)
        self._iconview.drag_dest_set(gtk.DEST_DEFAULT_ALL,
            [('text/uri-list', 0, _DRAG_EXTERNAL_ID)],
            gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_MOVE)
        self._iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.add(self._iconview)

        self._ui_manager = gtk.UIManager()
        ui_description = """
        <ui>
            <popup name="Popup">
                <menuitem action="open" />
                <separator />
                <menuitem action="remove from collection" />
                <menuitem action="remove from library" />
            </popup>
        </ui>
        """
        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = gtk.ActionGroup('comix-library-book-area')
        actiongroup.add_actions([
            ('open', gtk.STOCK_OPEN, _('Open'), None, None,
                self.open_selected_book),
            ('remove from collection', gtk.STOCK_REMOVE,
                _('Remove from this collection'), None, None,
                self._remove_books_from_collection),
            ('remove from library', gtk.STOCK_DELETE,
                _('Remove from the library...'), None, None,
                self._remove_books_from_library)])
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
            if i % 15 == 0: # Don't update GUI for every cover for efficiency.
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

    def open_selected_book(self, *args):
        """Open the currently selected book."""
        selected = self._iconview.get_selected_items()
        if not selected:
            return
        path = selected[0]
        self._book_activated(self._iconview, path)

    def _add_book(self, book):
        """Add the <book> to the ListStore (and thus to the _BookArea)."""
        pixbuf = self._library.backend.get_book_cover(book)
        if pixbuf is None:
            pixbuf = self._library.render_icon(gtk.STOCK_MISSING_IMAGE,
                gtk.ICON_SIZE_DIALOG)
        # The ratio (0.67) is just above the normal aspect ratio for books.
        pixbuf = image.fit_in_rectangle(pixbuf,
            int(0.67 * prefs['library cover size']),
            prefs['library cover size'])
        pixbuf = image.add_border(pixbuf, 1, 0xFFFFFFFF)
        self._liststore.append([pixbuf, book])

    def _book_activated(self, iconview, path):
        """Open the book at the (liststore) <path>."""
        book = self.get_book_at_path(path)
        self._library.open_book(book)

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

    def _remove_books_from_library(self, *args):
        """Remove the currently selected book(s) from the library, and thus
        also from the _BookArea, if the user clicks 'Yes' in a dialog.
        """
        choice_dialog = gtk.MessageDialog(self._library, 0,
            gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
            _('Remove books from the library?'))
        choice_dialog.format_secondary_text(
            _('The selected books will be removed from the library (but the original files will be untouched). Are you sure that you want to continue?'))
        response = choice_dialog.run()
        choice_dialog.destroy()
        if response == gtk.RESPONSE_YES:
            selected = self._iconview.get_selected_items()
            for path in selected:
                book = self.get_book_at_path(path)
                self._library.backend.remove_book(book)
                self.remove_book_at_path(path)
            self._library.set_status_message(
                _('Removed %d book(s) from the library.') % len(selected))

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
            cover = self._library.render_icon(gtk.STOCK_MISSING_IMAGE,
                gtk.ICON_SIZE_DIALOG)
        cover = cover.scale_simple(max(0, cover.get_width() // 2),
            max(0, cover.get_height() // 2), gtk.gdk.INTERP_TILES)
        cover = image.add_border(cover, 1, 0xFFFFFFFF)
        cover = image.add_border(cover, 1)
        
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
            circle = image.pil_to_pixbuf(im)
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


class _ControlArea(gtk.HBox):
    
    """The _ControlArea is the bottom area of the library window where
    information is displayed and controls such as buttons resides.
    """
    
    def __init__(self, library):
        self._library = library
        gtk.HBox.__init__(self, False, 12)

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
        adjustment = gtk.Adjustment(prefs['library cover size'], 50, 128, 1,
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
        add_collection_button = gtk.Button(_('Add collection'))
        add_collection_button.connect('clicked', self._add_collection)
        add_collection_button.set_image(gtk.image_new_from_stock(
            gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON))
        add_collection_button.set_tooltip_text(
            _('Add a new empty collection.'))
        hbox.pack_start(add_collection_button, False, False)
        hbox.pack_start(gtk.HBox(), True, True)
        self._open_button = gtk.Button(None, gtk.STOCK_OPEN)
        self._open_button.connect('clicked',
            self._library.book_area.open_selected_book)
        self._open_button.set_tooltip_text(_('Open the selected book.'))
        self._open_button.set_sensitive(False)
        hbox.pack_start(self._open_button, False, False)

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
        else:
            self._namelabel.set_text('')
        if pages is not None:
            self._pageslabel.set_text(_('%d pages') % pages)
        else:
            self._pageslabel.set_text('')
        if format is not None and size is not None:
            self._filelabel.set_text('%s, %s' % (archive.get_name(format),
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
        filechooser.open_library_filechooser_dialog(self._library)

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


class _AddBooksProgressDialog(gtk.Dialog):
    
    """Dialog with a ProgressBar that adds books to the library."""
    
    def __init__(self, library, paths, collection):
        """Adds the books at <paths> to the library, and also to the
        <collection>, unless it is None.
        """
        gtk.Dialog.__init__(self, _('Adding books'), library,
            gtk.DIALOG_MODAL, (gtk.STOCK_STOP, gtk.RESPONSE_CLOSE))
        self._destroy = False
        self.set_size_request(400, -1)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.set_border_width(4)
        self.connect('response', self._response)
        self.set_default_response(gtk.RESPONSE_CLOSE)

        main_box = gtk.VBox(False, 5)
        main_box.set_border_width(6)
        self.vbox.pack_start(main_box, False, False)
        hbox = gtk.HBox(False, 10)
        main_box.pack_start(hbox, False, False, 5)
        left_box = gtk.VBox(True, 5)
        right_box = gtk.VBox(True, 5)
        hbox.pack_start(left_box, False, False)
        hbox.pack_start(right_box, False, False)

        label = labels.BoldLabel('%s:' % _('Added books'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        number_label = gtk.Label('0')
        number_label.set_alignment(0, 1.0)
        right_box.pack_start(number_label, True, True)

        bar = gtk.ProgressBar()
        main_box.pack_start(bar, False, False)

        added_label = labels.ItalicLabel()
        added_label.set_alignment(0, 0.5)
        added_label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        main_box.pack_start(added_label, False, False)
        self.show_all()

        total_paths = float(len(paths))
        total_added = 0
        for i, path in enumerate(paths):
            if library.backend.add_book(path, collection):
                total_added += 1
                number_label.set_text('%d' % total_added)
            added_label.set_text(_("Adding '%s'...") %
                encoding.to_unicode(path))
            bar.set_fraction((i + 1) / total_paths)
            while gtk.events_pending():
                gtk.main_iteration(False)
            if self._destroy:
                return
        self._response()

    def _response(self, *args):
        self._destroy = True
        self.destroy()
        

def open_dialog(action, window):
    global _dialog
    if _dialog is None:
        if librarybackend.dbapi2 is None:
            print '! You need an sqlite wrapper to use the library.'
        else:
            _dialog = _LibraryDialog(window)
    else:
        _dialog.present()


def _close_dialog(*args):
    global _dialog
    if _dialog is not None:
        _dialog.destroy()
        _dialog = None
        gc.collect()

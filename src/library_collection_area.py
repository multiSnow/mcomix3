"""library_collection_area.py - Comic book library window that displays the collections."""

from xml.sax.saxutils import escape as xmlescape
import gtk
import gobject
import constants
from preferences import prefs

_dialog = None
# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1

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
            [('collection', gtk.TARGET_SAME_WIDGET, constants.LIBRARY_DRAG_COLLECTION_ID)],
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
        actiongroup = gtk.ActionGroup('mcomix-library-collection-area')
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
        if drag_id == constants.LIBRARY_DRAG_COLLECTION_ID:
            if pos in (gtk.TREE_VIEW_DROP_BEFORE, gtk.TREE_VIEW_DROP_AFTER):
                dest_collection = self._library.backend.get_supercollection(
                    dest_collection)
            self._library.backend.add_collection_to_collection(
                src_collection, dest_collection)
            self.display_collections()
        elif drag_id == constants.LIBRARY_DRAG_BOOK_ID:
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
                [('book', gtk.TARGET_SAME_APP, constants.LIBRARY_DRAG_BOOK_ID),
                ('collection', gtk.TARGET_SAME_WIDGET, constants.LIBRARY_DRAG_COLLECTION_ID)],
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

# vim: expandtab:sw=4:ts=4

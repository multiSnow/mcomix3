'''library_collection_area.py - Comic book library window that displays the collections.'''

from xml.sax.saxutils import escape as xmlescape
from gi.repository import Gdk, GdkPixbuf, Gtk, GLib

from mcomix.preferences import prefs
from mcomix import constants
from mcomix import i18n
from mcomix import status
from mcomix import file_chooser_library_dialog
from mcomix import message_dialog

_dialog = None
# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1
_COLLECTION_RECENT = -2

class _CollectionArea(Gtk.ScrolledWindow):

    '''The _CollectionArea is the sidebar area in the library where
    different collections are displayed in a tree.
    '''

    def __init__(self, library):
        super(_CollectionArea, self).__init__()
        self._library = library
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._treestore = Gtk.TreeStore(str, int) # (Name, ID) of collections.
        self._treeview = Gtk.TreeView(model=self._treestore)
        self._treeview.connect('cursor_changed', self._collection_selected)
        self._treeview.connect('drag_data_received', self._drag_data_received)
        self._treeview.connect('drag_motion', self._drag_motion)
        self._treeview.connect_after('drag_begin', self._drag_begin)
        self._treeview.connect('button_press_event', self._button_press)
        self._treeview.connect('key_press_event', self._key_press)
        self._treeview.connect('popup_menu', self._popup_menu)
        self._treeview.connect('row_activated', self._expand_or_collapse_row)
        self._treeview.set_headers_visible(False)
        self._set_acceptable_drop(True)
        self._treeview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                                [('collection', Gtk.TargetFlags.SAME_WIDGET,
                                                  constants.LIBRARY_DRAG_COLLECTION_ID)],
                                                Gdk.DragAction.MOVE)

        cellrenderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, cellrenderer, markup=0)
        self._treeview.append_column(column)
        self.add(self._treeview)

        self._ui_manager = Gtk.UIManager()
        self._tooltipstatus = status.TooltipStatusHelper(self._ui_manager,
            self._library.get_status_bar())
        ui_description = '''
        <ui>
            <popup name="library collections">
                <menuitem action="_title" />
                <separator />
                <menuitem action="add" />
                <separator />
                <menuitem action="new" />
                <menuitem action="rename" />
                <menuitem action="duplicate" />
                <separator />
                <menuitem action="cleanup" />
                <menuitem action="remove" />
            </popup>
        </ui>
        '''
        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = Gtk.ActionGroup(name='mcomix-library-collection-area')
        actiongroup.add_actions([
            ('_title', None, _('Library collections'), None, None,
             lambda *args: False),
            ('add', Gtk.STOCK_ADD, _('_Add...'), None,
             _('Add more books to the library.'),
             lambda *args: file_chooser_library_dialog.open_library_filechooser_dialog(self._library)),
            ('new', Gtk.STOCK_NEW, _('New'), None,
             _('Add a new empty collection.'),
             self.add_collection),
            ('rename', Gtk.STOCK_EDIT, _('Re_name'), None,
             _('Renames the selected collection.'),
             self._rename_collection),
            ('duplicate', Gtk.STOCK_COPY, _('_Duplicate'), None,
             _('Creates a duplicate of the selected collection.'),
             self._duplicate_collection),
            ('cleanup', Gtk.STOCK_CLEAR, _('_Clean up'), None,
             _('Removes no longer existant books from the collection.'),
             self._clean_collection),
            ('remove', Gtk.STOCK_REMOVE, _('_Remove'), None,
             _('Deletes the selected collection.'),
             self._remove_collection)])
        self._ui_manager.insert_action_group(actiongroup, 0)

        self.display_collections()

    def get_current_collection(self):
        '''Return the collection ID for the currently selected collection,
        or None if no collection is selected.
        '''
        treepath, focuspath = self._treeview.get_cursor()
        if treepath is not None:
            return self._get_collection_at_path(treepath)
        else:
            return None

    def display_collections(self):
        '''Display the library collections by redrawing them from the
        backend data. Should be called on startup or when the collections
        hierarchy has been changed (e.g. after moving, adding, renaming).
        Any row that was expanded before the call will have it's
        corresponding new row also expanded after the call.
        '''

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

    def add_collection(self, *args):
        '''Add a new collection to the library, through a dialog.'''
        add_dialog = message_dialog.MessageDialog(self._library, 0, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK_CANCEL)
        add_dialog.set_auto_destroy(False)
        add_dialog.set_default_response(Gtk.ResponseType.OK)
        add_dialog.set_text(
            _('Add new collection?'),
            _('Please enter a name for the new collection.')
        )

        box = Gtk.HBox() # To get nice line-ups with the padding.
        add_dialog.vbox.pack_start(box, True, True, 0)
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.pack_start(entry, True, True, 6)
        box.show_all()

        response = add_dialog.run()
        name = entry.get_text()
        add_dialog.destroy()
        if response == Gtk.ResponseType.OK and name:
            if self._library.backend.add_collection(name):
                collection = self._library.backend.get_collection_by_name(name)
                prefs['last library collection'] = collection.id
                self._library.collection_area.display_collections()
            else:
                message = _('Could not add a new collection called "%s".') % (name)
                if (self._library.backend.get_collection_by_name(name)
                  is not None):
                    message = '%s %s' % (message,
                                         _('A collection by that name already exists.'))
                self._library.set_status_message(message)

    def clean_collection(self, collection):
        ''' Check all books in the collection, removing those that
        no longer exist. If C{collection} is None, the whole library
        will be cleaned. '''

        removed = self._library.backend.clean_collection(collection)

        msg = i18n.get_translation().ngettext(
            'Removed %d book from the library.',
            'Removed %d books from the library.',
            removed)
        self._library.set_status_message(msg % removed)

        if removed > 0:
            collection = self._library.collection_area.get_current_collection()
            GLib.idle_add(self._library.book_area.display_covers, collection)

    def _get_collection_at_path(self, path):
        '''Return the collection ID of the collection at the (TreeView)
        <path>.
        '''
        iterator = self._treestore.get_iter(path)
        return self._treestore.get_value(iterator, 1)

    def _collection_selected(self, treeview):
        '''Change the viewed collection (in the _BookArea) to the
        currently selected one in the sidebar, if it has been changed.
        '''
        collection = self.get_current_collection()
        if (collection is None or
          collection == prefs['last library collection']):
            return
        prefs['last library collection'] = collection
        GLib.idle_add(self._library.book_area.display_covers, collection)

    def _clean_collection(self, *args):
        ''' Menu item hook to clean a collection. '''

        collection = self.get_current_collection()

        # The backend expects _COLLECTION_ALL to be passed as None
        if collection == _COLLECTION_ALL:
            collection = None

        self.clean_collection(collection)

    def _remove_collection(self, action=None):
        '''Remove the currently selected collection from the library.'''
        collection = self.get_current_collection()

        if collection not in (_COLLECTION_ALL, _COLLECTION_RECENT):
            self._library.backend.remove_collection(collection)
            prefs['last library collection'] = _COLLECTION_ALL
            self.display_collections()

    def _rename_collection(self, action):
        '''Rename the currently selected collection, using a dialog.'''
        collection = self.get_current_collection()
        try:
            old_name = self._library.backend.get_collection_name(collection)
        except Exception:
            return
        rename_dialog = message_dialog.MessageDialog(self._library, 0,
            Gtk.MessageType.INFO, Gtk.ButtonsType.OK_CANCEL)
        rename_dialog.set_auto_destroy(False)
        rename_dialog.set_text(
            _('Rename collection?'),
            _('Please enter a new name for the selected collection.')
        )
        rename_dialog.set_default_response(Gtk.ResponseType.OK)

        box = Gtk.HBox() # To get nice line-ups with the padding.
        rename_dialog.vbox.pack_start(box, True, True, 0)
        entry = Gtk.Entry()
        entry.set_text(old_name)
        entry.set_activates_default(True)
        box.pack_start(entry, True, True, 6)
        box.show_all()

        response = rename_dialog.run()
        new_name = entry.get_text()
        rename_dialog.destroy()
        if response == Gtk.ResponseType.OK and new_name:
            if self._library.backend.rename_collection(collection, new_name):
                self.display_collections()
            else:
                message = _('Could not change the name to "%s".') % new_name
                if (self._library.backend.get_collection_by_name(new_name)
                  is not None):
                    message = '%s %s' % (message,
                                         _('A collection by that name already exists.'))
                self._library.set_status_message(message)

    def _duplicate_collection(self, action):
        '''Duplicate the currently selected collection.'''
        collection = self.get_current_collection()
        if self._library.backend.duplicate_collection(collection):
            self.display_collections()
        else:
            self._library.set_status_message(
                _('Could not duplicate collection.'))

    def _button_press(self, treeview, event):
        '''Handle mouse button presses on the _CollectionArea.'''

        if event.button == 3:
            row = treeview.get_path_at_pos(int(event.x), int(event.y))
            if row:
                path, column, x, y = row
                collection = self._get_collection_at_path(path)
            else:
                collection = None

            self._popup_collection_menu(collection)

    def _popup_menu(self, treeview):
        ''' Called to open the control's popup menu via
        keyboard controls. '''

        model, iter = treeview.get_selection().get_selected()
        if iter is not None:
            book_path = model.get_path(iter)[0]
            collection = self._get_collection_at_path(book_path)
        else:
            collection = None

        self._popup_collection_menu(collection)
        return True

    def _popup_collection_menu(self, collection):
        ''' Show the library collection popup. Depending on the
        value of C{collection}, menu items will be disabled or enabled. '''

        is_collection_all = collection in (_COLLECTION_ALL, _COLLECTION_RECENT)

        for path in ('rename', 'duplicate', 'remove'):
            control = self._ui_manager.get_action(
                    '/library collections/' + path)
            control.set_sensitive(collection is not None and
                    not is_collection_all)

        self._ui_manager.get_action('/library collections/add').set_sensitive(collection is not None)
        self._ui_manager.get_action('/library collections/cleanup').set_sensitive(collection is not None)
        self._ui_manager.get_action('/library collections/_title').set_sensitive(False)

        menu = self._ui_manager.get_widget('/library collections')
        menu.popup(None, None, None, None, 3, Gtk.get_current_event_time())

    def _key_press(self, treeview, event):
        '''Handle key presses on the _CollectionArea.'''
        if event.keyval == Gdk.KEY_Delete:
            self._remove_collection()

    def _expand_or_collapse_row(self, treeview, path, column):
        '''Expand or collapse the activated row.'''
        if treeview.row_expanded(path):
            treeview.collapse_row(path)
        else:
            treeview.expand_to_path(path)

    def _drag_data_received(self, treeview, context, x, y, selection, drag_id,
      eventtime):
        '''Move books dragged from the _BookArea to the target collection,
        or move some collection into another collection.
        '''
        self._library.set_status_message('')
        drop_row = treeview.get_dest_row_at_pos(x, y)
        if drop_row is None: # Drop "after" the last row.
            dest_path, pos = ((len(self._treestore) - 1,),
                Gtk.TreeViewDropPosition.AFTER)
        else:
            dest_path, pos = drop_row
        src_collection = self.get_current_collection()
        dest_collection = self._get_collection_at_path(dest_path)
        if drag_id == constants.LIBRARY_DRAG_COLLECTION_ID:
            if pos in (Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.AFTER):
                dest_collection = self._library.backend.get_supercollection(
                    dest_collection)
            self._library.backend.add_collection_to_collection(
                src_collection, dest_collection)
            self.display_collections()
        elif drag_id == constants.LIBRARY_DRAG_BOOK_ID:

            #FIXME
            #tmp workaround for GTK bug, 2018
            #see also _drag_data_get in book_area
            #receaving as bytearray instead of text
            for path_str in selection.get_data().decode().split(','): # IconView path
            #for path_str in selection.get_text().split(','): # IconView path
                book = self._library.book_area.get_book_at_path(int(path_str))
                self._library.backend.add_book_to_collection(book,
                    dest_collection)
                if src_collection != _COLLECTION_ALL:
                    self._library.backend.remove_book_from_collection(book,
                        src_collection)
                    self._library.book_area.remove_book_at_path(int(path_str))

    def _drag_motion(self, treeview, context, x, y, *args):
        '''Set the library statusbar text when hovering a drag-n-drop over
        a collection (either books or from the collection area itself).
        Also set the TreeView to accept drops only when we are hovering over
        a valid drop position for the current drop type.

        This isn't pretty, but the details of treeviews and drag-n-drops
        are not pretty to begin with.
        '''
        drop_row = treeview.get_dest_row_at_pos(x, y)
        src_collection = self.get_current_collection()
        # Why isn't the drag ID passed along with drag-motion events?
        if Gtk.drag_get_source_widget(context) is self._treeview: # Moving collection.
            model, src_iter = treeview.get_selection().get_selected()
            if drop_row is None: # Drop "after" the last row.
                dest_path, pos = (len(model) - 1,), Gtk.TreeViewDropPosition.AFTER
            else:
                dest_path, pos = drop_row
            dest_iter = model.get_iter(dest_path)
            if model.is_ancestor(src_iter, dest_iter): # No cycles!
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            dest_collection = self._get_collection_at_path(dest_path)
            if pos in (Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.AFTER):
                dest_collection = self._library.backend.get_supercollection(
                    dest_collection)
            if (_COLLECTION_ALL in (src_collection, dest_collection) or
                _COLLECTION_RECENT in (src_collection, dest_collection) or
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
            message = (_('Put the collection "%(subcollection)s" in the collection "%(supercollection)s".') %
                       {'subcollection': src_name, 'supercollection': dest_name})
        else: # Moving book(s).
            if drop_row is None:
                self._set_acceptable_drop(False)
                self._library.set_status_message('')
                return
            dest_path, pos = drop_row
            if pos in (Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.AFTER):
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
                message = _('Add books to "%s".') % dest_name
            else:
                src_name = self._library.backend.get_collection_name(
                    src_collection)
                message = (_('Move books from "%(source collection)s" to "%(destination collection)s".') %
                           {'source collection': src_name,
                            'destination collection': dest_name})
        self._set_acceptable_drop(True)
        self._library.set_status_message(message)

    def _set_acceptable_drop(self, acceptable):
        '''Set the TreeView to accept drops if <acceptable> is True.'''
        if acceptable:
            self._treeview.enable_model_drag_dest(
                [('book', Gtk.TargetFlags.SAME_APP, constants.LIBRARY_DRAG_BOOK_ID),
                 ('collection', Gtk.TargetFlags.SAME_WIDGET, constants.LIBRARY_DRAG_COLLECTION_ID)],
                Gdk.DragAction.MOVE)
        else:
            self._treeview.enable_model_drag_dest([], Gdk.DragAction.MOVE)

    def _drag_begin(self, treeview, context):
        '''Create a cursor image for drag-n-drop of collections. We use the
        default one (i.e. the row with text), but put the hotspot in the
        top left corner so that one can actually see where one is dropping,
        which unfortunately isn't the default case.
        '''
        path = treeview.get_cursor()[0]
        surface = treeview.create_row_drag_icon(path)
        width, height = surface.get_width(), surface.get_height()
        pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)
        Gtk.drag_set_icon_pixbuf(context, pixbuf, -5, -5)

# vim: expandtab:sw=4:ts=4

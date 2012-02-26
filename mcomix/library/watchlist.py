""" Library watch list dialog and backend classes. """

import gtk
import gobject

from mcomix.library import backend_types


COL_DIRECTORY = 0
COL_COLLECTION = 0
COL_COLLECTION_ID = 1


class WatchListDialog(gtk.Dialog):
    """ Dialog for managing watched directories. """

    def __init__(self, library):
        """ Dialog constructor.
        @param library: Dialog parent window, should be library window.
        """
        super(WatchListDialog, self).__init__(_("Library watch list"),
            library, gtk.DIALOG_DESTROY_WITH_PARENT,
            (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.library = library

        self.set_default_response(gtk.RESPONSE_CLOSE)

        # Initialize treeview control showing existing watch directories
        self._treeview = gtk.TreeView(self._create_model())
        self._treeview.set_headers_visible(True)
        dir_renderer = gtk.CellRendererText()
        dir_column = gtk.TreeViewColumn(_("Directory"), dir_renderer)
        dir_column.set_attributes(dir_renderer, text=COL_DIRECTORY, editable=True)
        self._treeview.append_column(dir_column)

        collection_model = self._create_collection_model()
        collection_renderer = gtk.CellRendererCombo()
        collection_renderer.set_property('model', collection_model)
        collection_renderer.set_property('text-column', COL_COLLECTION)
        collection_renderer.set_property('editable', gtk.TRUE)
        collection_renderer.set_property('has-entry', gtk.FALSE)
        collection_renderer.connect('changed', self._collection_changed_cb, collection_model)
        collection_column = gtk.TreeViewColumn(_("Collection"), collection_renderer)
        collection_column.set_cell_data_func(collection_renderer,
                self._treeview_collection_id_to_name)
        self._treeview.append_column(collection_column)

        add_button = gtk.Button(_("_Add"), gtk.STOCK_ADD)
        add_button.connect('clicked', self._add_cb)
        remove_button = gtk.Button(_("_Remove"), gtk.STOCK_REMOVE)
        remove_button.connect('clicked', self._remove_cb)

        button_box = gtk.VBox()
        button_box.pack_start(add_button, expand=False)
        button_box.pack_start(remove_button, expand=False, padding=2)

        main_box = gtk.HBox()
        main_box.pack_start(self._treeview, padding=2)
        main_box.pack_end(button_box, expand=False)
        self.vbox.pack_start(main_box)

        self.resize(400, 350)
        self.connect('response', lambda *args: self.destroy())
        self.show_all()

    def _create_model(self):
        """ Creates a model containing all watched directories. """
        # Watched directory, associated library collection ID
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)

        for entry in  self.library.backend.watchlist.get_watchlist():
            if entry.collection.id is None:
                id = -1
            else:
                id = entry.collection.id

            model.append((entry.directory, id))

        return model

    def _create_collection_model(self):
        """ Creates a model containing all available collections. """
        # Collection ID, collection name
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)

        ids = self.library.backend.get_all_collections()
        model.append((backend_types.DefaultCollection.name, -1))
        for id in ids:
            model.append((self.library.backend.get_collection_name(id), id))

        return model

    def _collection_changed_cb(self, column, path,
                               collection_iter, collection_model, *args):
        """ A new collection was set for a watched directory. """
        # Get new collection ID from collection model
        new_id = collection_model.get_value(collection_iter, COL_COLLECTION_ID)

        # Update collection ID in watchlist model
        model = self._treeview.get_model()
        iter = model.get_iter(path)
        model.set_value(iter, COL_COLLECTION_ID, new_id)

        # TODO: Update database with new collection id

    def _add_cb(self, button, *args):
        """ Called when a new watch list entry should be added. """
        pass

    def _remove_cb(self, button, *args):
        """ Called when a watch list entry should be removed. """
        pass

    def _treeview_collection_id_to_name(self, column, cell, model, iter, *args):
        """ Maps a collection ID to the corresponding collection name. """
        id = model.get_value(iter, COL_COLLECTION_ID)
        if id != -1:
            text = self.library.backend.get_collection_name(id)
        else:
            text = backend_types.DefaultCollection.name

        cell.set_property("text", text)


# vim: expandtab:sw=4:ts=4

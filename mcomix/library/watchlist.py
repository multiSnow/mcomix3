""" Library watch list dialog and backend classes. """

import gtk
import gobject

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

        self.vbox.pack_start(self._treeview)

        self.resize(400, 350)
        self.connect('response', lambda *args: self.destroy())
        self.show_all()

    def _create_model(self):
        """ Creates a model containing all watched directories. """
        # Watched directory, associated library collection ID
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)
        collection_model = self._create_collection_model()

        # FIXME: Add real data from database
        model.append(("/home/user/data/", 1))
        model.append(("/var/tmp", 1))

        return model

    def _create_collection_model(self):
        """ Creates a model containing all available collections. """
        # Collection ID, collection name
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_INT)

        ids = self.library.backend.get_all_collections()
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

    def _treeview_collection_id_to_name(self, column, cell, model, iter, *args):
        """ Maps a collection ID to the corresponding collection name. """
        id = model.get_value(iter, COL_COLLECTION_ID)
        cell.set_property("text", self.library.backend.get_collection_name(id))

class WatchList(object):
    """ Scans watched directories and updates the database when new books have
    been added. """
    pass

# vim: expandtab:sw=4:ts=4

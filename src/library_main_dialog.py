"""library_main_dialog.py - The library dialog window."""

import gtk
import encoding
import constants
import file_chooser_library_dialog
import library_backend
import library_book_area
import library_collection_area
import library_control_area
import library_add_progress_dialog
from preferences import prefs

_dialog = None
# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1

class _LibraryDialog(gtk.Window):
    
    """The library window. Automatically creates and uses a new
    library_backend.LibraryBackend when opened.
    """

    def __init__(self, window, file_handler):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        self._window = window
        
        self.resize(prefs['lib window width'], prefs['lib window height'])
        self.set_title(_('Library'))
        self.connect('delete_event', self.close)
        
        self.filter_string = None
        self._file_handler = file_handler
        self._statusbar = gtk.Statusbar()
        self._statusbar.set_has_resize_grip(True)
        self.backend = library_backend.LibraryBackend()
        self.book_area = library_book_area._BookArea(self)
        self.control_area = library_control_area._ControlArea(self)
        self.collection_area = library_collection_area._CollectionArea(self)
        
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
        file_chooser_library_dialog.close_library_filechooser_dialog()
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
        
        library_add_progress_dialog._AddLibraryProgressDialog(self, self._window, paths, collection)
        
        if collection is not None:
            prefs['last library collection'] = collection
            
        self.collection_area.display_collections()

def open_dialog(action, window):
    global _dialog

    if _dialog is None:

        if library_backend.dbapi2 is None:
            print _('! You need an sqlite wrapper to use the library.')

        else:
            _dialog = _LibraryDialog(window, window.filehandler)

    else:
        _dialog.present()

def _close_dialog(*args):
    global _dialog

    if _dialog is not None:
        _dialog.destroy()
        _dialog = None
        constants.RUN_GARBAGE_COLLECTOR

# vim: expandtab:sw=4:ts=4

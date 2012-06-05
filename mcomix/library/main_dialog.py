"""library_main_dialog.py - The library dialog window."""

import os
import gtk

from mcomix.preferences import prefs
from mcomix import i18n
from mcomix import tools
from mcomix import log
from mcomix import file_chooser_library_dialog
from mcomix import status
from mcomix.library import backend as library_backend
from mcomix.library import book_area as library_book_area
from mcomix.library import collection_area as library_collection_area
from mcomix.library import control_area as library_control_area
from mcomix.library import add_progress_dialog as library_add_progress_dialog

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

        self.backend.watchlist.new_files_found += self._new_files_found

        table = gtk.Table(2, 2, False)
        table.attach(self.collection_area, 0, 1, 0, 1, gtk.FILL,
            gtk.EXPAND|gtk.FILL)
        table.attach(self.book_area, 1, 2, 0, 1, gtk.EXPAND|gtk.FILL,
            gtk.EXPAND|gtk.FILL)
        table.attach(self.control_area, 0, 2, 1, 2, gtk.EXPAND|gtk.FILL,
            gtk.FILL)

        if prefs['show statusbar']:
            table.attach(self._statusbar, 0, 2, 2, 3, gtk.FILL, gtk.FILL)

        self.add(table)
        self.show_all()
        self.present()

        if prefs['scan for new books on library startup']:
            self.scan_for_new_files()

    def open_book(self, books, keep_library_open=False):
        """Open the book with ID <book>."""

        paths = [ self.backend.get_book_path(book) for book in books ]

        if not keep_library_open:
            self.hide()

        self._window.present()

        if len(paths) > 1:
            self._file_handler.open_file(paths)
        elif len(paths) == 1:
            self._file_handler.open_file(paths[0])

    def scan_for_new_files(self):
        """ Start scanning for new files from the watch list. """

        if len(self.backend.watchlist.get_watchlist()) > 0:
            self.set_status_message(_("Scanning for new books..."))
            self.backend.watchlist.scan_for_new_files()

    def _new_files_found(self, filelist, watchentry):
        """ Called after the scan for new files finished. """

        if len(filelist) > 0:
            if watchentry.collection.id is not None:
                collection_name = watchentry.collection.name
            else:
                collection_name = None

            self.add_books(filelist, collection_name)

            if len(filelist) == 1:
                message = _("Added new book '%(bookname)s' "
                    "from directory '%(directory)s'.")
            else:
                message = _("Added %(count)d new books "
                    "from directory '%(directory)s'.")

            self.set_status_message(message % {'directory': watchentry.directory,
                'count': len(filelist), 'bookname': os.path.basename(filelist[0])})
        else:
            self.set_status_message(
                _("No new books found in directory '%s'.") % watchentry.directory)

    def get_status_bar(self):
        """ Returns the window's status bar. """
        return self._statusbar

    def set_status_message(self, message):
        """Set a specific message on the statusbar, replacing whatever was
        there earlier.
        """
        self._statusbar.pop(0)
        self._statusbar.push(0,
            ' ' * status.Statusbar.SPACING + '%s' % i18n.to_unicode(message))

    def close(self, *args):
        """Close the library and do required cleanup tasks."""
        prefs['lib window width'], prefs['lib window height'] = self.get_size()
        self.backend.watchlist.new_files_found -= self._new_files_found
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
            collection_id = self.collection_area.get_current_collection()
        else:
            collection = self.backend.get_collection_by_name(collection_name)

            if collection is None: # Collection by that name doesn't exist.
                self.backend.add_collection(collection_name)
                collection = self.backend.get_collection_by_name(
                    collection_name)

            collection_id = collection.id

        library_add_progress_dialog._AddLibraryProgressDialog(self, self._window, paths, collection_id)

        if collection_id is not None:
            prefs['last library collection'] = collection_id


def open_dialog(action, window):
    global _dialog

    if _dialog is None:

        if library_backend.dbapi2 is None:
            log.error( _('! You need an sqlite wrapper to use the library.') )

        else:
            _dialog = _LibraryDialog(window, window.filehandler)

    else:
        _dialog.present()

def _close_dialog(*args):
    global _dialog

    if _dialog is not None:
        _dialog.destroy()
        _dialog = None
        tools.garbage_collect()

# vim: expandtab:sw=4:ts=4

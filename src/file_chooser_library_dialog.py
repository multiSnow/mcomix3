"""file_chooser_library_dialog.py - Custom FileChooserDialog implementations."""

import os
import gtk
from preferences import prefs
import file_chooser_base_dialog

_library_filechooser_dialog = None

class _LibraryFileChooserDialog(file_chooser_base_dialog._BaseFileChooserDialog):

    """The filechooser dialog used when adding books to the library."""

    def __init__(self, library):
        file_chooser_base_dialog._BaseFileChooserDialog.__init__(self)

        self._library = library
        self.set_transient_for(library)
        self.filechooser.set_select_multiple(True)
        self.filechooser.connect('current_folder_changed',
            self._set_collection_name)

        self._collection_button = gtk.CheckButton(
            '%s:' % _('Automatically add the books to this collection'),
            False)
        self._collection_button.set_active(
            prefs['auto add books into collections'])
        self._comboentry = gtk.combo_box_entry_new_text()
        self._comboentry.child.set_activates_default(True)

        for collection in self._library.backend.get_all_collections():
            name = self._library.backend.get_collection_name(collection)
            self._comboentry.append_text(name)

        collection_box = gtk.HBox(False, 6)
        collection_box.pack_start(self._collection_button, False, False)
        collection_box.pack_start(self._comboentry, True, True)
        collection_box.show_all()
        self.filechooser.set_extra_widget(collection_box)

        filters = self.filechooser.list_filters()

        try:
            # When setting this to the first filter ("All files"), this
            # fails on some GTK+ versions and sets the filter to "blank".
            # The effect is the same though (i.e. display all files), and
            # there is no solution that I know of, so we'll have to live
            # with it. It only happens the second time a dialog is created
            # though, which is very strange.
            self.filechooser.set_filter(filters[
                prefs['last filter in library filechooser']])

        except Exception:
            self.filechooser.set_filter(filters[1])

    def _set_collection_name(self, *args):
        """Set the text in the ComboBoxEntry to the name of the current
        directory.
        """
        name = os.path.basename(self.filechooser.get_current_folder())
        self._comboentry.child.set_text(name)

    def files_chosen(self, paths):
        if paths:
            paths = [ path.decode('utf-8') for path in paths ]
            if self._collection_button.get_active():
                prefs['auto add books into collections'] = True
                collection_name = self._comboentry.get_active_text()

                if not collection_name: # No empty-string names.
                    collection_name = None

            else:
                prefs['auto add books into collections'] = False
                collection_name = None

            try: # For some reason this fails sometimes (GTK+ bug?)
                filter_index = self.filechooser.list_filters().index(
                    self.filechooser.get_filter())
                prefs['last filter in library filechooser'] = filter_index

            except Exception:
                pass

            close_library_filechooser_dialog()
            self._library.add_books(paths, collection_name)

        else:
            close_library_filechooser_dialog()

def open_library_filechooser_dialog(library):
    """Open the library filechooser dialog."""
    global _library_filechooser_dialog

    if _library_filechooser_dialog is None:
        _library_filechooser_dialog = _LibraryFileChooserDialog(library)
    else:
        _library_filechooser_dialog.present()

def close_library_filechooser_dialog(*args):
    """Close the library filechooser dialog."""
    global _library_filechooser_dialog

    if _library_filechooser_dialog is not None:
        _library_filechooser_dialog.destroy()
        _library_filechooser_dialog = None


# vim: expandtab:sw=4:ts=4

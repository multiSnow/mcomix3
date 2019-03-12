'''file_chooser_main_dialog.py - Custom FileChooserDialog implementations.'''

from gi.repository import Gtk

from mcomix.preferences import prefs
from mcomix import file_chooser_base_dialog

_main_filechooser_dialog = None

class _MainFileChooserDialog(file_chooser_base_dialog._BaseFileChooserDialog):

    '''The normal filechooser dialog used with the "Open" menu item.'''

    def __init__(self, window):
        super(_MainFileChooserDialog, self).__init__()
        self._window = window
        self.set_transient_for(window)
        self.filechooser.set_select_multiple(True)
        self.add_archive_filters()
        self.add_image_filters()
        filters = self.filechooser.list_filters()
        try:
            # When setting this to the first filter ("All files"), this
            # fails on some GTK+ versions and sets the filter to "blank".
            # The effect is the same though (i.e. display all files), and
            # there is no solution that I know of, so we'll have to live
            # with it. It only happens the second time a dialog is created
            # though, which is very strange.
            self.filechooser.set_filter(filters[
                prefs['last filter in main filechooser']])
        except:
            self.filechooser.set_filter(filters[0])

    def files_chosen(self, paths):
        if paths:
            try: # For some reason this fails sometimes (GTK+ bug?)
                filter_index = self.filechooser.list_filters().index(
                    self.filechooser.get_filter())
                prefs['last filter in main filechooser'] = filter_index
            except:
                pass
            _close_main_filechooser_dialog()

            # If more than one file is selected, restrict opening
            # further files to the selection.
            if len(paths) > 1:
                files = [ path for path in paths ]
            else:
                files = paths[0]

            self._window.filehandler.open_file(files)
        else:
            _close_main_filechooser_dialog()

def open_main_filechooser_dialog(action, window):
    '''Open the main filechooser dialog.'''
    global _main_filechooser_dialog
    if _main_filechooser_dialog is None:
        _main_filechooser_dialog = _MainFileChooserDialog(window)
    else:
        _main_filechooser_dialog.present()


def _close_main_filechooser_dialog(*args):
    '''Close the main filechooser dialog.'''
    global _main_filechooser_dialog
    if _main_filechooser_dialog is not None:
        _main_filechooser_dialog.destroy()
        _main_filechooser_dialog = None

# vim: expandtab:sw=4:ts=4

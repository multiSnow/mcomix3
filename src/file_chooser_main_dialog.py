"""file_chooser_main_dialog.py - Custom FileChooserDialog implementations."""

import gtk
from preferences import prefs
import file_chooser_base_dialog

_main_filechooser_dialog = None

class _MainFileChooserDialog(file_chooser_base_dialog._BaseFileChooserDialog):
    
    """The normal filechooser dialog used with the "Open" menu item."""
    
    def __init__(self, window):
        file_chooser_base_dialog._BaseFileChooserDialog.__init__(self)
        self._window = window
        self.set_transient_for(window)

        ffilter = gtk.FileFilter()
        ffilter.add_pixbuf_formats()
        ffilter.set_name(_('All images'))
        self.filechooser.add_filter(ffilter)
        self.add_filter(_('JPEG images'), ('image/jpeg',))
        self.add_filter(_('PNG images'), ('image/png',))
        self.add_filter(_('GIF images'), ('image/gif',))
        self.add_filter(_('TIFF images'), ('image/tiff',))
        self.add_filter(_('BMP images'), ('image/bmp',))

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
            file = paths[0].decode('utf-8')
            self._window.filehandler.open_file(file)
        else:
            _close_main_filechooser_dialog()
    
def open_main_filechooser_dialog(action, window):
    """Open the main filechooser dialog."""
    global _main_filechooser_dialog
    if _main_filechooser_dialog is None:
        _main_filechooser_dialog = _MainFileChooserDialog(window)
    else:
        _main_filechooser_dialog.present()


def _close_main_filechooser_dialog(*args):
    """Close the main filechooser dialog."""
    global _main_filechooser_dialog
    if _main_filechooser_dialog is not None:
        _main_filechooser_dialog.destroy()
        _main_filechooser_dialog = None

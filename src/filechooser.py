"""filechooser.py - Custom FileChooserDialog implementations."""

import os

import gtk
import pango

import encoding
import image
import labels
from preferences import prefs
import thumbnail

_main_filechooser_dialog = None
_library_filechooser_dialog = None


class _ComicFileChooserDialog(gtk.Dialog):

    """We roll our own FileChooserDialog because the one in GTK seems
    buggy with the preview widget. The <action> argument dictates what type
    of filechooser dialog we want (i.e. it is gtk.FILE_CHOOSER_ACTION_OPEN
    or gtk.FILE_CHOOSER_ACTION_SAVE).
    
    This is a base class for the _MainFileChooserDialog, the
    _LibraryFileChooserDialog and the StandAloneFileChooserDialog.

    Subclasses should implement a method files_chosen(paths) that will be
    called once the filechooser has done its job and selected some files.
    If the dialog was closed or Cancel was pressed, <paths> is the empty list.
    """
    
    _last_activated_file = None

    def __init__(self, action=gtk.FILE_CHOOSER_ACTION_OPEN):
        self._action = action
        if action == gtk.FILE_CHOOSER_ACTION_OPEN:
            title = _('Open')
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        else:
            title = _('Save')
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        gtk.Dialog.__init__(self, title, None, 0, buttons)
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_has_separator(False)

        self.filechooser = gtk.FileChooserWidget(action=action)
        self.filechooser.set_size_request(680, 420)
        self.vbox.pack_start(self.filechooser)
        self.set_border_width(4)
        self.filechooser.set_border_width(6)
        self.connect('response', self._response)
        self.filechooser.connect('file_activated', self._response,
            gtk.RESPONSE_OK)

        preview_box = gtk.VBox(False, 10)
        preview_box.set_size_request(130, 0)
        self._preview_image = gtk.Image()
        self._preview_image.set_size_request(130, 130)
        preview_box.pack_start(self._preview_image, False, False)
        self.filechooser.set_preview_widget(preview_box)
        self._namelabel = labels.FormattedLabel(weight=pango.WEIGHT_BOLD,
            scale=pango.SCALE_SMALL)
        self._namelabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        preview_box.pack_start(self._namelabel, False, False)
        self._sizelabel = labels.FormattedLabel(scale=pango.SCALE_SMALL)
        self._sizelabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        preview_box.pack_start(self._sizelabel, False, False)
        self.filechooser.set_use_preview_label(False)
        preview_box.show_all()
        self.filechooser.connect('update-preview', self._update_preview)

        ffilter = gtk.FileFilter()
        ffilter.add_pattern('*')
        ffilter.set_name(_('All files'))
        self.filechooser.add_filter(ffilter)

        self.add_filter(_('All Archives'), ('application/x-zip',
            'application/zip', 'application/x-rar', 'application/x-tar',
            'application/x-gzip', 'application/x-bzip2', 'application/x-cbz',
            'application/x-cbr', 'application/x-cbt'))
        self.add_filter(_('ZIP archives'),
            ('application/x-zip', 'application/zip', 'application/x-cbz'))
        self.add_filter(_('RAR archives'),
            ('application/x-rar', 'application/x-cbr'))
        self.add_filter(_('Tar archives'),
            ('application/x-tar', 'application/x-gzip',
            'application/x-bzip2', 'application/x-cbt'))
        
        try:
            if (self.__class__._last_activated_file is not None
                    and os.path.isfile(self.__class__._last_activated_file)):
                self.filechooser.set_filename(
                    self.__class__._last_activated_file)
            elif os.path.isdir(prefs['path of last browsed in filechooser']):
                self.filechooser.set_current_folder(
                    prefs['path of last browsed in filechooser'])
        except Exception: # E.g. broken prefs values.
            pass
        self.show_all()

    def add_filter(self, name, mimes):
        """Add a filter, called <name>, for each mime type in <mimes> to
        the filechooser.
        """
        ffilter = gtk.FileFilter()
        for mime in mimes:
            ffilter.add_mime_type(mime)
        ffilter.set_name(name)
        self.filechooser.add_filter(ffilter)

    def set_save_name(self, name):
        self.filechooser.set_current_name(name)

    def set_current_directory(self, path):
        self.filechooser.set_current_folder(path)

    def _response(self, widget, response):
        """Return a list of the paths of the chosen files, or None if the 
        event only changed the current directory.
        """
        if response == gtk.RESPONSE_OK:
            paths = self.filechooser.get_filenames()
            if len(paths) == 1 and os.path.isdir(paths[0]):
                self.filechooser.set_current_folder(paths[0])
                self.emit_stop_by_name('response')
                return
            if not paths:
                return
            # FileChooser.set_do_overwrite_confirmation() doesn't seem to
            # work on our custom dialog, so we use a simple alternative.
            if (self._action == gtk.FILE_CHOOSER_ACTION_SAVE
              and os.path.exists(paths[0])):
                overwrite_dialog = gtk.MessageDialog(None, 0,
                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,
                    _("A file named '%s' already exists. Do you want to replace it?") %
                    os.path.basename(paths[0]))
                overwrite_dialog.format_secondary_text(
                    _('Replacing it will overwrite its contents.'))
                response = overwrite_dialog.run()
                overwrite_dialog.destroy()
                if response != gtk.RESPONSE_OK:
                    self.emit_stop_by_name('response')
                    return
            prefs['path of last browsed in filechooser'] = \
                self.filechooser.get_current_folder()
            self.__class__._last_activated_file = paths[0]
            self.files_chosen(paths)
        else:
            self.files_chosen([])

    def _update_preview(self, *args):
        path = self.filechooser.get_preview_filename()
        if path and os.path.isfile(path):
            pixbuf = thumbnail.get_thumbnail(path, prefs['create thumbnails'])
            if pixbuf is None:
                self._preview_image.clear()
                self._namelabel.set_text('')
                self._sizelabel.set_text('')
            else:
                pixbuf = image.add_border(pixbuf, 1)
                self._preview_image.set_from_pixbuf(pixbuf)
                self._namelabel.set_text(encoding.to_unicode(
                    os.path.basename(path)))
                self._sizelabel.set_text(
                    '%.1f KiB' % (os.stat(path).st_size / 1024.0))
        else:
            self._preview_image.clear()
            self._namelabel.set_text('')
            self._sizelabel.set_text('')


class _MainFileChooserDialog(_ComicFileChooserDialog):
    
    """The normal filechooser dialog used with the "Open" menu item."""
    
    def __init__(self, window):
        _ComicFileChooserDialog.__init__(self)
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
            self._window.file_handler.open_file(paths[0])
        else:
            _close_main_filechooser_dialog()
    
class _LibraryFileChooserDialog(_ComicFileChooserDialog):
    
    """The filechooser dialog used when adding books to the library."""
    
    def __init__(self, library):
        _ComicFileChooserDialog.__init__(self)
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


class StandAloneFileChooserDialog(_ComicFileChooserDialog):
    
    """A simple filechooser dialog that is designed to be used with the
    gtk.Dialog.run() method. The <action> dictates what type of filechooser
    dialog we want (i.e. save or open). If the type is an open-dialog, we
    use multiple selection by default.
    """
    
    def __init__(self, action=gtk.FILE_CHOOSER_ACTION_OPEN):
        _ComicFileChooserDialog.__init__(self, action)
        if action == gtk.FILE_CHOOSER_ACTION_OPEN:
            self.filechooser.set_select_multiple(True)
        self._paths = None

        ffilter = gtk.FileFilter()
        ffilter.add_pixbuf_formats()
        ffilter.set_name(_('All images'))
        self.filechooser.add_filter(ffilter)
        self.add_filter(_('JPEG images'), ('image/jpeg',))
        self.add_filter(_('PNG images'), ('image/png',))
        self.add_filter(_('GIF images'), ('image/gif',))
        self.add_filter(_('TIFF images'), ('image/tiff',))
        self.add_filter(_('BMP images'), ('image/bmp',))

    def get_paths(self):
        """Return the selected paths. To be called after run() has returned
        a response.
        """
        return self._paths

    def files_chosen(self, paths):
        self._paths = paths


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

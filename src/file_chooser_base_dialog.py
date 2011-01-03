"""filechooser_chooser_base_dialog.py - Custom FileChooserDialog implementations."""

import os
import gtk
import pango
import encoding
import image_tools
import labels
from preferences import prefs
import thumbnail_tools

class _BaseFileChooserDialog(gtk.Dialog):

    """We roll our own FileChooserDialog because the one in GTK seems
    buggy with the preview widget. The <action> argument dictates what type
    of filechooser dialog we want (i.e. it is gtk.FILE_CHOOSER_ACTION_OPEN
    or gtk.FILE_CHOOSER_ACTION_SAVE).
    
    This is a base class for the _MainFileChooserDialog, the
    _LibraryFileChooserDialog and the SimpleFileChooserDialog.

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
        path = self.filechooser.get_preview_filename().decode('utf-8')

        if path and os.path.isfile(path):
            pixbuf = thumbnail_tools.get_thumbnail(path, prefs['create thumbnails'])

            if pixbuf is None:
                self._preview_image.clear()
                self._namelabel.set_text('')
                self._sizelabel.set_text('')

            else:
                pixbuf = image_tools.add_border(pixbuf, 1)
                self._preview_image.set_from_pixbuf(pixbuf)
                self._namelabel.set_text(os.path.basename(path))
                self._sizelabel.set_text(
                    '%.1f KiB' % (os.stat(path).st_size / 1024.0))
        else:
            self._preview_image.clear()
            self._namelabel.set_text('')
            self._sizelabel.set_text('')

# vim: expandtab:sw=4:ts=4

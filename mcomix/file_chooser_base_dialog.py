"""filechooser_chooser_base_dialog.py - Custom FileChooserDialog implementations."""

import os
import mimetypes
import gtk
import pango

import main
import image_tools
import labels
import constants
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
        self.filechooser.connect('destroy-event', self._window_destroyed)
        self._destroyed = False
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

        self._all_files_filter = self.add_filter(
            _('All files'), [], ['*'])

        # Determine which types should go into 'All archives' based on
        # extractor availability.
        mimetypes = constants.ZIP_FORMATS[0] + constants.TAR_FORMATS[0]
        patterns = constants.ZIP_FORMATS[1] + constants.TAR_FORMATS[1]
        if constants.RAR_AVAILABLE():
            mimetypes += constants.RAR_FORMATS[0]
            patterns += constants.RAR_FORMATS[1]
        if constants.SZIP_AVAILABLE():
            mimetypes += constants.SZIP_FORMATS[0]
            patterns += constants.SZIP_FORMATS[1]
        if constants.LHA_AVAILABLE():
            mimetypes += constants.LHA_FORMATS[0]
            patterns += constants.LHA_FORMATS[1]

        self.add_filter(_('All Archives'),
            mimetypes, patterns)

        self.add_filter(_('ZIP archives'),
                *constants.ZIP_FORMATS)

        self.add_filter(_('Tar archives'),
            *constants.TAR_FORMATS)

        if constants.RAR_AVAILABLE():
            self.add_filter(_('RAR archives'),
                *constants.RAR_FORMATS)

        if constants.SZIP_AVAILABLE():
            self.add_filter(_('7z archives'),
                *constants.SZIP_FORMATS)

        if constants.LHA_AVAILABLE():
            self.add_filter(_('LHA archives'),
                *constants.LHA_FORMATS)

        try:
            current_file = main.main_window().filehandler.get_path_to_base()
            last_file = self.__class__._last_activated_file

            # If a file is currently open, use its path
            if current_file and os.path.exists(current_file):
                self.filechooser.set_current_folder(os.path.dirname(current_file))
            # If no file is open, use the last stored file
            elif (last_file and os.path.exists(last_file)):
                self.filechooser.set_filename(last_file)
            # If no file was stored yet, fall back to preferences
            elif os.path.isdir(prefs['path of last browsed in filechooser']):
                self.filechooser.set_current_folder(
                    prefs['path of last browsed in filechooser'])

        except Exception: # E.g. broken prefs values.
            pass

        self.show_all()

    def add_filter(self, name, mimes, patterns=[]):
        """Add a filter, called <name>, for each mime type in <mimes> and
        each pattern in <patterns> to the filechooser.
        """
        ffilter = gtk.FileFilter()

        for mime in mimes:
            ffilter.add_mime_type(mime)
        for pattern in patterns:
            ffilter.add_pattern(pattern)

        ffilter.set_name(name)
        self.filechooser.add_filter(ffilter)
        return ffilter

    def collect_files_from_subdir(self, path, filter, recursive=False):
        """ Finds archives within C{path} that match the
        L{gtk.FileFilter} passed in C{filter}. """
        mimetypes.init()

        for root, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                mimetype = mimetypes.guess_type(full_path)[0]

                if (filter == self._all_files_filter or
                    filter.filter((full_path.encode('utf-8'),
                    None, None, mimetype))):

                    yield full_path

            if not recursive:
                break

    def set_save_name(self, name):
        self.filechooser.set_current_name(name)

    def set_current_directory(self, path):
        self.filechooser.set_current_folder(path)

    def should_open_recursive(self):
        return False

    def _response(self, widget, response):
        """Return a list of the paths of the chosen files, or None if the
        event only changed the current directory.
        """
        if response == gtk.RESPONSE_OK:
            if not self.filechooser.get_filenames():
                return

            # Collect files, if necessary also from subdirectories
            filter = self.filechooser.get_filter()
            paths = [ ]
            for path in self.filechooser.get_filenames():
                path = path.decode('utf-8')

                if os.path.isdir(path):
                    paths.extend(self.collect_files_from_subdir(path, filter,
                        self.should_open_recursive()))
                else:
                    paths.append(path)

            # FileChooser.set_do_overwrite_confirmation() doesn't seem to
            # work on our custom dialog, so we use a simple alternative.
            first_path = self.filechooser.get_filenames()[0].decode('utf-8')
            if (self._action == gtk.FILE_CHOOSER_ACTION_SAVE and
                not os.path.isdir(first_path) and
                os.path.exists(first_path)):

                overwrite_dialog = gtk.MessageDialog(None, 0,
                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL,
                    _("A file named '%s' already exists. Do you want to replace it?") %
                    os.path.basename(first_path))

                overwrite_dialog.format_secondary_text(
                    _('Replacing it will overwrite its contents.'))
                response = overwrite_dialog.run()
                overwrite_dialog.destroy()

                if response != gtk.RESPONSE_OK:
                    self.emit_stop_by_name('response')
                    return

            prefs['path of last browsed in filechooser'] = \
                self.filechooser.get_current_folder()
            self.__class__._last_activated_file = first_path
            self.files_chosen(paths)

        else:
            self.files_chosen([])

    def _update_preview(self, *args):
        if self.filechooser.get_preview_filename():
            path = self.filechooser.get_preview_filename().decode('utf-8')
        else:
            path = None

        if path and os.path.isfile(path):
            thumbnailer = thumbnail_tools.Thumbnailer()
            thumbnailer.set_size(128, 128)
            thumbnailer.thumbnail_finished += self._preview_thumbnail_finished
            pixbuf = thumbnailer.thumbnail(path, async=True)
        else:
            self._preview_image.clear()
            self._namelabel.set_text('')
            self._sizelabel.set_text('')

    def _preview_thumbnail_finished(self, filepath, pixbuf):
        """ Called when the thumbnailer has finished creating
        the thumbnail for <filepath>. """

        if self._destroyed:
            return

        current_path = self.filechooser.get_preview_filename()
        if current_path and current_path.decode('utf-8') == filepath:

            if pixbuf is None:
                self._preview_image.clear()
                self._namelabel.set_text('')
                self._sizelabel.set_text('')

            else:
                pixbuf = image_tools.add_border(pixbuf, 1)
                self._preview_image.set_from_pixbuf(pixbuf)
                self._namelabel.set_text(os.path.basename(filepath))
                self._sizelabel.set_text(
                    '%.1f KiB' % (os.stat(filepath).st_size / 1024.0))

    def _window_destroyed(self, *args):
        """ Called when the dialog is being destroyed. """
        self._destroyed = True

# vim: expandtab:sw=4:ts=4

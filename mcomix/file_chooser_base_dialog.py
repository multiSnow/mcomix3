"""filechooser_chooser_base_dialog.py - Custom FileChooserDialog implementations."""

import os
import mimetypes
import fnmatch
import gtk
import pango

from mcomix.preferences import prefs
from mcomix import image_tools
from mcomix import archive_tools
from mcomix import labels
from mcomix import constants
from mcomix import log
from mcomix import thumbnail_tools
from mcomix import message_dialog
from mcomix import file_provider

mimetypes.init()

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
        self._destroyed = False

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

        pango_scale_small = (1 / 1.2)

        self._namelabel = labels.FormattedLabel(weight=pango.WEIGHT_BOLD,
            scale=pango_scale_small)
        self._namelabel.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        preview_box.pack_start(self._namelabel, False, False)

        self._sizelabel = labels.FormattedLabel(scale=pango_scale_small)
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
        if archive_tools.rar_available():
            mimetypes += constants.RAR_FORMATS[0]
            patterns += constants.RAR_FORMATS[1]
        if archive_tools.szip_available():
            mimetypes += constants.SZIP_FORMATS[0]
            patterns += constants.SZIP_FORMATS[1]
        if archive_tools.lha_available():
            mimetypes += constants.LHA_FORMATS[0]
            patterns += constants.LHA_FORMATS[1]

        self.add_filter(_('All Archives'),
            mimetypes, patterns)

        self.add_filter(_('ZIP archives'),
                *constants.ZIP_FORMATS)

        self.add_filter(_('Tar archives'),
            *constants.TAR_FORMATS)

        if archive_tools.rar_available():
            self.add_filter(_('RAR archives'),
                *constants.RAR_FORMATS)

        if archive_tools.szip_available():
            self.add_filter(_('7z archives'),
                *constants.SZIP_FORMATS)

        if archive_tools.lha_available():
            self.add_filter(_('LHA archives'),
                *constants.LHA_FORMATS)

        try:
            current_file = self._current_file()
            last_file = self.__class__._last_activated_file

            # If a file is currently open, use its path
            if current_file and os.path.exists(current_file):
                self.filechooser.set_current_folder(os.path.dirname(current_file))
            # If no file is open, use the last stored file
            elif (last_file and os.path.exists(last_file)):
                self.filechooser.set_filename(last_file)
            # If no file was stored yet, fall back to preferences
            elif os.path.isdir(prefs['path of last browsed in filechooser']):
                if prefs['store recent file info']:
                    self.filechooser.set_current_folder(
                        prefs['path of last browsed in filechooser'])
                else:
                    self.filechooser.set_current_folder(
                        constants.HOME_DIR)

        except Exception, ex: # E.g. broken prefs values.
            log.debug(ex)

        self.show_all()

    def add_filter(self, name, mimes, patterns=[]):
        """Add a filter, called <name>, for each mime type in <mimes> and
        each pattern in <patterns> to the filechooser.
        """
        ffilter = gtk.FileFilter()
        ffilter.add_custom(
                gtk.FILE_FILTER_FILENAME|gtk.FILE_FILTER_MIME_TYPE,
                self._filter, (patterns, mimes))

        ffilter.set_name(name)
        self.filechooser.add_filter(ffilter)
        return ffilter

    def _filter(self, filter_info, data):
        """ Callback function used to determine if a file
        should be filtered or not. C{data} is a tuple containing
        (patterns, mimes) that should pass the test. Returns True
        if the file passed in C{filter_info} should be displayed. """

        path, uri, display, mime = filter_info
        match_patterns, match_mimes = data

        matches_mime = bool(filter(
            lambda match_mime: match_mime == mime,
            match_mimes))
        matches_pattern = bool(filter(
            lambda match_pattern: fnmatch.fnmatch(path, match_pattern),
            match_patterns))

        return matches_mime or matches_pattern

    def collect_files_from_subdir(self, path, filter, recursive=False):
        """ Finds archives within C{path} that match the
        L{gtk.FileFilter} passed in C{filter}. """

        for root, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                mimetype = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'

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
                    subdir_files = list(self.collect_files_from_subdir(path, filter,
                        self.should_open_recursive()))
                    file_provider.FileProvider.sort_files(subdir_files)
                    paths.extend(subdir_files)
                else:
                    paths.append(path)

            # FileChooser.set_do_overwrite_confirmation() doesn't seem to
            # work on our custom dialog, so we use a simple alternative.
            first_path = self.filechooser.get_filenames()[0].decode('utf-8')
            if (self._action == gtk.FILE_CHOOSER_ACTION_SAVE and
                not os.path.isdir(first_path) and
                os.path.exists(first_path)):

                overwrite_dialog = message_dialog.MessageDialog(None, 0,
                    gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK_CANCEL)
                overwrite_dialog.set_text(
                    _("A file named '%s' already exists. Do you want to replace it?") %
                        os.path.basename(first_path),
                    _('Replacing it will overwrite its contents.'))
                response = overwrite_dialog.run()

                if response != gtk.RESPONSE_OK:
                    self.emit_stop_by_name('response')
                    return

            # Do not store path if the user chose not to keep a file history
            if prefs['store recent file info']:
                prefs['path of last browsed in filechooser'] = \
                    self.filechooser.get_current_folder()
            else:
                prefs['path of last browsed in filechooser'] = \
                    constants.HOME_DIR

            self.__class__._last_activated_file = first_path
            self.files_chosen(paths)

        else:
            self.files_chosen([])

        self._destroyed = True

    def _update_preview(self, *args):
        if self.filechooser.get_preview_filename():
            path = self.filechooser.get_preview_filename().decode('utf-8')
        else:
            path = None

        if path and os.path.isfile(path):
            thumbnailer = thumbnail_tools.Thumbnailer()
            thumbnailer.set_size(128, 128)
            thumbnailer.thumbnail_finished += self._preview_thumbnail_finished
            thumbnailer.thumbnail(path, async=True)
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

    def _current_file(self):
        # XXX: This method defers the import of main to avoid cyclic imports
        # during startup.

        from mcomix import main
        return main.main_window().filehandler.get_path_to_base()

# vim: expandtab:sw=4:ts=4

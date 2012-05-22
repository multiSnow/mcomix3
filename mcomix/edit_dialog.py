"""edit_dialog.py - The dialog for the archive editing window."""

import os
import tempfile
import gobject
import gtk
import re

from mcomix.preferences import prefs
from mcomix import archive_packer
from mcomix import file_chooser_simple_dialog
from mcomix import image_tools
from mcomix import edit_image_area
from mcomix import edit_comment_area
from mcomix import constants
from mcomix import message_dialog

_dialog = None

class _EditArchiveDialog(gtk.Dialog):

    """The _EditArchiveDialog lets users edit archives (or directories) by
    reordering images and removing and adding images or comment files. The
    result can be saved as a ZIP archive.
    """

    def __init__(self, window):
        gtk.Dialog.__init__(self, _('Edit archive'), window, gtk.DIALOG_MODAL,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))

        self._accept_changes_button = self.add_button(gtk.STOCK_APPLY, gtk.RESPONSE_APPLY)

        self.kill = False # Dialog is killed.
        self.file_handler = window.filehandler
        self._window = window
        self._imported_files = []

        self._save_button = self.add_button(gtk.STOCK_SAVE_AS, constants.RESPONSE_SAVE_AS)

        self._import_button = self.add_button(_('_Import'), constants.RESPONSE_IMPORT)
        self._import_button.set_image(gtk.image_new_from_stock(gtk.STOCK_ADD,
            gtk.ICON_SIZE_BUTTON))

        self.set_has_separator(False)
        self.set_border_width(4)
        self.resize(min(gtk.gdk.screen_get_default().get_width() - 50, 750),
            min(gtk.gdk.screen_get_default().get_height() - 50, 600))

        self.connect('response', self._response)

        self._image_area = edit_image_area._ImageArea(self, window)
        self._comment_area = edit_comment_area._CommentArea(self)

        notebook = gtk.Notebook()
        notebook.set_border_width(6)
        notebook.append_page(self._image_area, gtk.Label(_('Images')))
        notebook.append_page(self._comment_area, gtk.Label(_('Comment files')))
        self.vbox.pack_start(notebook)

        self.show_all()

        gobject.idle_add(self._load_original_files)

    def _load_original_files(self):
        """Load the original files from the archive or directory into
        the edit dialog.
        """
        self._save_button.set_sensitive(False)
        self._import_button.set_sensitive(False)
        self._window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self._image_area.fetch_images()

        if self.kill: # fetch_images() allows pending events to be handled.
            return False

        self._comment_area.fetch_comments()
        self._window.set_cursor(None)
        self._save_button.set_sensitive(True)
        self._import_button.set_sensitive(True)

        return False

    def _pack_archive(self, archive_path):
        """Create a new archive with the chosen files."""
        self.set_sensitive(False)
        self._window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

        while gtk.events_pending():
            gtk.main_iteration(False)

        image_files = self._image_area.get_file_listing()
        comment_files = self._comment_area.get_file_listing()

        try:
            fd, tmp_path = tempfile.mkstemp(
                suffix='.%s' % os.path.basename(archive_path),
                prefix='tmp.', dir=os.path.dirname(archive_path))
            # Close open tempfile handle (writing is handled by the packer)
            os.close(fd)
            fail = False

        except:
            fail = True

        if not fail:
            packer = archive_packer.Packer(image_files, comment_files, tmp_path,
                os.path.splitext(os.path.basename(archive_path))[0])
            packer.pack()
            packing_success = packer.wait()

            if packing_success:
                # Preserve permissions if currently edited files come from an archive
                if (self._window.filehandler.archive_type is not None and
                    os.path.exists(self._window.filehandler.get_path_to_base())):
                    mode = os.stat(self._window.filehandler.get_path_to_base()).st_mode
                else:
                    mode = os.stat(tmp_path).st_mode

                # Remove existing file (Win32 fails on rename otherwise)
                if os.path.exists(archive_path):
                    os.unlink(archive_path)

                os.rename(tmp_path, archive_path)
                os.chmod(archive_path, mode)

                _close_dialog()
            else:
                fail = True
        
        self._window.set_cursor(None)
        if fail:
            dialog = message_dialog.MessageDialog(self._window, 0, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_CLOSE)
            dialog.set_text(
                _("The new archive could not be saved!"),
                _("The original files have not been removed."))
            dialog.run()

            self.set_sensitive(True)

    def _response(self, dialog, response):

        if response == constants.RESPONSE_SAVE_AS:

            dialog = file_chooser_simple_dialog.SimpleFileChooserDialog(
                gtk.FILE_CHOOSER_ACTION_SAVE)

            src_path = self.file_handler.get_path_to_base()

            dialog.set_current_directory(os.path.dirname(src_path))
            dialog.set_save_name('%s.cbz' % os.path.splitext(
                os.path.basename(src_path))[0])
            dialog.filechooser.set_extra_widget(gtk.Label(
                _('Archives are stored as ZIP files.')))
            dialog.run()

            paths = dialog.get_paths()
            dialog.destroy()

            if paths:
                self._pack_archive(paths[0])

        elif response == constants.RESPONSE_IMPORT:

            dialog = file_chooser_simple_dialog.SimpleFileChooserDialog()
            dialog.run()
            paths = dialog.get_paths()
            dialog.destroy()

            exts = '|'.join(prefs['comment extensions'])
            comment_re = re.compile(r'\.(%s)\s*$' % exts, re.I)

            for path in paths:

                if image_tools.is_image_file(path):
                    self._imported_files.append( path )
                    self._image_area.add_extra_image(path)

                elif os.path.isfile(path):

                    if comment_re.search( path ):
                        self._imported_files.append( path )
                        self._comment_area.add_extra_file(path)

        elif response == gtk.RESPONSE_APPLY:

            old_image_array = self._window.imagehandler._image_files

            treeiter = self._image_area._liststore.get_iter_root()

            new_image_array = []

            while treeiter is not None:
                path = self._image_area._liststore.get_value(treeiter, 2)
                new_image_array.append(path)
                treeiter = self._image_area._liststore.iter_next(treeiter)

            new_positions = []

            end_index = len(old_image_array) - 1

            for image_path in old_image_array:

                try:
                    new_position = new_image_array.index( image_path )
                    new_positions.append(new_position)
                except ValueError:
                    # the path was not found in the new array so that means it was deleted
                    new_positions.append(end_index)
                    end_index -= 1

            self._window.imagehandler._image_files = new_image_array
            self._window.imagehandler._raw_pixbufs = {}
            self._window.imagehandler.do_cacheing()

            self._window.thumbnailsidebar.clear()
            self._window.thumbnailsidebar.load_thumbnails()

            while self._window.imagehandler.is_cacheing and \
                  not self._window.thumbnailsidebar._is_loading:
                while gtk.events_pending():
                    gtk.main_iteration(False)

            self._window.set_page(1)
            self._window.thumbnailsidebar._selection_is_forced = False

        else:
            _close_dialog()
            self.kill = True

def open_dialog(action, window):
    global _dialog

    if _dialog is None:
        _dialog = _EditArchiveDialog(window)
    else:
        _dialog.present()


def _close_dialog(*args):
    global _dialog

    if _dialog is not None:
        _dialog.destroy()
        _dialog = None

# vim: expandtab:sw=4:ts=4

'''edit_dialog.py - The dialog for the archive editing window.'''

import os
import tempfile
from gi.repository import Gdk, Gtk, GLib
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

class _EditArchiveDialog(Gtk.Dialog):

    '''The _EditArchiveDialog lets users edit archives (or directories) by
    reordering images and removing and adding images or comment files. The
    result can be saved as a ZIP archive.
    '''

    def __init__(self, window):
        super(_EditArchiveDialog, self).__init__(title=_('Edit archive'), modal=True)
        self.set_transient_for(window)
        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)

        self._accept_changes_button = self.add_button(Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY)

        self.kill = False # Dialog is killed.
        self.file_handler = window.filehandler
        self._window = window
        self._imported_files = []

        self._save_button = self.add_button(Gtk.STOCK_SAVE_AS, constants.RESPONSE_SAVE_AS)

        self._import_button = self.add_button(_('_Import'), constants.RESPONSE_IMPORT)
        self._import_button.set_image(Gtk.Image.new_from_stock(Gtk.STOCK_ADD,
            Gtk.IconSize.BUTTON))

        self.set_border_width(4)
        self.resize(min(Gdk.Screen.get_default().get_width() - 50, 750),
            min(Gdk.Screen.get_default().get_height() - 50, 600))

        self.connect('response', self._response)

        self._image_area = edit_image_area._ImageArea(self, window)
        self._comment_area = edit_comment_area._CommentArea(self)

        notebook = Gtk.Notebook()
        notebook.set_border_width(6)
        notebook.append_page(self._image_area, Gtk.Label(label=_('Images')))
        notebook.append_page(self._comment_area, Gtk.Label(label=_('Comment files')))
        self.vbox.pack_start(notebook, True, True, 0)

        self.show_all()

        GLib.idle_add(self._load_original_files)

    def _load_original_files(self):
        '''Load the original files from the archive or directory into
        the edit dialog.
        '''
        self._save_button.set_sensitive(False)
        self._import_button.set_sensitive(False)
        self._window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self._image_area.fetch_images()

        if self.kill: # fetch_images() allows pending events to be handled.
            return False

        self._comment_area.fetch_comments()
        self._window.set_cursor(None)
        self._save_button.set_sensitive(True)
        self._import_button.set_sensitive(True)

        return False

    def _pack_archive(self, archive_path):
        '''Create a new archive with the chosen files.'''
        self.set_sensitive(False)
        self._window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))

        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

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
            dialog = message_dialog.MessageDialog(
                self._window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CLOSE)
            dialog.set_text(
                _('The new archive could not be saved!'),
                _('The original files have not been removed.'))
            dialog.run()

            self.set_sensitive(True)

    def _response(self, dialog, response):

        if response == constants.RESPONSE_SAVE_AS:

            dialog = file_chooser_simple_dialog.SimpleFileChooserDialog(
                self, Gtk.FileChooserAction.SAVE)

            src_path = self.file_handler.get_path_to_base()

            dialog.set_current_directory(os.path.dirname(src_path))
            dialog.set_save_name('%s.cbz' % os.path.splitext(
                os.path.basename(src_path))[0])
            dialog.filechooser.set_extra_widget(Gtk.Label(label=
                _('Archives are stored as ZIP files.')))
            dialog.add_archive_filters()
            dialog.run()

            paths = dialog.get_paths()
            dialog.destroy()

            if paths:
                self._pack_archive(paths[0])

        elif response == constants.RESPONSE_IMPORT:

            dialog = file_chooser_simple_dialog.SimpleFileChooserDialog(self)
            dialog.add_image_filters()
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

        elif response == Gtk.ResponseType.APPLY:

            old_image_array = self._window.imagehandler.get_image_files()

            treeiter = self._image_area._liststore.get_iter_first()

            new_image_array = []

            while treeiter is not None:
                path = self._image_area._liststore.get_value(treeiter, 2)
                new_image_array.append(path)
                treeiter = self._image_area._liststore.iter_next(treeiter)

            new_positions = []

            end_index = len(old_image_array) - 1

            for image_path in old_image_array:

                try:
                    new_position = new_image_array.index(image_path)
                    new_positions.append(new_position)
                except ValueError:
                    # the path was not found in the new array so that means it was deleted
                    new_positions.append(end_index)
                    end_index -= 1

            self._window.imagehandler.set_image_files(new_image_array)
            self._window.imagehandler.clear_raw_pixbufs()
            self._window.imagehandler.do_cacheing()
            self._window.thumbnailsidebar.clear()
            self._window.set_page(1)
            self._window.thumbnailsidebar.load_thumbnails()

        else:
            _close_dialog()
            self.kill = True

    def destroy(self):
        self._image_area.cleanup()
        Gtk.Dialog.destroy(self)

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

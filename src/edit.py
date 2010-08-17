"""edit.py - Archive editor."""

import os
import tempfile

import gobject
import gtk
import pango

import archive
import cursor
import encoding
import filechooser
import filehandler
import image
import thumbnail

_dialog = None


class _EditArchiveDialog(gtk.Dialog):
    
    """The _EditArchiveDialog lets users edit archives (or directories) by
    reordering images and removing and adding images or other files. The
    result can be saved as a ZIP archive.
    """

    def __init__(self, window):
        gtk.Dialog.__init__(self, _('Edit archive'), window, gtk.DIALOG_MODAL,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        self.kill = False # Dialog is killed.
        self.file_handler = window.file_handler
        self._window = window
        self._save_button = self.add_button(gtk.STOCK_SAVE_AS, gtk.RESPONSE_OK)
        # There is no stock response for "import", but by using
        # RESPONSE_HELP we automatically get the button placed at the left.
        self._import_button = self.add_button(_('Import'), gtk.RESPONSE_HELP)
        self._import_button.set_image(gtk.image_new_from_stock(gtk.STOCK_ADD,
            gtk.ICON_SIZE_BUTTON))
        self.set_has_separator(False)
        self.set_border_width(4)
        self.resize(min(gtk.gdk.screen_get_default().get_width() - 50, 750),
            min(gtk.gdk.screen_get_default().get_height() - 50, 600))
        self.connect('response', self._response)
        
        self._image_area = _ImageArea(self)
        self._other_area = _OtherArea(self)

        notebook = gtk.Notebook()
        notebook.set_border_width(6)
        notebook.append_page(self._image_area, gtk.Label(_('Images')))
        notebook.append_page(self._other_area, gtk.Label(_('Other files')))
        self.vbox.pack_start(notebook)
        self.show_all()
        gobject.idle_add(self._load_original_files)

    def _load_original_files(self):
        """Load the original files from the archive or directory into
        the edit dialog.
        """
        self._save_button.set_sensitive(False)
        self._import_button.set_sensitive(False)
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self._image_area.fetch_images()
        if self.kill: # fetch_images() allows pending events to be handled.
            return False
        self._other_area.fetch_comments()
        self.window.set_cursor(None)
        self._save_button.set_sensitive(True)
        self._import_button.set_sensitive(True)
        return False

    def _pack_archive(self, archive_path):
        """Create a new archive with the chosen files."""
        self.set_sensitive(False)
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        while gtk.events_pending():
            gtk.main_iteration(False)
        image_files = self._image_area.get_file_listing()
        other_files = self._other_area.get_file_listing()
        try:
            tmp_path = tempfile.mkstemp(
                suffix='.%s' % os.path.basename(archive_path),
                prefix='tmp.', dir=os.path.dirname(archive_path))[1]
            fail = False
        except:
            fail = True
        if not fail:
            packer = archive.Packer(image_files, other_files, tmp_path,
                os.path.splitext(os.path.basename(archive_path))[0])
            packer.pack()
            packing_success = packer.wait()
            if packing_success:
                os.rename(tmp_path, archive_path)
                _close_dialog()
            else:
                fail = True
        if fail:
            self.window.set_cursor(None)
            dialog = gtk.MessageDialog(self._window, 0, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_CLOSE, _("The new archive could not be saved!"))
            dialog.format_secondary_text(
                _("The original files have not been removed."))
            dialog.run()
            dialog.destroy()
            self.set_sensitive(True)

    def _response(self, dialog, response):
        if response == gtk.RESPONSE_OK:
            dialog = filechooser.StandAloneFileChooserDialog(
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
        elif response == gtk.RESPONSE_HELP: # Actually "Import"
            dialog = filechooser.StandAloneFileChooserDialog()
            dialog.run()
            paths = dialog.get_paths()
            dialog.destroy()
            for path in paths:
                if filehandler.is_image_file(path):
                    self._image_area.add_extra_image(path)
                elif os.path.isfile(path):
                    self._other_area.add_extra_file(path)
        else:
            _close_dialog()
            self.kill = True


class _ImageArea(gtk.ScrolledWindow):
    
    """The area used for displaying and handling image files."""
    
    def __init__(self, edit_dialog):
        gtk.ScrolledWindow.__init__(self)
        self._edit_dialog = edit_dialog
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        
        # The ListStore layout is (thumbnail, basename, full path).
        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        self._iconview = gtk.IconView(self._liststore)
        self._iconview.set_pixbuf_column(0)
        self._iconview.set_tooltip_column(1)
        self._iconview.set_reorderable(True)
        self._iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self._iconview.connect('button_press_event', self._button_press)
        self._iconview.connect('key_press_event', self._key_press)
        self._iconview.connect_after('drag_begin', self._drag_begin)
        self.add(self._iconview)

        self._ui_manager = gtk.UIManager()
        ui_description = """
        <ui>
            <popup name="Popup">
                <menuitem action="remove" />
            </popup>
        </ui>
        """
        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = gtk.ActionGroup('comix-edit-archive-image-area')
        actiongroup.add_actions([
            ('remove', gtk.STOCK_REMOVE, _('Remove from archive'), None, None,
                self._remove_pages)])
        self._ui_manager.insert_action_group(actiongroup, 0)

    def fetch_images(self):
        """Load all the images in the archive or directory."""
        for page in xrange(1,
          self._edit_dialog.file_handler.get_number_of_pages() + 1):
            thumb = self._edit_dialog.file_handler.get_thumbnail(
                page, 67, 100, create=False)
            thumb = image.add_border(thumb, 1, 0x555555FF)
            path = self._edit_dialog.file_handler.get_path_to_page(page)
            self._liststore.append([thumb,
                encoding.to_unicode(os.path.basename(path)), path])
            if page % 10 == 0:
                while gtk.events_pending():
                    gtk.main_iteration(False)
                if self._edit_dialog.kill:
                    return

    def add_extra_image(self, path):
        """Add an imported image (at <path>) to the end of the image list."""
        thumb = thumbnail.get_thumbnail(path, create=False)
        if thumb is None:
            thumb = self.render_icon(gtk.STOCK_MISSING_IMAGE,
                gtk.ICON_SIZE_DIALOG)
        thumb = image.fit_in_rectangle(thumb, 67, 100)
        thumb = image.add_border(thumb, 1, 0x555555FF)
        self._liststore.append([thumb, os.path.basename(path), path])

    def get_file_listing(self):
        """Return a list with the full paths to all the images, in order."""
        file_list = []
        for row in self._liststore:
            file_list.append(row[2])
        return file_list

    def _remove_pages(self, *args):
        """Remove the currently selected pages from the list."""
        paths = self._iconview.get_selected_items()
        for path in paths:
            iterator = self._liststore.get_iter(path)
            self._liststore.remove(iterator)
    
    def _button_press(self, iconview, event):
        """Handle mouse button presses on the thumbnail area."""
        path = iconview.get_path_at_pos(int(event.x), int(event.y))
        if path is None:
            return
        if event.button == 3:
            if not iconview.path_is_selected(path):
                iconview.unselect_all()
                iconview.select_path(path)
            self._ui_manager.get_widget('/Popup').popup(None, None, None,
                event.button, event.time)

    def _key_press(self, iconview, event):
        """Handle key presses on the thumbnail area."""
        if event.keyval == gtk.keysyms.Delete:
            self._remove_pages()

    def _drag_begin(self, iconview, context):
        """We hook up on drag_begin events so that we can set the hotspot
        for the cursor at the top left corner of the thumbnail (so that we
        might actually see where we are dropping!).
        """
        path = iconview.get_cursor()[0]
        pixmap = iconview.create_drag_icon(path)
        # context.set_icon_pixmap() seems to cause crashes, so we do a
        # quick and dirty conversion to pixbuf.
        pointer = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
            *pixmap.get_size())
        pointer = pointer.get_from_drawable(pixmap, iconview.get_colormap(),
            0, 0, 0, 0, *pixmap.get_size())
        context.set_icon_pixbuf(pointer, -5, -5)


class _OtherArea(gtk.VBox):
    
    """The area used for displaying and handling non-image files."""
    
    def __init__(self, edit_dialog):
        gtk.VBox.__init__(self)
        self._edit_dialog = edit_dialog

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.pack_start(scrolled)
        info = gtk.Label(_('Please note that the only files that are automatically added to this list are those files in archives that Comix recognizes as comments.'))
        info.set_alignment(0.5, 0.5)
        info.set_line_wrap(True)
        self.pack_start(info, False, False, 10)
        
        # The ListStore layout is (basename, size, full path).
        self._liststore = gtk.ListStore(str, str, str)
        self._treeview = gtk.TreeView(self._liststore)
        self._treeview.set_rules_hint(True)
        self._treeview.connect('button_press_event', self._button_press)
        self._treeview.connect('key_press_event', self._key_press)
        cellrenderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('Name'), cellrenderer, text=0)
        column.set_expand(True)
        self._treeview.append_column(column)
        column = gtk.TreeViewColumn(_('Size'), cellrenderer, text=1)
        self._treeview.append_column(column)
        scrolled.add(self._treeview)

        self._ui_manager = gtk.UIManager()
        ui_description = """
        <ui>
            <popup name="Popup">
                <menuitem action="remove" />
            </popup>
        </ui>
        """
        self._ui_manager.add_ui_from_string(ui_description)
        actiongroup = gtk.ActionGroup('comix-edit-archive-other-area')
        actiongroup.add_actions([
            ('remove', gtk.STOCK_REMOVE, _('Remove from archive'), None, None,
                self._remove_file)])
        self._ui_manager.insert_action_group(actiongroup, 0)
    
    def fetch_comments(self):
        """Load all comments in the archive."""
        for num in xrange(1,
          self._edit_dialog.file_handler.get_number_of_comments() + 1):
            path = self._edit_dialog.file_handler.get_comment_name(num)
            size = '%.1f KiB' % (os.stat(path).st_size / 1024.0)
            self._liststore.append([os.path.basename(path), size, path])

    def add_extra_file(self, path):
        """Add an extra imported file (at <path>) to the list."""
        size = '%.1f KiB' % (os.stat(path).st_size / 1024.0)
        self._liststore.append([os.path.basename(path), size, path])

    def get_file_listing(self):
        """Return a list with the full paths to all the files, in order."""
        file_list = []
        for row in self._liststore:
            file_list.append(row[2])
        return file_list

    def _remove_file(self, *args):
        """Remove the currently selected file from the list."""
        iterator = self._treeview.get_selection().get_selected()[1]
        if iterator is not None:
            self._liststore.remove(iterator)

    def _button_press(self, treeview, event):
        """Handle mouse button presses on the area."""
        path = treeview.get_path_at_pos(int(event.x), int(event.y))
        if path is None:
            return
        path = path[0]
        if event.button == 3:
            self._ui_manager.get_widget('/Popup').popup(None, None, None,
                event.button, event.time)

    def _key_press(self, iconview, event):
        """Handle key presses on the area."""
        if event.keyval == gtk.keysyms.Delete:
            self._remove_file()


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

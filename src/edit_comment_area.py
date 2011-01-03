"""edit_comment_area.py - The area in the editing window that displays comments."""

import os
import gtk

class _CommentArea(gtk.VBox):
    
    """The area used for displaying and handling non-image files."""
    
    def __init__(self, edit_dialog):
        gtk.VBox.__init__(self)
        self._edit_dialog = edit_dialog

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.pack_start(scrolled)
        
        info = gtk.Label(_('Please note that the only files that are automatically added to this list are those files in archives that MComix recognizes as comments.'))
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
        actiongroup = gtk.ActionGroup('mcomix-edit-archive-comment-area')
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

# vim: expandtab:sw=4:ts=4

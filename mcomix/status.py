"""status.py - Statusbar for main window."""

import gtk
import gobject

import i18n
import constants
from preferences import prefs

class Statusbar(gtk.EventBox):

    def __init__(self):
        gtk.EventBox.__init__(self)

        self._loading = True

        self.cellview = gtk.CellView()
        # Status text, page number, file number, resolution, path, filename
        self.model = gtk.ListStore(*([ gobject.TYPE_STRING ] * 6))
        self.cellview.set_model(self.model)
        self.add(self.cellview)

        # Set up renderers for the statusbar boxes.
        for i in range(6):
            cell = gtk.CellRendererText()
            cell.set_property("xpad", 20)

            self.cellview.pack_start(cell, False)
            self.cellview.add_attribute(cell, "text", i)

        # Create popup menu for enabling/disabling status boxes.
        self.ui_manager = gtk.UIManager()
        ui_description = """
        <ui>
            <popup name="Statusbar">
                <menuitem action="pagenumber" />
                <menuitem action="filenumber" />
                <menuitem action="resolution" />
                <menuitem action="rootpath" />
                <menuitem action="filename" />
            </popup>
        </ui>
        """
        self.ui_manager.add_ui_from_string(ui_description)

        actiongroup = gtk.ActionGroup('mcomix-statusbar')
        actiongroup.add_toggle_actions([
            ('pagenumber', None, _('Show page numbers'), None, None,
                self.toggle_status_visibility),
            ('filenumber', None, _('Show file numbers'), None, None,
                self.toggle_status_visibility),
            ('resolution', None, _('Show resolution'), None, None,
                self.toggle_status_visibility),
            ('rootpath', None, _('Show path'), None, None,
                self.toggle_status_visibility),
            ('filename', None, _('Show filename'), None, None,
                self.toggle_status_visibility)])
        self.ui_manager.insert_action_group(actiongroup, 0)

        # Hook mouse release event
        self.connect('button-release-event', self._button_released)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK|gtk.gdk.BUTTON_RELEASE_MASK)

        # Default status information
        self._page_info = ''
        self._file_info = ''
        self._resolution = ''
        self._root = ''
        self._filename = ''
        self.update()

        self._loading = False

    def set_message(self, message):
        """Set a specific message (such as an error message) on the statusbar,
        replacing whatever was there earlier.
        """
        self.model.clear()
        self.model.append((message, '', '', '', '', ''))
        self.cellview.set_displayed_row(0)

        # Hide all cells so that only the message is shown.
        self.cellview.get_cells()[0].set_property('visible', True)
        for cell in self.cellview.get_cells()[1:]:
            cell.set_property('visible', False)

    def set_page_number(self, page, total, double_page=False):
        """Update the page number."""
        if double_page:
            self._page_info = '%d,%d / %d' % (page, page + 1, total)
        else:
            self._page_info = '%d / %d' % (page, total)

    def set_file_number(self, fileno, total):
        """Updates the file number (i.e. number of current file/total
        files loaded)."""
        if total > 0:
            self._file_info = '(%d / %d)' % (fileno, total)
        else:
            self._file_info = ''

    def set_resolution(self, left_dimensions, right_dimensions=None):
        """Update the resolution data.

        Takes one or two tuples, (x, y, scale), describing the original
        resolution of an image as well as the currently displayed scale
        in percent.
        """
        self._resolution = '%dx%d (%.1f%%)' % left_dimensions
        if right_dimensions is not None:
            self._resolution += ', %dx%d (%.1f%%)' % right_dimensions

    def set_root(self, root):
        """Set the name of the root (directory or archive)."""
        self._root = i18n.to_unicode(root)

    def set_filename(self, filename):
        """Update the filename."""
        self._filename = i18n.to_unicode(filename)

    def update(self):
        """Set the statusbar to display the current state."""

        self.model.clear()
        self.model.append(('', self._page_info, self._file_info,
            self._resolution, self._root, self._filename))
        self.cellview.set_displayed_row(0)

        self._update_visibility()

    def toggle_status_visibility(self, action, *args):
        """ Called when status entries visibility is to be changed. """

        # Ignore events as long as control is still loading.
        if self._loading:
            return

        actionname = action.get_name()
        if actionname == 'pagenumber':
            bit = constants.STATUS_PAGE
        elif actionname == 'resolution':
            bit = constants.STATUS_RESOLUTION
        elif actionname == 'rootpath':
            bit = constants.STATUS_PATH
        elif actionname == 'filename':
            bit = constants.STATUS_FILENAME
        elif actionname == 'filenumber':
            bit = constants.STATUS_FILENUMBER

        if action.get_active():
            prefs['statusbar fields'] |= bit
        else:
            prefs['statusbar fields'] &= ~bit

        self._update_visibility()

        # Redraw widget to prevent strange overlapping texts. queue_draw()
        # does NOT fix all issues, for some reason.
        self.hide_all()
        self.show_all()

    def _button_released(self, widget, event, *args):
        """ Triggered when a mouse button is released to open the context
        menu. """
        if event.button == 3:
            self.ui_manager.get_widget('/Statusbar').popup(None, None, None,
                event.button, event.time)

    def _update_visibility(self):
        """ Updates the cells' visibility based on user preferences.
        The status text cell (the first one) is always hidden by this method. """

        status, page, fileno, resolution, path, filename = self.cellview.get_cells()

        page_visible = prefs['statusbar fields'] & constants.STATUS_PAGE
        fileno_visible = prefs['statusbar fields'] & constants.STATUS_FILENUMBER
        resolution_visible = prefs['statusbar fields'] & constants.STATUS_RESOLUTION
        path_visible = prefs['statusbar fields'] & constants.STATUS_PATH
        filename_visible = prefs['statusbar fields'] & constants.STATUS_FILENAME

        status.set_property('visible', False)
        page.set_property('visible', page_visible)
        fileno.set_property('visible', fileno_visible)
        resolution.set_property('visible', resolution_visible)
        path.set_property('visible', path_visible)
        filename.set_property('visible', filename_visible)

        for name, visible in (('pagenumber', page_visible),
                ('filenumber', fileno_visible),
                ('resolution', resolution_visible),
                ('rootpath', path_visible),
                ('filename', filename_visible)):
            action = self.ui_manager.get_action('/Statusbar/' + name)
            action.set_active(visible)

# vim: expandtab:sw=4:ts=4

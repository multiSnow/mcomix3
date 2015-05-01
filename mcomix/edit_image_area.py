"""edit_image_area.py - The area of the editing archive window that displays images."""

import os
import gtk

from mcomix import constants
from mcomix import i18n
from mcomix import thumbnail_tools
from mcomix import thumbnail_view
from mcomix.preferences import prefs

class _ImageArea(gtk.ScrolledWindow):

    """The area used for displaying and handling image files."""

    def __init__(self, edit_dialog, window):
        super(_ImageArea, self).__init__()

        self._window = window
        self._edit_dialog = edit_dialog
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        # The ListStore layout is (thumbnail, basename, full path, pagenumber, thumbnail status).
        # Basename is used as image tooltip.
        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str, int, bool)
        self._iconview = thumbnail_view.ThumbnailIconView(self._liststore)
        self._iconview.pixbuf_column = 0
        self._iconview.status_column = 4
        # This method isn't necessary, as generate_thumbnail doesn't need the path
        self._iconview.get_file_path_from_model = lambda *args: None
        self._iconview.generate_thumbnail = self._generate_thumbnail
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

        actiongroup = gtk.ActionGroup('mcomix-edit-archive-image-area')
        actiongroup.add_actions([
            ('remove', gtk.STOCK_REMOVE, _('Remove from archive'), None, None,
                self._remove_pages)])
        self._ui_manager.insert_action_group(actiongroup, 0)

    def fetch_images(self):
        """Load all the images in the archive or directory."""

        pixbuf = gtk.gdk.Pixbuf(colorspace=gtk.gdk.COLORSPACE_RGB,
                has_alpha=True,
                bits_per_sample=8,
                width=prefs['thumbnail size'], height=prefs['thumbnail size'])

        # Make the pixbuf transparent.
        pixbuf.fill(0)

        for page in xrange(1, self._window.imagehandler.get_number_of_pages() + 1):
            path = self._window.imagehandler.get_path_to_page(page)
            encoded_path = i18n.to_unicode(os.path.basename(path))
            encoded_path = encoded_path.replace('&', '&amp;')

            self._liststore.append([pixbuf, encoded_path, path, page, False])

    def _generate_thumbnail(self, file_path, path):
        """ Creates the thumbnail for the passed model path. """

        if path is None:
            return constants.MISSING_IMAGE_ICON

        model = self._liststore
        iter = model.get_iter(path)
        page = model.get_value(iter, 3)
        pixbuf = self._window.imagehandler.get_thumbnail(page) or \
            constants.MISSING_IMAGE_ICON

        return pixbuf

    def add_extra_image(self, path):
        """Add an imported image (at <path>) to the end of the image list."""
        thumbnailer = thumbnail_tools.Thumbnailer()
        thumbnailer.set_archive_support(False)
        thumbnailer.set_store_on_disk(False)
        thumb = thumbnailer.thumbnail(path)

        if thumb is None:
            thumb = self.render_icon(gtk.STOCK_MISSING_IMAGE,
                gtk.ICON_SIZE_DIALOG)

        self._liststore.append([thumb, os.path.basename(path), path, -1, True])

    def get_file_listing(self):
        """Return a list with the full paths to all the images, in order."""
        file_list = []

        for row in self._liststore:
            file_list.append(row[2].decode('utf-8'))

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

    def cleanup(self):
        self._iconview.stop_update()

# vim: expandtab:sw=4:ts=4

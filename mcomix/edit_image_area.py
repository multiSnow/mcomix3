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

        # The ListStore layout is (thumbnail, basename, full path, thumbnail status).
        # Basename is used as image tooltip.
        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str, bool)
        self._iconview = thumbnail_view.ThumbnailIconView(
            self._liststore,
            2, # UID
            0, # pixbuf
            3, # status
        )
        self._iconview.generate_thumbnail = self._generate_thumbnail
        self._iconview.set_tooltip_column(1)
        self._iconview.set_reorderable(True)
        self._iconview.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self._iconview.connect('button_press_event', self._button_press)
        self._iconview.connect('key_press_event', self._key_press)
        self._iconview.connect_after('drag_begin', self._drag_begin)
        self.add(self._iconview)

        self._thumbnail_size = 128
        self._thumbnailer = thumbnail_tools.Thumbnailer()
        self._thumbnailer.set_archive_support(False)
        self._thumbnailer.set_store_on_disk(False)
        self._thumbnailer.set_size(self._thumbnail_size, self._thumbnail_size)

        self._filler = gtk.gdk.Pixbuf(colorspace=gtk.gdk.COLORSPACE_RGB,
                                      has_alpha=True, bits_per_sample=8,
                                      width=self._thumbnail_size,
                                      height=self._thumbnail_size)
        # Make the pixbuf transparent.
        self._filler.fill(0)

        self._window.imagehandler.page_available += self._on_page_available

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
        for page in xrange(1, self._window.imagehandler.get_number_of_pages() + 1):
            path = self._window.imagehandler.get_path_to_page(page)
            encoded_path = i18n.to_unicode(os.path.basename(path))
            encoded_path = encoded_path.replace('&', '&amp;')
            self._liststore.append([self._filler, encoded_path, path, False])

    def _generate_thumbnail(self, uid):
        assert isinstance(uid, str)
        path = uid
        try:
            if not self._window.filehandler.file_is_available(path):
                return None
        except KeyError:
            # Not a page from the current archive, ignore.
            pass
        pixbuf = self._thumbnailer.thumbnail(path)
        if pixbuf is None:
            pixbuf = constants.MISSING_IMAGE_ICON
        return pixbuf

    def add_extra_image(self, path):
        """Add an imported image (at <path>) to the end of the image list."""
        self._liststore.append([self._filler, os.path.basename(path), path, False])

    def get_file_listing(self):
        """Return a list with the full paths to all the images, in order."""
        return [row[2] for row in self._liststore]

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

    def _on_page_available(self, page):
        """ Called whenever a new page is ready for display. """
        self._iconview.draw_thumbnails_on_screen()

# vim: expandtab:sw=4:ts=4

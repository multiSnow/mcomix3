"""lens.py - Magnifying glass."""

import math

import gtk

import cursor
from preferences import prefs
import image


class MagnifyingGlass:

    """The MagnifyingGlass creates cursors from the raw pixbufs containing
    the unscaled data for the currently displayed images. It does this by
    looking at the cursor position and calculating what image data to put
    in the "lens" cursor.

    Note: The mapping is highly dependent on the exact layout of the main
    window images, thus this module isn't really independent from the main
    module as it uses implementation details not in the interface.
    """

    def __init__(self, window):
        self._window = window

    def set_lens_cursor(self, x, y):
        """Calculate what image data to put in the lens and update the cursor
        with it; <x> and <y> are the positions of the cursor within the
        main window layout area.
        """
        if not self._window.file_handler.file_loaded:
            return
        pixbuf = self._get_lens_pixbuf(x, y)
        cursor = gtk.gdk.Cursor(gtk.gdk.display_get_default(), pixbuf,
            prefs['lens size'] // 2, prefs['lens size'] // 2)
        self._window.cursor_handler.set_cursor_type(cursor)

    def toggle(self, action):
        """Toggle on or off the lens depending on the state of <action>."""
        if action.get_active():
            x, y = self._window.get_layout_pointer_position()
            self.set_lens_cursor(x, y)
        else:
            self._window.cursor_handler.set_cursor_type(cursor.NORMAL)

    def _get_lens_pixbuf(self, x, y):
        """Get a pixbuf containing the appropiate image data for the lens
        where <x> and <y> are the positions of the cursor.
        """
        canvas = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
            prefs['lens size'], prefs['lens size'])
        canvas.fill(0x000000bb)
        if self._window.displayed_double():
            if self._window.is_manga_mode:
                r_source_pixbuf, l_source_pixbuf = \
                    self._window.file_handler.get_pixbufs()
            else:
                l_source_pixbuf, r_source_pixbuf = \
                    self._window.file_handler.get_pixbufs()
            l_image_size = self._window.left_image.size_request()
            r_image_size = self._window.right_image.size_request()
            self._add_subpixbuf(canvas, x, y, l_image_size, l_source_pixbuf,
                r_image_size[0], left=True)
            self._add_subpixbuf(canvas, x, y, r_image_size, r_source_pixbuf,
                l_image_size[0], left=False)
        else:
            source_pixbuf = self._window.file_handler.get_pixbufs()
            image_size = self._window.left_image.size_request()
            self._add_subpixbuf(canvas, x, y, image_size, source_pixbuf)
        return image.add_border(canvas, 1)

    def _add_subpixbuf(self, canvas, x, y, image_size, source_pixbuf,
        other_image_width=0, left=True):
        """Copy a subpixbuf from <source_pixbuf> to <canvas> as it should
        be in the lens if the coordinates <x>, <y> are the mouse pointer
        position on the main window layout area.

        The displayed image (scaled from the <source_pixbuf>) must have
        size <image_size>.

        If <other_image_width> is given, it is the width of the "other" image
        in double page mode.

        The image we are getting the coordinates for is the left one unless
        <left> is False.
        """
        area_x, area_y = self._window.get_visible_area_size()
        if left:
            padding_x = max(0,
                (area_x - other_image_width - image_size[0]) // 2)
        else:
            padding_x = \
                (max(0, (area_x - other_image_width - image_size[0]) // 2) +
                other_image_width + 2)
        padding_y = max(0, (area_y - image_size[1]) // 2)
        x -= padding_x
        y -= padding_y
        rotation = prefs['rotation']
        if prefs['auto rotate from exif']:
            rotation += image.get_implied_rotation(source_pixbuf)
            rotation = rotation % 360

        if rotation in [90, 270]:
            scale = float(source_pixbuf.get_height()) / image_size[0]
        else:
            scale = float(source_pixbuf.get_width()) / image_size[0]
        x *= scale
        y *= scale
        source_mag = prefs['lens magnification'] / scale
        width = prefs['lens size'] / source_mag
        height = width
        paste_left = x > width / 2
        paste_top = y > height / 2
        dest_x = max(0, int(math.ceil((width / 2 - x) * source_mag)))
        dest_y = max(0, int(math.ceil((height / 2 - y) * source_mag)))

        if rotation == 90:
            x, y = y, source_pixbuf.get_height() - x
        elif rotation == 180:
            x = source_pixbuf.get_width() - x
            y = source_pixbuf.get_height() - y
        elif rotation == 270:
            x, y = source_pixbuf.get_width() - y, x
        if prefs['horizontal flip']:
            if rotation in (90, 270):
                y = source_pixbuf.get_height() - y
            else:
                x = source_pixbuf.get_width() - x
        if prefs['vertical flip']:
            if rotation in (90, 270):
                x = source_pixbuf.get_width() - x
            else:
                y = source_pixbuf.get_height() - y

        src_x = x - width / 2
        src_y = y - height / 2
        if src_x < 0:
            width += src_x
            src_x = 0
        if src_y < 0:
            height += src_y
            src_y = 0
        width = max(0, min(source_pixbuf.get_width() - src_x, width))
        height = max(0, min(source_pixbuf.get_height() - src_y, height))
        if width < 1 or height < 1:
            return

        subpixbuf = source_pixbuf.subpixbuf(int(src_x), int(src_y),
            int(width), int(height))
        subpixbuf = subpixbuf.scale_simple(
            int(math.ceil(source_mag * subpixbuf.get_width())),
            int(math.ceil(source_mag * subpixbuf.get_height())),
            gtk.gdk.INTERP_TILES)

        if rotation == 90:
            subpixbuf = subpixbuf.rotate_simple(
                gtk.gdk.PIXBUF_ROTATE_CLOCKWISE)
        elif rotation == 180:
            subpixbuf = subpixbuf.rotate_simple(
                gtk.gdk.PIXBUF_ROTATE_UPSIDEDOWN)
        elif rotation == 270:
            subpixbuf = subpixbuf.rotate_simple(
                gtk.gdk.PIXBUF_ROTATE_COUNTERCLOCKWISE)
        if prefs['horizontal flip']:
            subpixbuf = subpixbuf.flip(horizontal=True)
        if prefs['vertical flip']:
            subpixbuf = subpixbuf.flip(horizontal=False)
        if paste_left:
            dest_x = 0
        else:
            dest_x = min(canvas.get_width() - subpixbuf.get_width(), dest_x)
        if paste_top:
            dest_y = 0
        else:
            dest_y = min(canvas.get_height() - subpixbuf.get_height(), dest_y)

        subpixbuf.copy_area(0, 0, subpixbuf.get_width(),
            subpixbuf.get_height(), canvas, dest_x, dest_y)

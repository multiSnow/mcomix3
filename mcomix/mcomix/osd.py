# -*- coding: utf-8 -*-
''' osd.py - Onscreen display showing currently opened file. '''

import textwrap

from gi.repository import Gdk, Gtk, GLib
from gi.repository import Pango, PangoCairo

from mcomix.preferences import prefs


class OnScreenDisplay(object):

    ''' The OSD shows information such as currently opened file, archive and
    page in a black box drawn on the bottom end of the screen.

    The OSD will automatically be erased after TIMEOUT seconds.
    '''

    TIMEOUT = 3

    def __init__(self, window):
        #: MainWindow
        self._window = window
        #: Stores the last rectangle that was used to render the OSD
        self._last_osd_rect = None
        #: Timeout event ID registered while waiting to hide the OSD
        self._timeout_event = None

    def show(self, text):
        ''' Shows the OSD on the lower portion of the image window. '''

        # Determine text to draw
        text = self._wrap_text(text)
        layout = self._window._image_box.create_pango_layout(text)

        # Set up font information
        font = layout.get_context().get_font_description()
        font.set_weight(Pango.Weight.BOLD)
        layout.set_alignment(Pango.Alignment.CENTER)

        # Scale font to fit within the screen size
        max_width, max_height = self._window.get_visible_area_size()
        self._scale_font(font, layout, max_width, max_height)

        # Calculate surrounding box
        layout_width, layout_height = layout.get_pixel_size()
        pos_x = max(int(max_width // 2) - int(layout_width // 2) +
                    int(self._window._hadjust.get_value()), 0)
        pos_y = max(int(max_height) - int(layout_height * 1.1) +
                    int(self._window._vadjust.get_value()), 0)

        rect = (pos_x - 10, pos_y - 20,
                layout_width + 20, layout_height + 20)

        self._draw_osd(layout, rect)

        self._last_osd_rect = rect
        if self._timeout_event:
            GLib.source_remove(self._timeout_event)
        self._timeout_event = GLib.timeout_add_seconds(OnScreenDisplay.TIMEOUT, self.clear)

    def clear(self):
        ''' Removes the OSD. '''
        if self._timeout_event:
            GLib.source_remove(self._timeout_event)
        self._timeout_event = None
        self._clear_osd()
        return 0 # To unregister timer event

    def _wrap_text(self, text, width=70):
        ''' Wraps the text to be C{width} characters at most. '''
        return '\n'.join(textwrap.fill(s, width=width) for s in text.splitlines())

    def _clear_osd(self):
        ''' Clear the last OSD region. '''

        if not self._last_osd_rect:
            return

        window = self._window._main_layout.get_bin_window()
        gdk_rect = Gdk.Rectangle()
        gdk_rect.x, gdk_rect.y, gdk_rect.width, gdk_rect.height = self._last_osd_rect
        window.invalidate_rect(gdk_rect, True)
        window.process_updates(True)
        self._last_osd_rect = None

    def _scale_font(self, font, layout, max_width, max_height):
        ''' Scales the font used by C{layout} until max_width/max_height is reached. '''

        # hard limited from 8 to 60
        SIZE_MIN, SIZE_MAX = 8, min(prefs['osd max font size'], 60)+1
        for font_size in range(SIZE_MIN, SIZE_MAX):
            old_size = font.get_size()
            font.set_size(font_size * Pango.SCALE)
            layout.set_font_description(font)

            if layout.get_pixel_size()[0] > max_width:
                font.set_size(old_size)
                layout.set_font_description(font)
                break

    def _draw_osd(self, layout, rect):
        ''' Draws the text specified in C{layout} into a box at C{rect}. '''

        draw_region = Gdk.Rectangle()
        draw_region.x, draw_region.y, draw_region.width, draw_region.height = rect
        if self._last_osd_rect:
            last_region = Gdk.Rectangle()
            last_region.x, last_region.y, last_region.width, last_region.height = self._last_osd_rect
            draw_region = Gdk.rectangle_union(draw_region, last_region)

        gdk_rect = Gdk.Rectangle()
        gdk_rect.x = draw_region.x
        gdk_rect.y = draw_region.y
        gdk_rect.width = draw_region.width
        gdk_rect.height = draw_region.height
        window = self._window._main_layout.get_bin_window()
        window.begin_paint_rect(gdk_rect)

        self._clear_osd()

        cr = window.cairo_create()
        cr.set_source_rgba(*prefs['osd bg color'])
        cr.rectangle(*rect)
        cr.fill()
        extents = layout.get_extents()[0]
        cr.set_source_rgba(*prefs['osd color'])
        cr.translate(rect[0] + extents.x / Pango.SCALE,
                     rect[1] + extents.y / Pango.SCALE)
        PangoCairo.update_layout(cr, layout)
        PangoCairo.show_layout(cr, layout)

        window.end_paint()

# vim: expandtab:sw=4:ts=4

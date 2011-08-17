"""event.py - Event handling (keyboard, mouse, etc.) for the main window.
"""

import constants
import urllib
import gtk
import gtk.gdk
import portability
from preferences import prefs

class EventHandler:

    def __init__(self, window):
        self._window = window

        self._last_pointer_pos_x = 0
        self._last_pointer_pos_y = 0
        self._last_lens_pos_x = 0
        self._last_lens_pos_y = 0
        self._pressed_pointer_pos_x = 0
        self._pressed_pointer_pos_y = 0

        self._extra_scroll_events = 0 # For scrolling "off the page".

    def resize_event(self, widget, event):
        """Handle events from resizing and moving the main window."""
        if not self._window.is_fullscreen:
            prefs['window x'], prefs['window y'] = self._window.get_position()

        if (event.width != self._window.width or
            event.height != self._window.height):

            if not self._window.is_fullscreen:
                prefs['window width'] = event.width
                prefs['window height'] = event.height

            self._window.width = event.width
            self._window.height = event.height
            self._window.draw_image()

    def key_press_event(self, widget, event, *args):
        """Handle key press events on the main window."""

        # ----------------------------------------------------------------
        # Some navigation keys that work as well as the accelerators in
        # ui.py.
        # ----------------------------------------------------------------
        if event.keyval in (gtk.keysyms.KP_Page_Up, gtk.keysyms.BackSpace) or \
           (event.keyval == gtk.keysyms.Left and event.state & gtk.gdk.MOD1_MASK):
            self._window.previous_page()

        elif event.keyval == gtk.keysyms.KP_Page_Down or \
             (event.keyval == gtk.keysyms.Right and event.state & gtk.gdk.MOD1_MASK):
            self._window.next_page()

        # ----------------------------------------------------------------
        # Numpad (without numlock) aligns the image depending on the key.
        # ----------------------------------------------------------------
        elif event.keyval == gtk.keysyms.KP_1:
            self._window.scroll_to_fixed(horiz='left', vert='bottom')

        elif event.keyval == gtk.keysyms.KP_2:
            self._window.scroll_to_fixed(horiz='middle', vert='bottom')

        elif event.keyval == gtk.keysyms.KP_3:
            self._window.scroll_to_fixed(horiz='right', vert='bottom')

        elif event.keyval == gtk.keysyms.KP_4:
            self._window.scroll_to_fixed(horiz='left', vert='middle')

        elif event.keyval == gtk.keysyms.KP_5:
            self._window.scroll_to_fixed(horiz='middle', vert='middle')

        elif event.keyval == gtk.keysyms.KP_6:
            self._window.scroll_to_fixed(horiz='right', vert='middle')

        elif event.keyval == gtk.keysyms.KP_7:
            self._window.scroll_to_fixed(horiz='left', vert='top')

        elif event.keyval == gtk.keysyms.KP_8:
            self._window.scroll_to_fixed(horiz='middle', vert='top')

        elif event.keyval == gtk.keysyms.KP_9:
            self._window.scroll_to_fixed(horiz='right', vert='top')

        # ----------------------------------------------------------------
        # Enter/exit fullscreen. 'f' is also a valid key, defined as an
        # accelerator elsewhere.
        # ----------------------------------------------------------------
        elif event.keyval == gtk.keysyms.Escape:
            self._window.actiongroup.get_action('fullscreen').set_active(False)

        elif event.keyval == gtk.keysyms.F11:
            self._window.actiongroup.get_action('fullscreen').activate()

        # ----------------------------------------------------------------
        # Zooming commands for manual zoom mode. These keys complement
        # others (with the same action) defined as accelerators.
        # ----------------------------------------------------------------
        elif event.keyval in (gtk.keysyms.plus, gtk.keysyms.equal):
            self._window.actiongroup.get_action('zoom_in').activate()

        elif event.keyval == gtk.keysyms.minus:
            self._window.actiongroup.get_action('zoom_out').activate()

        elif (event.keyval in (gtk.keysyms._0, gtk.keysyms.KP_0) and
          'GDK_CONTROL_MASK' in event.state.value_names):
            self._window.actiongroup.get_action('zoom_original').activate()

        # ----------------------------------------------------------------
        # Arrow keys scroll the image, except in best fit mode where
        # they flip pages instead.
        # ----------------------------------------------------------------
        elif event.keyval in (gtk.keysyms.Down, gtk.keysyms.KP_Down):

            if not prefs['zoom mode'] == constants.ZOOM_MODE_BEST:
                self._scroll_with_flipping(0, prefs['number of pixels to scroll per key event'])
            else:
                self._window.next_page()

        elif event.keyval in (gtk.keysyms.Up, gtk.keysyms.KP_Up):

            if not prefs['zoom mode'] == constants.ZOOM_MODE_BEST:
                self._scroll_with_flipping(0, -prefs['number of pixels to scroll per key event'])
            else:
                self._window.previous_page()

        elif event.keyval in (gtk.keysyms.Right, gtk.keysyms.KP_Right):

            if not prefs['zoom mode'] == constants.ZOOM_MODE_BEST:
                self._scroll_with_flipping(prefs['number of pixels to scroll per key event'], 0)
            else:
                self._window.next_page()

        elif event.keyval in (gtk.keysyms.Left, gtk.keysyms.KP_Left):

            if not prefs['zoom mode'] == constants.ZOOM_MODE_BEST:
                self._scroll_with_flipping(-prefs['number of pixels to scroll per key event'], 0)
            else:
                self._window.previous_page()

        # ----------------------------------------------------------------
        # Space key scrolls down a percentage of the window height or the
        # image height at a time. When at the bottom it flips to the next
        # page.
        #
        # It also has a "smart scrolling mode" in which we try to follow
        # the flow of the comic.
        #
        # If Shift is pressed we should backtrack instead.
        # ----------------------------------------------------------------
        elif event.keyval in [gtk.keysyms.space, gtk.keysyms.KP_Home,
          gtk.keysyms.KP_End]:

            x_step, y_step = self._window.get_visible_area_size()
            x_step = int(x_step * 0.9)
            y_step = int(y_step * 0.9)

            if self._window.is_manga_mode:
                x_step *= -1

            if ('GDK_SHIFT_MASK' in event.state.value_names or
              event.keyval == gtk.keysyms.KP_Home):

                if prefs['smart space scroll']:

                    if self._window.displayed_double():

                        if self._window.is_on_first_page():

                            if not self._window.scroll(-x_step, 0, 'first'):

                                if not self._window.scroll(0, -y_step):
                                    self._window.previous_page()
                                else:
                                    self._window.scroll_to_fixed(
                                        horiz='endfirst')

                        else:
                            if not self._window.scroll(-x_step, 0, 'second'):

                                if not self._window.scroll(0, -y_step):

                                    if not self._window.scroll_to_fixed(
                                      horiz='endfirst'):
                                        self._window.previous_page()

                                    else:
                                        self._window.scroll_to_fixed(
                                            vert='bottom')

                                else:
                                    self._window.scroll_to_fixed(
                                        horiz='endsecond')
                    else:
                        # When a double page is displayed, scroll left/right,
                        # then top/bottom
                        if not prefs['invert smart scroll']:
                            if not self._window.scroll(-x_step, 0):

                                if not self._window.scroll(0, -y_step):
                                    self._window.previous_page()
                                else:
                                    self._window.scroll_to_fixed(horiz='endfirst')
                        # Scroll top/bottom, then left/right
                        else:
                            if not self._window.scroll(0, -y_step):
                                if not self._window.scroll(-x_step, 0):
                                    self._window.previous_page()
                                else:
                                    self._window.scroll_to_fixed(
                                        horiz='startfirst', vert='bottom')
                else:

                    if (prefs['zoom mode'] == constants.ZOOM_MODE_BEST or
                      not self._window.scroll(0, -y_step)):
                        self._window.previous_page()
            else:

                if prefs['smart space scroll']:

                    if self._window.displayed_double():

                        if self._window.is_on_first_page():

                            if not self._window.scroll(x_step, 0, 'first'):

                                if not self._window.scroll(0, y_step):

                                    if not self._window.scroll_to_fixed(
                                      horiz='startsecond'):
                                        self._window.next_page()
                                    else:
                                        self._window.scroll_to_fixed(
                                                vert='top')

                                else:

                                    self._window.scroll_to_fixed(
                                        horiz='startfirst')
                        else:

                            if not self._window.scroll(x_step, 0, 'second'):

                                if not self._window.scroll(0, y_step):
                                    self._window.next_page()
                                else:
                                    self._window.scroll_to_fixed(
                                        horiz='startsecond')
                    else:
                        # When a double page is displayed, scroll left/right,
                        # then top/bottom
                        if not prefs['invert smart scroll']:
                            if not self._window.scroll(x_step, 0):

                                if not self._window.scroll(0, y_step):
                                    self._window.next_page()
                                else:
                                    self._window.scroll_to_fixed(
                                        horiz='startfirst')
                        # Scroll top/bottom, then left/right
                        else:
                            if not self._window.scroll(0, y_step):
                                if not self._window.scroll(x_step, 0):
                                    self._window.next_page()
                                else:
                                    self._window.scroll_to_fixed(
                                        horiz='startsecond', vert='top')

                else:

                    if (prefs['zoom mode'] == constants.ZOOM_MODE_BEST or
                      not self._window.scroll(0, y_step)):
                        self._window.next_page()

        # ---------------------------------------------------------------
        # OSD display
        # ---------------------------------------------------------------
        elif event.keyval == gtk.keysyms.Tab:
            self._window.show_info_panel()

        # ---------------------------------------------------------------
        # Register CTRL for scrolling only one page instead of two
        # pages in double page mode
        # ---------------------------------------------------------------
        if event.keyval in (gtk.keysyms.Control_L, gtk.keysyms.Control_R):
            self._window.imagehandler.force_single_step = True

        # ----------------------------------------------------------------
        # We kill the signals here for the Up, Down, Space and Enter keys,
        # or they will start fiddling with the thumbnail selector (bad).
        # ----------------------------------------------------------------
        if (event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down,
          gtk.keysyms.space, gtk.keysyms.KP_Enter, gtk.keysyms.KP_Up,
          gtk.keysyms.KP_Down, gtk.keysyms.KP_Home, gtk.keysyms.KP_End,
          gtk.keysyms.KP_Page_Up, gtk.keysyms.KP_Page_Down) or
          (event.keyval == gtk.keysyms.Return and not
          'GDK_MOD1_MASK' in event.state.value_names)):

            self._window.emit_stop_by_name('key_press_event')

            return True

    def key_release_event(self, widget, event, *args):
        """ Handle release of keys for the main window. """

        # ---------------------------------------------------------------
        # Unregister CTRL for scrolling only one page in double page mode
        # ---------------------------------------------------------------
        if event.keyval in (gtk.keysyms.Control_L, gtk.keysyms.Control_R):
            self._window.imagehandler.force_single_step = False

    def scroll_wheel_event(self, widget, event, *args):
        """Handle scroll wheel events on the main layout area. The scroll
        wheel flips pages in best fit mode and scrolls the scrollbars
        otherwise.
        """
        if 'GDK_BUTTON2_MASK' in event.state.value_names:
            return

        if event.direction == gtk.gdk.SCROLL_UP:

            if prefs['zoom mode'] == constants.ZOOM_MODE_BEST:
                self._window.previous_page()

            elif prefs['zoom mode'] == constants.ZOOM_MODE_HEIGHT:

                if self._window.is_manga_mode:
                    self._scroll_with_flipping(prefs['number of pixels to scroll per mouse wheel event'], 0)
                else:
                    self._scroll_with_flipping(-prefs['number of pixels to scroll per mouse wheel event'], 0)

            else:
                self._scroll_with_flipping(0, -prefs['number of pixels to scroll per mouse wheel event'])

        elif event.direction == gtk.gdk.SCROLL_DOWN:

            if prefs['zoom mode'] == constants.ZOOM_MODE_BEST:
                self._window.next_page()

            elif prefs['zoom mode'] == constants.ZOOM_MODE_HEIGHT:

                if self._window.is_manga_mode:
                    self._scroll_with_flipping(-prefs['number of pixels to scroll per mouse wheel event'], 0)
                else:
                    self._scroll_with_flipping(prefs['number of pixels to scroll per mouse wheel event'], 0)
            else:
                self._scroll_with_flipping(0, prefs['number of pixels to scroll per mouse wheel event'])

        elif event.direction == gtk.gdk.SCROLL_RIGHT:
            self._window.next_page()

        elif event.direction == gtk.gdk.SCROLL_LEFT:
            self._window.previous_page()

    def mouse_press_event(self, widget, event):
        """Handle mouse click events on the main layout area."""

        if event.button == 1:
            self._pressed_pointer_pos_x = event.x_root
            self._pressed_pointer_pos_y = event.y_root
            self._last_pointer_pos_x = event.x_root
            self._last_pointer_pos_y = event.y_root

        elif event.button == 2:
            self._window.actiongroup.get_action('lens').set_active(True)

        elif event.button == 3 and not event.state & gtk.gdk.MOD1_MASK:
            self._window.cursor_handler.set_cursor_type(constants.NORMAL_CURSOR)
            self._window.popup.popup(None, None, None, event.button,
                event.time)

    def mouse_release_event(self, widget, event):
        """Handle mouse button release events on the main layout area."""

        self._window.cursor_handler.set_cursor_type(constants.NORMAL_CURSOR)

        if (event.button == 1):

            if event.x_root == self._pressed_pointer_pos_x and \
                event.y_root == self._pressed_pointer_pos_y and \
                not self._window.was_out_of_focus:
                self._window.next_page()

            else:
                self._window.was_out_of_focus = False

        elif event.button == 2:
            self._window.actiongroup.get_action('lens').set_active(False)

        elif event.button == 3 and event.state & gtk.gdk.MOD1_MASK:
            self._window.previous_page()

    def mouse_move_event(self, widget, event):
        """Handle mouse pointer movement events."""

        if not self._window.is_in_focus:
            self._window.was_out_of_focus = True
        else:
            self._window.was_out_of_focus = False

        event = _get_latest_event_of_same_type(event)

        if 'GDK_BUTTON1_MASK' in event.state.value_names:
            self._window.cursor_handler.set_cursor_type(constants.GRAB_CURSOR)
            self._window.scroll(self._last_pointer_pos_x - event.x_root,
                                self._last_pointer_pos_y - event.y_root)
            self._last_pointer_pos_x = event.x_root
            self._last_pointer_pos_y = event.y_root
            self._drag_timer = event.time

        elif self._window.actiongroup.get_action('lens').get_active():

            # this is set to check if the mouse hasn't moved but the mouse event has fired
            # this attempts to prevent lens re-drawing in the case of a jittery mouse or
            # extremely small mouse movements
            if event.x != self._last_lens_pos_x or event.y != self._last_lens_pos_y:

                self._window.lens.set_lens_cursor(event.x, event.y)

        else:
            self._window.cursor_handler.refresh()

        self._last_lens_pos_x = event.x
        self._last_lens_pos_y = event.y

    def drag_n_drop_event(self, widget, context, x, y, selection, drag_id,
      eventtime):
        """Handle drag-n-drop events on the main layout area."""
        # The drag source is inside MComix itself, so we ignore.

        if (context.get_source_widget() is not None):
            return

        uris = selection.get_uris()

        if not uris:
            return

        # Normalize URIs
        uris = [ portability.normalize_uri(uri) for uri in uris ]
        paths = [ urllib.url2pathname(uri).decode('utf-8') for uri in uris ]

        if len(paths) > 1:
            self._window.filehandler.open_file(paths)
        else:
            self._window.filehandler.open_file(paths[0])

    def _scroll_with_flipping(self, x, y):
        """Handle scrolling with the scroll wheel or the arrow keys, for which
        the pages might be flipped depending on the preferences.  Returns True
        if able to scroll without flipping and False if a new page was flipped
        to.
        """

        if self._window.scroll(x, y) or not prefs['flip with wheel']:
            self._extra_scroll_events = 0

            return True

        if y > 0 or (self._window.is_manga_mode and x < 0) or (
          not self._window.is_manga_mode and x > 0):
            forwards_scroll = True

        else:
            forwards_scroll = False

        if forwards_scroll:
            self._extra_scroll_events = max(1, self._extra_scroll_events + 1)

            if self._extra_scroll_events >= prefs['number of key presses before page turn']:
                self._extra_scroll_events = 0
                self._window.next_page()

                return False

            return True
        else:
            self._extra_scroll_events = min(-1, self._extra_scroll_events - 1)

            if self._extra_scroll_events <= -prefs['number of key presses before page turn']:
                self._extra_scroll_events = 0

                self._window.previous_page()

                return False

            return True

def _get_latest_event_of_same_type(event):
    """Return the latest event in the event queue that is of the same type
    as <event>, or <event> itself if no such events are in the queue. All
    events of that type will be removed from the event queue.
    """
    events = []

    while gtk.gdk.events_pending():
        queued_event = gtk.gdk.event_get()

        if queued_event is not None:

            if queued_event.type == event.type:
                event = queued_event
            else:
                events.append(queued_event)

    for queued_event in events:
        queued_event.put()

    return event


# vim: expandtab:sw=4:ts=4

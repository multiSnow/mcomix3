"""event.py - Event handling (keyboard, mouse, etc.) for the main window.
"""

import urllib
import gtk
import gtk.gdk

from mcomix.preferences import prefs
from mcomix import constants
from mcomix import portability
from mcomix import keybindings
from mcomix import openwith


class EventHandler:

    def __init__(self, window):
        self._window = window

        self._last_pointer_pos_x = 0
        self._last_pointer_pos_y = 0
        self._pressed_pointer_pos_x = 0
        self._pressed_pointer_pos_y = 0

        #: For scrolling "off the page".
        self._extra_scroll_events = 0
        #: If True, increment _extra_scroll_events before switchting pages
        self._scroll_protection = False
        #: If True, the last smart scroll action was in direction 1 (usually
        #: horizontal). False means that direction 2 was scrolled (vertically)
        self._last_scroll_was_direction_1 = False

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

    def register_key_events(self):
        """ Registers keyboard events and their default binings, and hooks
        them up with their respective callback functions. """

        manager = keybindings.keybinding_manager(self._window)

        # Navigation keys
        manager.register('previous_page',
            ['Page_Up', 'KP_Page_Up', 'BackSpace'],
            self._window.previous_page)
        manager.register('next_page',
            ['Page_Down', 'KP_Page_Down'],
            self._window.next_page)
        manager.register('previous_page_dynamic',
            ['<Mod1>Left'],
            self._left_right_page_progress, kwargs={'left': True})
        manager.register('next_page_dynamic',
            ['<Mod1>Right'],
            self._left_right_page_progress, kwargs={'left': False})

        manager.register('previous_page_ff',
            ['<Shift>Page_Up', '<Shift>KP_Page_Up', '<Shift>BackSpace', '<Shift><Mod1>Left'],
            self._window.previous_page_fast_forward)
        manager.register('next_page_ff',
            ['<Shift>Page_Down', '<Shift>KP_Page_Down', '<Shift><Mod1>Right'],
            self._window.next_page_fast_forward)


        manager.register('first_page',
            ['Home'],
            self._window.first_page)
        manager.register('last_page',
            ['End'],
            self._window.last_page)
        manager.register('go_to',
            ['G'],
            self._window.page_select)

        # Numpad (without numlock) aligns the image depending on the key.
        manager.register('scroll_left_bottom',
            ['KP_1'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'left', 'vert': 'bottom'})
        manager.register('scroll_middle_bottom',
            ['KP_2'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'middle', 'vert': 'bottom'})
        manager.register('scroll_right_bottom',
            ['KP_3'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'right', 'vert': 'bottom'})

        manager.register('scroll_left_middle',
            ['KP_4'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'left', 'vert': 'middle'})
        manager.register('scroll_middle',
            ['KP_5'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'middle', 'vert': 'middle'})
        manager.register('scroll_right_middle',
            ['KP_6'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'right', 'vert': 'middle'})

        manager.register('scroll_left_top',
            ['KP_7'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'left', 'vert': 'top'})
        manager.register('scroll_middle_top',
            ['KP_8'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'middle', 'vert': 'top'})
        manager.register('scroll_right_top',
            ['KP_9'],
            self._window.scroll_to_fixed,
            kwargs={'horiz': 'right', 'vert': 'top'})

        # Enter/exit fullscreen.
        manager.register('exit_fullscreen',
            ['Escape'],
            self.escape_event)

        # View modes
        manager.register('double_page',
            ['d'],
            self._window.actiongroup.get_action('double_page').activate)


        manager.register('best_fit_mode',
            ['b'],
            self._window.actiongroup.get_action('best_fit_mode').activate)

        manager.register('fit_width_mode',
            ['w'],
            self._window.actiongroup.get_action('fit_width_mode').activate)

        manager.register('fit_height_mode',
            ['h'],
            self._window.actiongroup.get_action('fit_height_mode').activate)

        manager.register('fit_size_mode',
            ['s'],
            self._window.actiongroup.get_action('fit_size_mode').activate)

        manager.register('fit_manual_mode',
            ['a'],
            self._window.actiongroup.get_action('fit_manual_mode').activate)


        manager.register('manga_mode',
            ['m'],
            self._window.actiongroup.get_action('manga_mode').activate)

        manager.register('invert_scroll',
            ['x'],
            self._window.actiongroup.get_action('invert_scroll').activate)

        manager.register('keep_transformation',
            ['k'],
            self._window.actiongroup.get_action('keep_transformation').activate)

        manager.register('lens',
            ['l'],
            self._window.actiongroup.get_action('lens').activate)

        manager.register('stretch',
            ['y'],
            self._window.actiongroup.get_action('stretch').activate)

        # Zooming commands for manual zoom mode
        manager.register('zoom_in',
            ['plus', 'KP_Add', 'equal'],
            self._window.actiongroup.get_action('zoom_in').activate)
        manager.register('zoom_out',
            ['minus', 'KP_Subtract'],
            self._window.actiongroup.get_action('zoom_out').activate)
        # Zoom out is already defined as GTK menu hotkey
        manager.register('zoom_original',
            ['<Control>0', 'KP_0'],
            self._window.actiongroup.get_action('zoom_original').activate)

        manager.register('rotate_90',
            ['r'],
            self._window.rotate_90)

        manager.register('rotate_270',
            ['<Shift>r'],
            self._window.rotate_270)

        manager.register('rotate_180',
            [],
            self._window.rotate_180)

        manager.register('flip_horiz',
            [],
            self._window.flip_horizontally)

        manager.register('flip_vert',
            [],
            self._window.flip_vertically)

        manager.register('no_autorotation',
            [],
            self._window.actiongroup.get_action('no_autorotation').activate)

        manager.register('rotate_90_width',
            [],
            self._window.actiongroup.get_action('rotate_90_width').activate)
        manager.register('rotate_270_width',
            [],
            self._window.actiongroup.get_action('rotate_270_width').activate)

        manager.register('rotate_90_height',
            [],
            self._window.actiongroup.get_action('rotate_90_height').activate)

        manager.register('rotate_270_height',
            [],
            self._window.actiongroup.get_action('rotate_270_height').activate)

        # Arrow keys scroll the image
        manager.register('scroll_down',
            ['Down', 'KP_Down'],
            self._scroll_down)
        manager.register('scroll_up',
            ['Up', 'KP_Up'],
            self._scroll_up)
        manager.register('scroll_right',
            ['Right', 'KP_Right'],
            self._scroll_right)
        manager.register('scroll_left',
            ['Left', 'KP_Left'],
            self._scroll_left)

        # File operations
        manager.register('close',
            ['<Control>W'],
            self._window.filehandler.close_file)

        manager.register('quit',
            ['<Control>Q'],
            self._window.close_program)

        manager.register('save_and_quit',
            ['<Control><shift>q'],
            self._window.save_and_terminate_program)

        manager.register('delete',
            ['Delete'],
            self._window.delete)

        manager.register('extract_page',
            ['<Control><Shift>s'],
            self._window.extract_page)

        manager.register('refresh_archive',
            ['<control><shift>R'],
            self._window.filehandler.refresh_file)

        manager.register('next_archive',
            ['<control><shift>N'],
            self._window.filehandler._open_next_archive)

        manager.register('previous_archive',
            ['<control><shift>P'],
            self._window.filehandler._open_previous_archive)

        manager.register('next_directory',
            ['<control>N'],
            self._window.filehandler.open_next_directory)

        manager.register('previous_directory',
            ['<control>P'],
            self._window.filehandler.open_previous_directory)

        manager.register('comments',
            ['c'],
            self._window.actiongroup.get_action('comments').activate)

        manager.register('properties',
            ['<Alt>Return'],
            self._window.actiongroup.get_action('properties').activate)

        manager.register('preferences',
            ['F12'],
            self._window.actiongroup.get_action('preferences').activate)

        manager.register('edit_archive',
            [],
            self._window.actiongroup.get_action('edit_archive').activate)

        manager.register('open',
            ['<Control>O'],
            self._window.actiongroup.get_action('open').activate)

        manager.register('enhance_image',
            ['e'],
            self._window.actiongroup.get_action('enhance_image').activate)

        manager.register('library',
            ['<Control>L'],
            self._window.actiongroup.get_action('library').activate)

        # Space key scrolls down a percentage of the window height or the
        # image height at a time. When at the bottom it flips to the next
        # page.
        #
        # It also has a "smart scrolling mode" in which we try to follow
        # the flow of the comic.
        #
        # If Shift is pressed we should backtrack instead.
        manager.register('smart_scroll_down',
            ['space'],
            self._smart_scroll_down)
        manager.register('smart_scroll_up',
            ['<Shift>space'],
            self._smart_scroll_up)

        # User interface
        manager.register('osd_panel',
            ['Tab'],
            self._window.show_info_panel)

        manager.register('minimize',
            ['n'],
            self._window.minimize)

        manager.register('fullscreen',
            ['f', 'F11'],
            self._window.actiongroup.get_action('fullscreen').activate)

        manager.register('toolbar',
            [],
            self._window.actiongroup.get_action('toolbar').activate)

        manager.register('menubar',
            ['<Control>M'],
            self._window.actiongroup.get_action('menubar').activate)

        manager.register('statusbar',
            [],
            self._window.actiongroup.get_action('statusbar').activate)

        manager.register('scrollbar',
            [],
            self._window.actiongroup.get_action('scrollbar').activate)

        manager.register('thumbnails',
            ['F9'],
            self._window.actiongroup.get_action('thumbnails').activate)


        manager.register('hide_all',
            ['i'],
            self._window.actiongroup.get_action('hide_all').activate)

        manager.register('slideshow',
            ['<Control>S'],
            self._window.slideshow.toggle)

        # Execute external command. Bind keys from 1 to 9 to commands 1 to 9.
        for i in range(1, 10):
            manager.register('execute_command_%d' % i, ['%d' % i],
                             self._execute_command, args=[i - 1])

    def key_press_event(self, widget, event, *args):
        """Handle key press events on the main window."""

        # This is set on demand by callback functions
        self._scroll_protection = False

        # Dispatch keyboard input handling
        manager = keybindings.keybinding_manager(self._window)
        # Some keys can only be pressed with certain modifiers that
        # are irrelevant to the actual hotkey. Find out and ignore them.
        keymap = gtk.gdk.keymap_get_default()
        keyval, egroup, level, consumed = keymap.translate_keyboard_state(
                event.hardware_keycode, event.state, event.group)
        # 'consumed' is the modifier that was necessary to type the key
        manager.execute((event.keyval, event.state & ~consumed))

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

    def escape_event(self):
        """ Determines the behavior of the ESC key. """
        if prefs['escape quits']:
            self._window.close_program()
        else:
            self._window.actiongroup.get_action('fullscreen').set_active(False)

    def scroll_wheel_event(self, widget, event, *args):
        """Handle scroll wheel events on the main layout area. The scroll
        wheel flips pages in best fit mode and scrolls the scrollbars
        otherwise.
        """
        if 'GDK_BUTTON2_MASK' in event.state.value_names:
            return

        self._scroll_protection = True

        if event.direction == gtk.gdk.SCROLL_UP:
            if prefs['smart scroll']:
                self._smart_scroll_up(prefs['number of pixels to scroll per mouse wheel event'])
            else:
                self._scroll_with_flipping(0, -prefs['number of pixels to scroll per mouse wheel event'])

        elif event.direction == gtk.gdk.SCROLL_DOWN:
            if prefs['smart scroll']:
                self._smart_scroll_down(prefs['number of pixels to scroll per mouse wheel event'])
            else:
                self._scroll_with_flipping(0, prefs['number of pixels to scroll per mouse wheel event'])

        elif event.direction == gtk.gdk.SCROLL_RIGHT:
            if not self._window.is_manga_mode:
                self._window.next_page()
            else:
                self._previous_page_with_protection()

        elif event.direction == gtk.gdk.SCROLL_LEFT:
            if not self._window.is_manga_mode:
                self._previous_page_with_protection()
            else:
                self._window.next_page()

    def mouse_press_event(self, widget, event):
        """Handle mouse click events on the main layout area."""

        if event.button == 1:
            self._pressed_pointer_pos_x = event.x_root
            self._pressed_pointer_pos_y = event.y_root
            self._last_pointer_pos_x = event.x_root
            self._last_pointer_pos_y = event.y_root

        elif event.button == 2:
            self._window.actiongroup.get_action('lens').set_active(True)

        elif (event.button == 3 and
              not event.state & gtk.gdk.MOD1_MASK and
              not event.state & gtk.gdk.SHIFT_MASK):
            self._window.cursor_handler.set_cursor_type(constants.NORMAL_CURSOR)
            self._window.popup.popup(None, None, None, event.button,
                event.time)

        elif event.button == 4:
            self._window.show_info_panel()

    def mouse_release_event(self, widget, event):
        """Handle mouse button release events on the main layout area."""

        self._window.cursor_handler.set_cursor_type(constants.NORMAL_CURSOR)

        if (event.button == 1):

            if event.x_root == self._pressed_pointer_pos_x and \
                event.y_root == self._pressed_pointer_pos_y and \
                not self._window.was_out_of_focus:

                if event.state & gtk.gdk.SHIFT_MASK:
                    self._window.next_page_fast_forward()
                else:
                    self._window.next_page()

            else:
                self._window.was_out_of_focus = False

        elif event.button == 2:
            self._window.actiongroup.get_action('lens').set_active(False)

        elif event.button == 3:
            if event.state & gtk.gdk.MOD1_MASK:
                self._window.previous_page()
            elif event.state & gtk.gdk.SHIFT_MASK:
                self._window.previous_page_fast_forward()

    def mouse_move_event(self, widget, event):
        """Handle mouse pointer movement events."""

        if not self._window.is_in_focus:
            self._window.was_out_of_focus = True
        else:
            self._window.was_out_of_focus = False

        event = _get_latest_event_of_same_type(event)

        if 'GDK_BUTTON1_MASK' in event.state.value_names:
            self._window.cursor_handler.set_cursor_type(constants.GRAB_CURSOR)
            scrolled = self._window.scroll(self._last_pointer_pos_x - event.x_root,
                                           self._last_pointer_pos_y - event.y_root)

            # Cursor wrapping stuff. See:
            # https://sourceforge.net/tracker/?func=detail&aid=2988441&group_id=146377&atid=764987
            if prefs['wrap mouse scroll'] and scrolled:
                # FIXME: Problems with multi-screen setups
                screen = self._window.get_screen()
                warp_x0 = warp_y0 = 0
                warp_x1 = screen.get_width()
                warp_y1 = screen.get_height()

                new_x = _valwarp(event.x_root, warp_x1, minval=warp_x0)
                new_y = _valwarp(event.y_root, warp_y1, minval=warp_y0)
                if (new_x != event.x_root) or (new_y != event.y_root):
                    display = screen.get_display()
                    display.warp_pointer(screen, int(new_x), int(new_y))
                    ## This might be (or might not be) necessary to avoid
                    ## doing one warp multiple times.
                    event = _get_latest_event_of_same_type(event)

                self._last_pointer_pos_x = new_x
                self._last_pointer_pos_y = new_y
            else:
                self._last_pointer_pos_x = event.x_root
                self._last_pointer_pos_y = event.y_root
            self._drag_timer = event.time

        else:
            self._window.cursor_handler.refresh()

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
        uris = [portability.normalize_uri(uri) for uri in uris]
        paths = [urllib.url2pathname(uri).decode('utf-8') for uri in uris]

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

        self._scroll_protection = True
        self._last_scroll_was_direction_1 = False

        if self._window.scroll(x, y):
            self._extra_scroll_events = 0
            return True

        if y > 0 or (self._window.is_manga_mode and x < 0) or (
          not self._window.is_manga_mode and x > 0):
            forwards_scroll = True

        else:
            forwards_scroll = False

        if forwards_scroll:
            return not self._next_page_with_protection()
        else:
            return not self._previous_page_with_protection()

    def _scroll_down(self):
        """ Scrolls down. """
        self._scroll_with_flipping(0, prefs['number of pixels to scroll per key event'])

    def _scroll_up(self):
        """ Scrolls up. """
        self._scroll_with_flipping(0, -prefs['number of pixels to scroll per key event'])

    def _scroll_right(self):
        """ Scrolls right. """
        self._scroll_with_flipping(prefs['number of pixels to scroll per key event'], 0)

    def _scroll_left(self):
        """ Scrolls left. """
        self._scroll_with_flipping(-prefs['number of pixels to scroll per key event'], 0)

    def _smart_scroll_down(self, small_step=None):
        """ Smart scrolling. """

        width, height = self._window.get_visible_area_size()
        distance = prefs['smart scroll percentage']

        if small_step is None:
            x_step_small = x_step_large = int(width * distance)
            y_step_small = y_step_large = int(height * distance)
        else:
            x_step_small = small_step
            y_step_small = small_step
            x_step_large = int(width * distance)
            y_step_large = int(height * distance)

            if prefs['invert smart scroll']:
                x_step_small, y_step_small = y_step_small, x_step_small
                x_step_large, y_step_large = y_step_large, x_step_small

        if self._window.is_manga_mode:
            x_step_small *= -1
            x_step_large *= -1

        if not prefs["smart scroll"]:
            if not self._window.scroll(0, y_step_small):
                self._next_page_with_protection()
            return

        if self._window.displayed_double():
            if self._window.is_on_first_page():
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(x_step_small, 0, 'first')
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and y_step_large or y_step_small

                    if not self._window.scroll(0, scroll_size):

                        if not self._window.scroll_to_fixed(
                          horiz='startsecond'):
                            self._next_page_with_protection()
                        else:
                            self._window.scroll_to_fixed(
                                    vert='top')

                    else:

                        self._window.scroll_to_fixed(
                            horiz='startfirst')
            else:
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(x_step_small, 0, 'second')
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and y_step_large or y_step_small

                    if not self._window.scroll(0, scroll_size):
                        self._next_page_with_protection()
                    else:
                        self._window.scroll_to_fixed(
                            horiz='startsecond')
        else:
            # When a double page is displayed, scroll left/right,
            # then top/bottom
            if not prefs['invert smart scroll']:
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(x_step_small, 0)
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and y_step_large or y_step_small
                    if not self._window.scroll(0, scroll_size):
                        self._next_page_with_protection()
                    else:
                        self._window.scroll_to_fixed(
                            horiz='startfirst')
            # Scroll top/bottom, then left/right
            else:
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(0, y_step_small)
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and x_step_large or x_step_small
                    if not self._window.scroll(scroll_size, 0):
                        self._next_page_with_protection()
                    else:
                        self._window.scroll_to_fixed(
                            horiz='startsecond', vert='top')

    def _smart_scroll_up(self, small_step=None):
        """ Reversed smart scrolling. """

        width, height = self._window.get_visible_area_size()
        distance = prefs['smart scroll percentage']

        if small_step is None:
            x_step_small = x_step_large = int(width * distance)
            y_step_small = y_step_large = int(height * distance)
        else:
            x_step_small = small_step
            y_step_small = small_step
            x_step_large = int(width * distance)
            y_step_large = int(height * distance)

            if prefs['invert smart scroll']:
                x_step_small, y_step_small = y_step_small, x_step_small
                x_step_large, y_step_large = y_step_large, x_step_small

        if self._window.is_manga_mode:
            x_step_small *= -1
            x_step_large *= -1

        if not prefs["smart scroll"]:
            if not self._window.scroll(0, -y_step_small):
                self._previous_page_with_protection()
            return

        if self._window.displayed_double():
            if self._window.is_on_first_page():
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(-x_step_small, 0, 'first')
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and y_step_large or y_step_small

                    if not self._window.scroll(0, -scroll_size):
                        self._previous_page_with_protection()
                    else:
                        self._window.scroll_to_fixed(
                            horiz='endfirst')

            else:
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(-x_step_small, 0, 'second')
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and y_step_large or y_step_small

                    if not self._window.scroll(0, -scroll_size):

                        if not self._window.scroll_to_fixed(
                          horiz='endfirst'):
                            self._previous_page_with_protection()

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
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(-x_step_small, 0)
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and y_step_large or y_step_small
                    if not self._window.scroll(0, -scroll_size):
                        self._previous_page_with_protection()
                    else:
                        self._window.scroll_to_fixed(horiz='endfirst')
            # Scroll top/bottom, then left/right
            else:
                last_scroll = self._last_scroll_was_direction_1
                self._last_scroll_was_direction_1 = self._window.scroll(0, -y_step_small)
                if not self._last_scroll_was_direction_1:
                    scroll_size = last_scroll and x_step_large or x_step_small
                    if not self._window.scroll(-scroll_size, 0):
                        self._previous_page_with_protection()
                    else:
                        self._window.scroll_to_fixed(
                            horiz='startfirst', vert='bottom')

    def _next_page_with_protection(self):
        """ Advances to the next page. If L{_scroll_protection} is enabled,
        this method will only advance if enough scrolling attempts have been made.

        @return: True when the page was flipped."""

        if not prefs['flip with wheel']:
            self._extra_scroll_events = 0
            return False

        if (not self._scroll_protection
            or self._extra_scroll_events >= prefs['number of key presses before page turn'] - 1
            or not self._window.is_scrollable()):

            self._extra_scroll_events = 0
            self._window.next_page()
            return True

        elif (self._scroll_protection):
            self._extra_scroll_events = max(1, self._extra_scroll_events + 1)
            return False

        else:
            # This path should not be reached.
            assert False, "Programmer is moron, incorrect assertion."

    def _previous_page_with_protection(self):
        """ Goes back to the previous page. If L{_scroll_protection} is enabled,
        this method will only go back if enough scrolling attempts have been made.

        @return: True when the page was flipped."""

        if not prefs['flip with wheel']:
            self._extra_scroll_events = 0
            return False

        if (not self._scroll_protection
            or self._extra_scroll_events <= -prefs['number of key presses before page turn'] + 1
            or not self._window.is_scrollable()):

            self._extra_scroll_events = 0
            self._window.previous_page()
            return True

        elif (self._scroll_protection):
            self._extra_scroll_events = min(-1, self._extra_scroll_events - 1)
            return False

        else:
            # This path should not be reached.
            assert False, "Programmer is moron, incorrect assertion."

    def _left_right_page_progress(self, left=True):
        """ If left is True, this function advances one page in manga mode and goes
        back one page in normal mode. The opposite happens for left=False. """

        next = not left
        if self._window.is_manga_mode:
            # Switch next and previous page
            next = not next

        if next:
            self._window.next_page()
        else:
            self._window.previous_page()

    def _execute_command(self, cmdindex):
        """ Execute an external command. cmdindex should be an integer from 0 to 9,
        representing the command that should be executed. """
        manager = openwith.OpenWithManager()
        commands = [cmd for cmd in manager.get_commands() if not cmd.is_separator()]
        if len(commands) > cmdindex:
            commands[cmdindex].execute(self._window)


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


def _valwarp(cur, maxval, minval=0, tolerance=3, extra=2):
    """ Helper function for warping the cursor around the screen when it
      comes within `tolerance` to a border (and `extra` more to avoid
      jumping back and forth).  """
    if cur < minval + tolerance:
        overmove = minval + tolerance - cur
        return maxval - tolerance - overmove - extra
    if (maxval - cur) < tolerance:
        overmove = tolerance - (maxval - cur)
        return minval + tolerance + overmove + extra
    return cur


# vim: expandtab:sw=4:ts=4

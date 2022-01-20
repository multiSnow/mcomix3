'''event.py - Event handling (keyboard, mouse, etc.) for the main window.
'''

import urllib
from gi.repository import Gdk, Gtk

from mcomix.preferences import prefs
from mcomix import constants
from mcomix import portability
from mcomix import keybindings
from mcomix import openwith


class EventHandler(object):

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

    def resize_event(self, widget, event):
        '''Handle events from resizing and moving the main window.'''
        size = (event.width, event.height)
        if size != self._window.previous_size:
            self._window.previous_size = size
            self._window.draw_image()

    def window_state_event(self, widget, event):
        is_fullscreen = self._window.is_fullscreen
        # Some window manager has special methods to set or exit fullscreen.
        # (e.g. gesture on touchscreen)
        # In this case, toggleaction will not be correctly set.
        # So, set the activation of toggleaction again with window-state-event.
        # Also see comment in main.MainWindow.change_fullscreen
        toggleaction = self._window.actiongroup.get_action('fullscreen')
        toggleaction.set_active(is_fullscreen)
        if self._window.was_fullscreen != is_fullscreen:
            # Fullscreen state changed.
            self._window.was_fullscreen = is_fullscreen
            if is_fullscreen:
                redraw = True
            else:
                # Only redraw if we don't need to restore geometry.
                redraw = not self._window.restore_window_geometry()
            self._window._update_toggles_sensitivity()
            if redraw:
                self._window.previous_size = self._window.get_size()
                self._window.draw_image()

    def register_key_events(self):
        ''' Registers keyboard events and their default binings, and hooks
        them up with their respective callback functions. '''

        manager = keybindings.keybinding_manager(self._window)

        # Navigation keys
        manager.register('previous_page',
                         self._flip_page, kwargs={'number_of_pages': -1})
        manager.register('next_page',
                         self._flip_page, kwargs={'number_of_pages': 1})
        manager.register('previous_page_singlestep',
                         self._flip_page, kwargs={'number_of_pages': -1, 'single_step': True})
        manager.register('next_page_singlestep',
                         self._flip_page, kwargs={'number_of_pages': 1, 'single_step': True})
        manager.register('previous_page_dynamic',
                         self._left_right_page_progress, kwargs={'number_of_pages': -1})
        manager.register('next_page_dynamic',
                         self._left_right_page_progress, kwargs={'number_of_pages': 1})

        manager.register('previous_page_ff',
                         self._flip_page, kwargs={'number_of_pages': -10})
        manager.register('next_page_ff',
                         self._flip_page, kwargs={'number_of_pages': 10})

        manager.register('first_page',
                         self._window.first_page)
        manager.register('last_page',
                         self._window.last_page)
        manager.register('go_to',
                         self._window.page_select)

        manager.register('scroll_left_bottom',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (-1, 1), 'index': constants.UNION_INDEX})
        manager.register('scroll_middle_bottom',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (constants.SCROLL_TO_CENTER, 1),
                                 'index': constants.UNION_INDEX})
        manager.register('scroll_right_bottom',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (1, 1), 'index': constants.UNION_INDEX})

        manager.register('scroll_left_middle',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (-1, constants.SCROLL_TO_CENTER),
                                 'index': constants.UNION_INDEX})
        manager.register('scroll_middle',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (constants.SCROLL_TO_CENTER,
                                                 constants.SCROLL_TO_CENTER), 'index': constants.UNION_INDEX})
        manager.register('scroll_right_middle',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (1, constants.SCROLL_TO_CENTER),
                                 'index': constants.UNION_INDEX})

        manager.register('scroll_left_top',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (-1, -1), 'index': constants.UNION_INDEX})
        manager.register('scroll_middle_top',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (constants.SCROLL_TO_CENTER, -1),
                                 'index': constants.UNION_INDEX})
        manager.register('scroll_right_top',
                         self._window.scroll_to_predefined,
                         kwargs={'destination': (1, -1), 'index': constants.UNION_INDEX})

        # Enter/exit fullscreen.
        manager.register('exit_fullscreen',
                         self.escape_event)

        # View modes
        manager.register('double_page',
                         self._window.actiongroup.get_action('double_page').activate)

        manager.register('best_fit_mode',
                         self._window.actiongroup.get_action('best_fit_mode').activate)
        manager.register('fit_width_mode',
                         self._window.actiongroup.get_action('fit_width_mode').activate)
        manager.register('fit_height_mode',
                         self._window.actiongroup.get_action('fit_height_mode').activate)
        manager.register('fit_size_mode',
                         self._window.actiongroup.get_action('fit_size_mode').activate)
        manager.register('fit_manual_mode',
                         self._window.actiongroup.get_action('fit_manual_mode').activate)

        manager.register('manga_mode',
                         self._window.actiongroup.get_action('manga_mode').activate)
        manager.register('invert_scroll',
                         self._window.actiongroup.get_action('invert_scroll').activate)
        manager.register('keep_transformation',
                         self._window.actiongroup.get_action('keep_transformation').activate)
        manager.register('lens',
                         self._window.actiongroup.get_action('lens').activate)
        manager.register('stretch',
                         self._window.actiongroup.get_action('stretch').activate)

        # Zooming commands for manual zoom mode
        manager.register('zoom_in',
                         self._window.actiongroup.get_action('zoom_in').activate)
        manager.register('zoom_out',
                         self._window.actiongroup.get_action('zoom_out').activate)
        manager.register('zoom_original',
                         self._window.actiongroup.get_action('zoom_original').activate)

        manager.register('rotate_90',
                         self._window.rotate_90)
        manager.register('rotate_270',
                         self._window.rotate_270)
        manager.register('rotate_180',
                         self._window.rotate_180)
        manager.register('flip_horiz',
                         self._window.flip_horizontally)
        manager.register('flip_vert',
                         self._window.flip_vertically)
        manager.register('no_autorotation',
                         self._window.actiongroup.get_action('no_autorotation').activate)
        manager.register('rotate_90_width',
                         self._window.actiongroup.get_action('rotate_90_width').activate)
        manager.register('rotate_270_width',
                         self._window.actiongroup.get_action('rotate_270_width').activate)
        manager.register('rotate_90_height',
                         self._window.actiongroup.get_action('rotate_90_height').activate)
        manager.register('rotate_270_height',
                         self._window.actiongroup.get_action('rotate_270_height').activate)

        manager.register('scroll_down',
                         self._scroll_down)
        manager.register('scroll_up',
                         self._scroll_up)
        manager.register('scroll_right',
                         self._scroll_right)
        manager.register('scroll_left',
                         self._scroll_left)

        # File operations
        manager.register('close',
                         self._window.filehandler.close_file)
        manager.register('quit',
                         self._window.close_program)
        manager.register('save_and_quit',
                         self._window.save_and_terminate_program)
        manager.register('extract_page',
                         self._window.extract_page)
        manager.register('refresh_archive',
                         self._window.filehandler.refresh_file)
        manager.register('next_archive',
                         self._window.filehandler._open_next_archive)
        manager.register('previous_archive',
                         self._window.filehandler._open_previous_archive)
        manager.register('next_directory',
                         self._window.filehandler.open_next_directory)
        manager.register('previous_directory',
                         self._window.filehandler.open_previous_directory)
        manager.register('comments',
                         self._window.actiongroup.get_action('comments').activate)
        manager.register('properties',
                         self._window.actiongroup.get_action('properties').activate)
        manager.register('preferences',
                         self._window.actiongroup.get_action('preferences').activate)
        manager.register('edit_archive',
                         self._window.actiongroup.get_action('edit_archive').activate)
        manager.register('open',
                         self._window.actiongroup.get_action('open').activate)
        manager.register('enhance_image',
                         self._window.actiongroup.get_action('enhance_image').activate)
        manager.register('library',
                         self._window.actiongroup.get_action('library').activate)

        manager.register('smart_scroll_down',
                         self._smart_scroll_down)
        manager.register('smart_scroll_up',
                         self._smart_scroll_up)

        # User interface
        manager.register('osd_panel',
                         self._window.show_info_panel)
        manager.register('minimize',
                         self._window.minimize)
        manager.register('fullscreen',
                         lambda:self._window.actiongroup.get_action('fullscreen').set_active(True))
        manager.register('toggle_fullscreen',
                         self._window.actiongroup.get_action('fullscreen').activate)
        manager.register('toolbar',
                         self._window.actiongroup.get_action('toolbar').activate)
        manager.register('menubar',
                         self._window.actiongroup.get_action('menubar').activate)
        manager.register('statusbar',
                         self._window.actiongroup.get_action('statusbar').activate)
        manager.register('scrollbar',
                         self._window.actiongroup.get_action('scrollbar').activate)
        manager.register('thumbnails',
                         self._window.actiongroup.get_action('thumbnails').activate)
        manager.register('hide_all',
                         self._window.actiongroup.get_action('hide_all').activate)
        manager.register('slideshow',
                         self._window.actiongroup.get_action('slideshow').activate)

        manager.register('keyhandler_open',
                         self._window.actiongroup.get_action('keyhandler_open').activate)

        # Execute external command. Bind keys from 1 to 9 to commands 1 to 9.
        for i in range(1, 10):
            manager.register('execute_command_%d' % i,
                             self._execute_command, args=[i - 1])

    def key_press_event(self, widget, event, *args):
        '''Handle key press events on the main window.'''

        # This is set on demand by callback functions
        self._scroll_protection = False

        # Dispatch keyboard input handling
        manager = keybindings.keybinding_manager(self._window)
        # Some keys can only be pressed with certain modifiers that
        # are irrelevant to the actual hotkey. Find out and ignore them.
        ALL_ACCELS_MASK = (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK |
                           Gdk.ModifierType.MOD1_MASK)

        keymap = Gdk.Keymap.get_default()
        code = keymap.translate_keyboard_state(
            event.hardware_keycode, event.get_state(), event.group)

        if code[0]:
            keyval = code[1]
            consumed = code[4]

            # If the resulting key is upper case (i.e. SHIFT + key),
            # convert it to lower case and remove SHIFT from the consumed flags
            # to match how keys are registered (<Shift> + lowercase)
            if (event.get_state() & Gdk.ModifierType.SHIFT_MASK and
                keyval != Gdk.keyval_to_lower(keyval)):
                keyval = Gdk.keyval_to_lower(keyval)
                consumed &= ~Gdk.ModifierType.SHIFT_MASK

            # 'consumed' is the modifier that was necessary to type the key
            manager.execute((keyval, event.get_state() & ~consumed & ALL_ACCELS_MASK))

        # ---------------------------------------------------------------
        # Register CTRL for scrolling only one page instead of two
        # pages in double page mode. This is mainly for mouse scrolling.
        # ---------------------------------------------------------------
        if event.keyval in (Gdk.KEY_Control_L, Gdk.KEY_Control_R):
            self._window.imagehandler.force_single_step = True

        # ----------------------------------------------------------------
        # We kill the signals here for the Up, Down, Space and Enter keys,
        # or they will start fiddling with the thumbnail selector (bad).
        # ----------------------------------------------------------------
        if (event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down,
                             Gdk.KEY_space, Gdk.KEY_KP_Enter, Gdk.KEY_KP_Up,
                             Gdk.KEY_KP_Down, Gdk.KEY_KP_Home, Gdk.KEY_KP_End,
                             Gdk.KEY_KP_Page_Up, Gdk.KEY_KP_Page_Down) or
            (event.keyval == Gdk.KEY_Return and not
             'GDK_MOD1_MASK' in event.get_state().value_names)):

            self._window.stop_emission_by_name('key_press_event')
            return True

    def key_release_event(self, widget, event, *args):
        ''' Handle release of keys for the main window. '''

        # ---------------------------------------------------------------
        # Unregister CTRL for scrolling only one page in double page mode
        # ---------------------------------------------------------------
        if event.keyval in (Gdk.KEY_Control_L, Gdk.KEY_Control_R):
            self._window.imagehandler.force_single_step = False

    def escape_event(self):
        ''' Determines the behavior of the ESC key. '''
        if prefs['escape quits']:
            self._window.close_program()
        else:
            self._window.actiongroup.get_action('fullscreen').set_active(False)

    def scroll_wheel_event(self, widget, event, *args):
        '''Handle scroll wheel events on the main layout area. The scroll
        wheel flips pages in best fit mode and scrolls the scrollbars
        otherwise.
        '''
        if event.get_state() & Gdk.ModifierType.BUTTON2_MASK:
            return

        has_direction, direction = event.get_scroll_direction()
        if not has_direction:
            direction = None
            has_delta, delta_x, delta_y = event.get_scroll_deltas()
            if has_delta:
                if delta_y < 0:
                    direction = Gdk.ScrollDirection.UP
                elif delta_y > 0:
                    direction = Gdk.ScrollDirection.DOWN
                elif delta_x < 0:
                    direction = Gdk.ScrollDirection.LEFT
                elif delta_x > 0:
                    direction = Gdk.ScrollDirection.RIGHT

        self._scroll_protection = True

        if direction == Gdk.ScrollDirection.UP:
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                self._window.manual_zoom_in()
            elif prefs['smart scroll']:
                self._smart_scroll_up(prefs['number of pixels to scroll per mouse wheel event'])
            else:
                self._scroll_with_flipping(0, -prefs['number of pixels to scroll per mouse wheel event'])

        elif direction == Gdk.ScrollDirection.DOWN:
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                self._window.manual_zoom_out()
            elif prefs['smart scroll']:
                self._smart_scroll_down(prefs['number of pixels to scroll per mouse wheel event'])
            else:
                self._scroll_with_flipping(0, prefs['number of pixels to scroll per mouse wheel event'])

        elif direction == Gdk.ScrollDirection.RIGHT:
            self._scroll_with_flipping(prefs['number of pixels to scroll per mouse wheel event'], 0)

        elif direction == Gdk.ScrollDirection.LEFT:
            self._scroll_with_flipping(-prefs['number of pixels to scroll per mouse wheel event'], 0)

    def mouse_press_event(self, widget, event):
        '''Handle mouse click events on the main layout area.'''

        if self._window.was_out_of_focus:
            return

        if event.button == 1:
            self._pressed_pointer_pos_x = event.x_root
            self._pressed_pointer_pos_y = event.y_root
            self._last_pointer_pos_x = event.x_root
            self._last_pointer_pos_y = event.y_root

        elif event.button == 2:
            self._window.actiongroup.get_action('lens').set_active(True)

        elif (event.button == 3 and
              not event.get_state() & Gdk.ModifierType.MOD1_MASK and
              not event.get_state() & Gdk.ModifierType.SHIFT_MASK):
            self._window.cursor_handler.set_cursor_type(constants.NORMAL_CURSOR)
            self._window.popup.popup(None, None, None, None,
                                     event.button, event.time)

        elif event.button == 4:
            self._window.show_info_panel()

    def mouse_release_event(self, widget, event):
        '''Handle mouse button release events on the main layout area.'''

        self._window.cursor_handler.set_cursor_type(constants.NORMAL_CURSOR)

        if event.button == 1:

            if self._window.was_out_of_focus:
                # main window should always focused before the release event occured.
                # it should be a bug of gtk if interpreter goes to here.
                return

            if not prefs['flip with click']:
                return

            if (self._pressed_pointer_pos_x, self._pressed_pointer_pos_y) == \
               (event.x_root, event.y_root):

                # right to next, left to previous, no matter the double page mode
                direction = 1 if event.x > widget.get_property('width') // 2 else -1

                # if in manga mode, left to next, right to previous
                if self._window.is_manga_mode:
                    direction *= -1

                # over flip with shift pressed
                if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                    direction *= 10

                self._flip_page(direction)

        elif event.button == 2:
            self._window.actiongroup.get_action('lens').set_active(False)

        elif event.button == 3:
            if event.get_state() & Gdk.ModifierType.MOD1_MASK:
                self._flip_page(-1)
            elif event.get_state() & Gdk.ModifierType.SHIFT_MASK:
                self._flip_page(-10)

    def mouse_move_event(self, widget, event):
        '''Handle mouse pointer movement events.'''

        event = _get_latest_event_of_same_type(event)

        if 'GDK_BUTTON1_MASK' in event.get_state().value_names:
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

    def drag_n_drop_event(self, widget, context, x, y, selection, drag_id,
                          eventtime):
        '''Handle drag-n-drop events on the main layout area.'''
        # The drag source is inside MComix itself, so we ignore.

        if (Gtk.drag_get_source_widget(context) is not None):
            return

        uris = selection.get_uris()

        if not uris:
            return

        # Normalize URIs
        uris = [portability.normalize_uri(uri) for uri in uris]
        paths = [urllib.request.url2pathname(uri) for uri in uris]

        if len(paths) > 1:
            self._window.filehandler.open_file(paths)
        else:
            self._window.filehandler.open_file(paths[0])

    def _scroll_with_flipping(self, x, y):
        '''Handle scrolling with the scroll wheel or the arrow keys, for which
        the pages might be flipped depending on the preferences.  Returns True
        if able to scroll without flipping and False if a new page was flipped
        to.
        '''

        self._scroll_protection = True

        if self._window.scroll(x, y):
            self._extra_scroll_events = 0
            return True

        if y > 0 or \
           (self._window.is_manga_mode and x < 0) or \
           (not self._window.is_manga_mode and x > 0):
            page_flipped = self._next_page_with_protection()
        else:
            page_flipped = self._previous_page_with_protection()

        return not page_flipped

    def _scroll_down(self):
        ''' Scrolls down. '''
        self._scroll_with_flipping(0, prefs['number of pixels to scroll per key event'])

    def _scroll_up(self):
        ''' Scrolls up. '''
        self._scroll_with_flipping(0, -prefs['number of pixels to scroll per key event'])

    def _scroll_right(self):
        ''' Scrolls right. '''
        self._scroll_with_flipping(prefs['number of pixels to scroll per key event'], 0)

    def _scroll_left(self):
        ''' Scrolls left. '''
        self._scroll_with_flipping(-prefs['number of pixels to scroll per key event'], 0)

    def _smart_scroll_down(self, small_step=None):
        ''' Smart scrolling. '''
        self._smart_scrolling(small_step, False)

    def _smart_scroll_up(self, small_step=None):
        ''' Reversed smart scrolling. '''
        self._smart_scrolling(small_step, True)

    def _smart_scrolling(self, small_step, backwards):
        # Collect data from the environment
        viewport_size = self._window.get_visible_area_size()
        distance = prefs['smart scroll percentage']
        if small_step is None:
            max_scroll = [distance * viewport_size[0],
                          distance * viewport_size[1]] # 2D only
        else:
            max_scroll = [small_step] * 2 # 2D only
        swap_axes = constants.SWAPPED_AXES if prefs['invert smart scroll'] \
            else constants.NORMAL_AXES
        self._window.update_layout_position()

        # Scroll to the new position
        new_index = self._window.layout.scroll_smartly(max_scroll, backwards, swap_axes)
        n = 2 if self._window.displayed_double() else 1 # XXX limited to at most 2 pages

        if new_index == -1:
            self._previous_page_with_protection()
        elif new_index == n:
            self._next_page_with_protection()
        else:
            # Update actual viewport
            self._window.update_viewport_position()


    def _next_page_with_protection(self):
        ''' Advances to the next page. If L{_scroll_protection} is enabled,
        this method will only advance if enough scrolling attempts have been made.

        @return: True when the page was flipped.'''

        if not prefs['flip with wheel']:
            self._extra_scroll_events = 0
            return False

        if (not self._scroll_protection
            or self._extra_scroll_events >= prefs['number of key presses before page turn'] - 1
            or not self._window.is_scrollable()):

            self._flip_page(1)
            return True

        elif (self._scroll_protection):
            self._extra_scroll_events = max(1, self._extra_scroll_events + 1)
            return False

        else:
            # This path should not be reached.
            assert False, 'Programmer is moron, incorrect assertion.'

    def _previous_page_with_protection(self):
        ''' Goes back to the previous page. If L{_scroll_protection} is enabled,
        this method will only go back if enough scrolling attempts have been made.

        @return: True when the page was flipped.'''

        if not prefs['flip with wheel']:
            self._extra_scroll_events = 0
            return False

        if (not self._scroll_protection
            or self._extra_scroll_events <= -prefs['number of key presses before page turn'] + 1
            or not self._window.is_scrollable()):

            self._flip_page(-1)
            return True

        elif (self._scroll_protection):
            self._extra_scroll_events = min(-1, self._extra_scroll_events - 1)
            return False

        else:
            # This path should not be reached.
            assert False, 'Programmer is moron, incorrect assertion.'


    def _flip_page(self, number_of_pages, single_step=False):
        ''' Switches a number of pages forwards/backwards. If C{single_step} is True,
        the page count will be advanced by only one page even in double page mode. '''
        self._extra_scroll_events = 0
        self._window.flip_page(number_of_pages, single_step=single_step)

    def _left_right_page_progress(self, number_of_pages=1):
        ''' If number_of_pages is positive, this function advances the specified
        number of pages in manga mode and goes back the same number of pages in
        normal mode. The opposite happens for number_of_pages being negative. '''
        self._flip_page(-number_of_pages if self._window.is_manga_mode else number_of_pages)

    def _execute_command(self, cmdindex):
        ''' Execute an external command. cmdindex should be an integer from 0 to 9,
        representing the command that should be executed. '''
        manager = openwith.OpenWithManager()
        commands = [cmd for cmd in manager.get_commands() if not cmd.is_separator()]
        if len(commands) > cmdindex:
            commands[cmdindex].execute(self._window)


def _get_latest_event_of_same_type(event):
    '''Return the latest event in the event queue that is of the same type
    as <event>, or <event> itself if no such events are in the queue. All
    events of that type will be removed from the event queue.
    '''
    return event
    events = []

    while Gdk.events_pending():
        queued_event = Gdk.event_get()

        if queued_event is not None:

            if queued_event.type == event.type:
                event = queued_event
            else:
                events.append(queued_event)

    for queued_event in events:
        queued_event.put()

    return event


def _valwarp(cur, maxval, minval=0, tolerance=3, extra=2):
    ''' Helper function for warping the cursor around the screen when it
      comes within `tolerance` to a border (and `extra` more to avoid
      jumping back and forth).  '''
    if cur < minval + tolerance:
        overmove = minval + tolerance - cur
        return maxval - tolerance - overmove - extra
    if (maxval - cur) < tolerance:
        overmove = tolerance - (maxval - cur)
        return minval + tolerance + overmove + extra
    return cur


# vim: expandtab:sw=4:ts=4

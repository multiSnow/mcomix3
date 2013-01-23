"""main.py - Main window."""

import os
import shutil
import threading
import gtk
import gobject

from mcomix import constants
from mcomix import cursor_handler
from mcomix import i18n
from mcomix import enhance_backend
from mcomix import enhance_dialog
from mcomix import event
from mcomix import file_handler
from mcomix import image_handler
from mcomix import image_tools
from mcomix import lens
from mcomix import preferences
from mcomix.preferences import prefs
from mcomix import ui
from mcomix import slideshow
from mcomix import status
from mcomix import thumbbar
from mcomix import clipboard
from mcomix import pageselect
from mcomix import osd
from mcomix import keybindings
from mcomix import zoom
from mcomix import bookmark_backend
from mcomix import message_dialog
from mcomix.library import backend


class MainWindow(gtk.Window):

    """The main window, is created at start and terminates the
    program when closed.
    """

    def __init__(self, fullscreen=False, is_slideshow=slideshow,
            show_library=False, manga_mode=False, double_page=False,
            zoom_mode=None, open_path=None, open_page=1):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

        # ----------------------------------------------------------------
        # Attributes
        # ----------------------------------------------------------------
        self.is_in_focus = True
        self.is_fullscreen = False
        self.is_double_page = False
        self.is_manga_mode = False
        self.is_virtual_double_page = False  # I.e. a wide image is displayed
        self.width = None
        self.height = None
        self.was_out_of_focus = False
        #: Used to remember if changing to fullscreen enabled 'Hide all'
        self.hide_all_forced = False

        self._waiting_for_redraw = False

        self._image_box = gtk.HBox(False, 2)
        self._main_layout = gtk.Layout()
        self._event_handler = event.EventHandler(self)
        self._vadjust = self._main_layout.get_vadjustment()
        self._hadjust = self._main_layout.get_hadjustment()
        self._vscroll = gtk.VScrollbar(self._vadjust)
        self._hscroll = gtk.HScrollbar(self._hadjust)

        self.filehandler = file_handler.FileHandler(self)
        self.imagehandler = image_handler.ImageHandler(self)
        self.imagehandler.page_available += self._page_available
        self.thumbnailsidebar = thumbbar.ThumbnailSidebar(self)

        self.statusbar = status.Statusbar()
        self.clipboard = clipboard.Clipboard(self)
        self.slideshow = slideshow.Slideshow(self)
        self.cursor_handler = cursor_handler.CursorHandler(self)
        self.enhancer = enhance_backend.ImageEnhancer(self)
        self.lens = lens.MagnifyingLens(self)
        self.osd = osd.OnScreenDisplay(self)
        self.zoom = zoom.ZoomModel()
        self.zoom.zoom_changed += lambda zoom: self.draw_image()
        self.uimanager = ui.MainUI(self)
        self.menubar = self.uimanager.get_widget('/Menu')
        self.toolbar = self.uimanager.get_widget('/Tool')
        self.popup = self.uimanager.get_widget('/Popup')
        self.actiongroup = self.uimanager.get_action_groups()[0]

        self.left_image = gtk.Image()
        self.right_image = gtk.Image()

        # ----------------------------------------------------------------
        # Setup
        # ----------------------------------------------------------------
        self.set_title(constants.APPNAME)
        self.set_size_request(300, 300)  # Avoid making the window *too* small
        self.resize(prefs['window width'], prefs['window height'])

        # Hook up any additional key events not handled by UI accelerators
        self._event_handler.register_key_events()

        # This is a hack to get the focus away from the toolbar so that
        # we don't activate it with space or some other key (alternative?)
        self.toolbar.set_focus_child(
            self.uimanager.get_widget('/Tool/expander'))
        self.toolbar.set_style(gtk.TOOLBAR_ICONS)
        self.toolbar.set_icon_size(gtk.ICON_SIZE_LARGE_TOOLBAR)

        self._image_box.add(self.left_image)
        self._image_box.add(self.right_image)
        self._image_box.show_all()

        self._main_layout.put(self._image_box, 0, 0)
        self.set_bg_colour(prefs['bg colour'])

        self._vadjust.step_increment = 15
        self._vadjust.page_increment = 1
        self._hadjust.step_increment = 15
        self._hadjust.page_increment = 1

        table = gtk.Table(2, 2, False)
        table.attach(self.thumbnailsidebar, 0, 1, 2, 5, gtk.FILL,
            gtk.FILL|gtk.EXPAND, 0, 0)

        table.attach(self._main_layout, 1, 2, 2, 3, gtk.FILL|gtk.EXPAND,
            gtk.FILL|gtk.EXPAND, 0, 0)
        table.attach(self._vscroll, 2, 3, 2, 3, gtk.FILL|gtk.SHRINK,
            gtk.FILL|gtk.SHRINK, 0, 0)
        table.attach(self._hscroll, 1, 2, 4, 5, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)
        table.attach(self.menubar, 0, 3, 0, 1, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)
        table.attach(self.toolbar, 0, 3, 1, 2, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)
        table.attach(self.statusbar, 0, 3, 5, 6, gtk.FILL|gtk.SHRINK,
            gtk.FILL, 0, 0)

        if prefs['default double page'] or double_page:
            self.actiongroup.get_action('double_page').activate()

        if prefs['default manga mode'] or manga_mode:
            self.actiongroup.get_action('manga_mode').activate()

        # Determine zoom mode. If zoom_mode is passed, it overrides
        # the zoom mode preference.
        zoom_actions = { constants.ZOOM_MODE_BEST : 'best_fit_mode',
                constants.ZOOM_MODE_WIDTH : 'fit_width_mode',
                constants.ZOOM_MODE_HEIGHT : 'fit_height_mode',
                constants.ZOOM_MODE_SIZE : 'fit_size_mode',
                constants.ZOOM_MODE_MANUAL : 'fit_manual_mode' }

        if zoom_mode is not None:
            zoom_action = zoom_actions[zoom_mode]
        else:
            zoom_action = zoom_actions[prefs['zoom mode']]

        if zoom_action == 'fit_manual_mode':
            # This little ugly hack is to get the activate call on
            # 'fit_manual_mode' to actually create an event (and callback).
            # Since manual mode is the default selected radio button action
            # it won't send an event if we activate it when it is already
            # the selected one.
            self.actiongroup.get_action('best_fit_mode').activate()

        self.actiongroup.get_action(zoom_action).activate()

        if prefs['stretch']:
            self.actiongroup.get_action('stretch').activate()

        if prefs['invert smart scroll']:
            self.actiongroup.get_action('invert_scroll').activate()

        if prefs['show toolbar']:
            prefs['show toolbar'] = False
            self.actiongroup.get_action('toolbar').activate()

        if prefs['show menubar']:
            prefs['show menubar'] = False
            self.actiongroup.get_action('menubar').activate()

        if prefs['show statusbar']:
            prefs['show statusbar'] = False
            self.actiongroup.get_action('statusbar').activate()

        if prefs['show scrollbar']:
            prefs['show scrollbar'] = False
            self.actiongroup.get_action('scrollbar').activate()

        if prefs['show thumbnails']:
            prefs['show thumbnails'] = False
            self.actiongroup.get_action('thumbnails').activate()

        if prefs['hide all']:
            prefs['hide all'] = False
            self.actiongroup.get_action('hide all').activate()

        if prefs['keep transformation']:
            prefs['keep transformation'] = False
            self.actiongroup.get_action('keep_transformation').activate()
        else:
            prefs['rotation'] = 0
            prefs['vertical flip'] = False
            prefs['horizontal flip'] = False

        self.actiongroup.get_action('menu_autorotate_width').set_sensitive(False)
        self.actiongroup.get_action('menu_autorotate_height').set_sensitive(False)

        self.add(table)
        table.show()
        self._main_layout.show()
        self._display_active_widgets()

        self._main_layout.set_events(gtk.gdk.BUTTON1_MOTION_MASK |
                                     gtk.gdk.BUTTON2_MOTION_MASK |
                                     gtk.gdk.BUTTON_PRESS_MASK |
                                     gtk.gdk.BUTTON_RELEASE_MASK |
                                     gtk.gdk.POINTER_MOTION_MASK)

        self._main_layout.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                                        [('text/uri-list', 0, 0)],
                                        gtk.gdk.ACTION_COPY |
                                        gtk.gdk.ACTION_MOVE)

        self.connect( 'focus-in-event', self.gained_focus )
        self.connect( 'focus-out-event', self.lost_focus )
        self.connect('delete_event', self.close_program)
        self.connect('key_press_event', self._event_handler.key_press_event)
        self.connect('key_release_event', self._event_handler.key_release_event)
        self.connect('configure_event', self._event_handler.resize_event)

        self._main_layout.connect('button_release_event',
            self._event_handler.mouse_release_event)
        self._main_layout.connect('scroll_event',
            self._event_handler.scroll_wheel_event)
        self._main_layout.connect('button_press_event',
            self._event_handler.mouse_press_event)
        self._main_layout.connect('motion_notify_event',
            self._event_handler.mouse_move_event)
        self._main_layout.connect('drag_data_received',
            self._event_handler.drag_n_drop_event)

        self.uimanager.set_sensitivities()
        self.show()

        # If MComix is set to start in fullscreen mode, it
        # cannot switch to windowed mode on Win32 unless this
        # condition is set to trigger after normal show().
        if prefs['default fullscreen'] or fullscreen:
            self.actiongroup.get_action('fullscreen').activate()

        if prefs['previous quit was quit and save']:
            fileinfo = self.filehandler.read_fileinfo_file()

            if fileinfo != None:

                open_path = fileinfo[0]
                open_page = fileinfo[1] + 1

        prefs['previous quit was quit and save'] = False

        if open_path is not None:
            self.filehandler.open_file(open_path, open_page)

        if is_slideshow:
            self.actiongroup.get_action('slideshow').activate()

        if show_library:
            self.actiongroup.get_action('library').activate()

    def gained_focus(self, *args):
        self.is_in_focus = True

    def lost_focus(self, *args):
        self.is_in_focus = False

        # If the user presses CTRL for a keyboard shortcut, e.g. to
        # open the library, key_release_event isn't fired and force_single_step
        # isn't properly unset.
        self.imagehandler.force_single_step = False

    def draw_image(self, at_bottom=False, scroll=False):
        """Draw the current pages and update the titlebar and statusbar.
        """
        if not self._waiting_for_redraw:  # Don't stack up redraws.
            self._waiting_for_redraw = True
            gobject.idle_add(self._draw_image, at_bottom, scroll,
                priority=gobject.PRIORITY_HIGH_IDLE)

    def _draw_image(self, at_bottom, scroll):
        self._display_active_widgets()

        if not self.filehandler.file_loaded:
            self._waiting_for_redraw = False
            return False

        self.is_virtual_double_page = \
            self.imagehandler.get_virtual_double_page()

        skip_pixbuf = not self.imagehandler.page_is_available()

        if self.displayed_double() and not skip_pixbuf:
            left_pixbuf, right_pixbuf = self.imagehandler.get_pixbufs()
            if self.is_manga_mode:
                right_pixbuf, left_pixbuf = left_pixbuf, right_pixbuf
            left_unscaled_x = left_pixbuf.get_width()
            left_unscaled_y = left_pixbuf.get_height()
            right_unscaled_x = right_pixbuf.get_width()
            right_unscaled_y = right_pixbuf.get_height()

            left_rotation = self._get_pixbuf_rotation(left_pixbuf, True)
            right_rotation = self._get_pixbuf_rotation(right_pixbuf, True)

            if left_rotation in (90, 270):
                total_width = left_unscaled_y
                total_height = left_unscaled_x
            else:
                total_width = left_unscaled_x
                total_height = left_unscaled_y

            if right_rotation in (90, 270):
                total_width += right_unscaled_y
                total_height = max(total_height, right_unscaled_x)
            else:
                total_width += right_unscaled_x
                total_height = max(total_height, right_unscaled_y)

            total_width += 2  # For the 2 px gap between images.
            scaled_width, scaled_height = self.zoom.get_zoomed_size(
                (total_width, total_height), self.get_visible_area_size())

            # Visible area size is recomputed depending on scrollbar visibility
            self._show_scrollbars((scaled_width, scaled_height),
                self.get_visible_area_size())
            area_width, area_height = self.get_visible_area_size()
            scaled_width, scaled_height = self.zoom.get_zoomed_size(
                (total_width, total_height), (area_width, area_height))

            left_pixbuf, right_pixbuf = image_tools.fit_2_in_rectangle(
                left_pixbuf, right_pixbuf, scaled_width, scaled_height,
                scale_up=True, rotation1=left_rotation,
                rotation2=right_rotation)

            if prefs['horizontal flip']:
                left_pixbuf = left_pixbuf.flip(horizontal=True)
                right_pixbuf = right_pixbuf.flip(horizontal=True)

            if prefs['vertical flip']:
                left_pixbuf = left_pixbuf.flip(horizontal=False)
                right_pixbuf = right_pixbuf.flip(horizontal=False)

            left_pixbuf = self.enhancer.enhance(left_pixbuf)
            right_pixbuf = self.enhancer.enhance(right_pixbuf)

            self.left_image.set_from_pixbuf(left_pixbuf)
            self.right_image.set_from_pixbuf(right_pixbuf)

            x_padding = (area_width - left_pixbuf.get_width() -
                right_pixbuf.get_width()) / 2
            y_padding = (area_height - max(left_pixbuf.get_height(),
                right_pixbuf.get_height())) / 2

            if left_rotation in (90, 270):
                left_scale_percent = (100.0 * left_pixbuf.get_width() /
                    left_unscaled_y)
            else:
                left_scale_percent = (100.0 * left_pixbuf.get_width() /
                    left_unscaled_x)

            if right_rotation in (90, 270):
                right_scale_percent = (100.0 * right_pixbuf.get_width() /
                    right_unscaled_y)
            else:
                right_scale_percent = (100.0 * right_pixbuf.get_width() /
                    right_unscaled_x)

            self.statusbar.set_resolution(
                (left_unscaled_x, left_unscaled_y, left_scale_percent),
                (right_unscaled_x, right_unscaled_y, right_scale_percent))

        elif not skip_pixbuf:
            pixbuf = self.imagehandler.get_pixbufs(single=True)[ 0 ]
            width, height = pixbuf.get_width(), pixbuf.get_height()

            rotation = self._get_pixbuf_rotation(pixbuf)
            if rotation in (90, 270):
                width, height = height, width

            scaled_width, scaled_height = self.zoom.get_zoomed_size(
                (width, height), self.get_visible_area_size())

            # Visible area size is recomputed depending on scrollbar visibility
            self._show_scrollbars((scaled_width, scaled_height),
                self.get_visible_area_size())
            area_width, area_height = self.get_visible_area_size()
            scaled_width, scaled_height = self.zoom.get_zoomed_size(
                (width, height), (area_width, area_height))

            pixbuf = image_tools.fit_in_rectangle(pixbuf, scaled_width,
                scaled_height, scale_up=True, rotation=rotation)

            if prefs['horizontal flip']:
                pixbuf = pixbuf.flip(horizontal=True)
            if prefs['vertical flip']:
                pixbuf = pixbuf.flip(horizontal=False)

            pixbuf = self.enhancer.enhance(pixbuf)

            self.left_image.set_from_pixbuf(pixbuf)
            self.right_image.clear()

            x_padding = (area_width - pixbuf.get_width()) / 2
            y_padding = (area_height - pixbuf.get_height()) / 2

            if rotation in (90, 270):
                scale_percent = 100.0 * pixbuf.get_width() / height
            else:
                scale_percent = 100.0 * pixbuf.get_width() / width

            self.statusbar.set_resolution((width, height,
                scale_percent))

        if prefs['smart bg'] and not skip_pixbuf:

            bg_colour = self.imagehandler.get_pixbuf_auto_background(
                    not self.displayed_double())
            self.set_bg_colour(bg_colour)

            if prefs['smart thumb bg'] and prefs['show thumbnails']:
                self.thumbnailsidebar.change_thumbnail_background_color(bg_colour)

        elif prefs['smart thumb bg'] and prefs['show thumbnails'] and not skip_pixbuf:

            bg_colour = image_tools.get_most_common_edge_colour(
                            self.left_image.get_pixbuf())

            self.thumbnailsidebar.change_thumbnail_background_color(bg_colour)

        if not skip_pixbuf:
            self._image_box.window.freeze_updates()
            self._main_layout.move(self._image_box, max(0, x_padding),
                max(0, y_padding))

            self.left_image.show()

            if self.displayed_double():
                self.right_image.show()
            else:
                self.right_image.hide()

            self._main_layout.set_size(*self._image_box.size_request())

            if scroll:
                if at_bottom:
                    self.scroll_to_fixed(horiz='endsecond', vert='bottom')
                else:
                    self.scroll_to_fixed(horiz='startfirst', vert='top')

            self._image_box.window.thaw_updates()
        else:
            # If the pixbuf for the current page(s) isn't available,
            # hide both images to clear any old pixbufs.
            self.left_image.hide()
            self.right_image.hide()

        self._update_page_information()
        self._waiting_for_redraw = False

        return False

    def _update_page_information(self):
        """ Updates the window with information that can be gathered
        even when the page pixbuf(s) aren't ready yet. """

        if self.displayed_double():
            self.statusbar.set_page_number(
                self.imagehandler.get_current_page(),
                self.imagehandler.get_number_of_pages(), double_page=True)

            left_filename, right_filename = \
                self.imagehandler.get_page_filename(double=True)

            if self.is_manga_mode:
                left_filename, right_filename = right_filename, left_filename

            self.statusbar.set_filename(left_filename + ', ' + right_filename)
        else:
            self.statusbar.set_page_number(
                self.imagehandler.get_current_page(),
                self.imagehandler.get_number_of_pages())

            self.statusbar.set_filename(self.imagehandler.get_page_filename())

        self.statusbar.set_root(self.filehandler.get_base_filename())
        self.statusbar.update()
        self.update_title()

    def _get_pixbuf_rotation(self, pixbuf, no_autorotation=False):
        """ Determines if a pixbuf must be rotated before being displayed.
        Returns the degree of rotation (0, 90, 180, 270). """
        
        width, height = pixbuf.get_width(), pixbuf.get_height()
        rotation = prefs['rotation']
        if prefs['auto rotate from exif']:
            rotation += image_tools.get_implied_rotation(pixbuf)
            rotation = rotation % 360

        if (height > width and
            not no_autorotation and
            prefs['auto rotate depending on size'] in
                (constants.AUTOROTATE_HEIGHT_90, constants.AUTOROTATE_HEIGHT_270)):

            if prefs['auto rotate depending on size'] == constants.AUTOROTATE_HEIGHT_90:
                rotation = 90
            else:
                rotation = 270
        elif (width > height and
              not no_autorotation and
              prefs['auto rotate depending on size'] in
                (constants.AUTOROTATE_WIDTH_90, constants.AUTOROTATE_WIDTH_270)):

            if prefs['auto rotate depending on size'] == constants.AUTOROTATE_WIDTH_90:
                rotation = 90
            else:
                rotation = 270

        return rotation

    def _page_available(self, page):
        """ Called whenever a new page is ready for displaying. """
        # Refresh display when currently opened page becomes available.
        if page == self.imagehandler.get_current_page() \
            or (self.displayed_double() and page == self.imagehandler.get_current_page() + 1):

            self.draw_image(False, True)

        # Use first page as application icon when opening archives.
        if (page == 1
            and self.filehandler.archive_type is not None
            and prefs['archive thumbnail as icon']):
            pixbuf = self.imagehandler.get_thumbnail(page, 48, 48)
            self.set_icon(pixbuf)

    def new_page(self, at_bottom=False):
        """Draw a *new* page correctly (as opposed to redrawing the same
        image with a new size or whatever).
        """
        if not prefs['keep transformation']:
            prefs['rotation'] = 0
            prefs['horizontal flip'] = False
            prefs['vertical flip'] = False

        self.thumbnailsidebar.update_select()

        self.draw_image(at_bottom=at_bottom, scroll=True)

    def set_page(self, num, at_bottom=False):
        if self.imagehandler.set_page(num):
            self.new_page(at_bottom=at_bottom)
            self.slideshow.update_delay()

    def next_page(self, *args):
        new_page_number = self.imagehandler.next_page()

        if new_page_number >= 1:
            self.set_page(new_page_number)

    def previous_page(self, *args):
        new_page_number = self.imagehandler.previous_page()
        if new_page_number >= 1:
            self.set_page(new_page_number, at_bottom=True)

    def first_page(self, *args):
        new_page_number = self.imagehandler.first_page()
        if new_page_number >= 1:
            self.set_page(new_page_number)

    def last_page(self, *args):
        new_page_number = self.imagehandler.last_page()
        if new_page_number >= 1:
            self.set_page(new_page_number)

    def page_select(self, *args):
        pageselect.Pageselector(self)

    def rotate_90(self, *args):
        prefs['rotation'] = (prefs['rotation'] + 90) % 360
        self.draw_image()

    def rotate_180(self, *args):
        prefs['rotation'] = (prefs['rotation'] + 180) % 360
        self.draw_image()

    def rotate_270(self, *args):
        prefs['rotation'] = (prefs['rotation'] + 270) % 360
        self.draw_image()

    def flip_horizontally(self, *args):
        prefs['horizontal flip'] = not prefs['horizontal flip']
        self.draw_image()

    def flip_vertically(self, *args):
        prefs['vertical flip'] = not prefs['vertical flip']
        self.draw_image()

    def change_double_page(self, toggleaction):
        prefs['default double page'] = toggleaction.get_active()
        self.is_double_page = toggleaction.get_active()
        self.draw_image()

    def change_manga_mode(self, toggleaction):
        prefs['default manga mode'] = toggleaction.get_active()
        self.is_manga_mode = toggleaction.get_active()
        self.draw_image()

    def change_invert_scroll(self, toggleaction):
        prefs['invert smart scroll'] = toggleaction.get_active()

    def change_fullscreen(self, toggleaction):
        self.is_fullscreen = toggleaction.get_active()
        if self.is_fullscreen:
            self.fullscreen()
            self.cursor_handler.auto_hide_on()

            if (prefs['hide all in fullscreen'] and
                not prefs['hide all']):

                self.hide_all_forced = True
                self.change_hide_all()
        else:
            self.unfullscreen()
            self.cursor_handler.auto_hide_off()

            if (prefs['hide all in fullscreen'] and
                prefs['hide all'] and
                self.hide_all_forced):

                self.change_hide_all()

            self.hide_all_forced = False

    def change_zoom_mode(self, radioaction=None, *args):
        if radioaction:
            prefs['zoom mode'] = radioaction.get_current_value()

        fitmode = zoom.FitMode.create(prefs['zoom mode'])
        fitmode.set_scale_up(prefs['stretch'])
        self.zoom.set_fit_mode(fitmode)

    def change_autorotation(self, radioaction=None, *args):
        """ Switches between automatic rotation modes, depending on which
        radiobutton is currently activated. """
        if radioaction:
            prefs['auto rotate depending on size'] = radioaction.get_current_value()

        self.draw_image()

    def change_stretch(self, toggleaction, *args):
        """ Toggles stretching small images. """
        prefs['stretch'] = toggleaction.get_active()
        self.zoom.get_fit_mode().set_scale_up(prefs['stretch'])
        self.draw_image()

    def change_toolbar_visibility(self, *args):
        prefs['show toolbar'] = not prefs['show toolbar']
        self.draw_image()

    def change_menubar_visibility(self, *args):
        prefs['show menubar'] = not prefs['show menubar']
        self.draw_image()

    def change_statusbar_visibility(self, *args):
        prefs['show statusbar'] = not prefs['show statusbar']
        self.draw_image()

    def change_scrollbar_visibility(self, *args):
        prefs['show scrollbar'] = not prefs['show scrollbar']
        self.draw_image()

    def change_thumbnails_visibility(self, *args):
        prefs['show thumbnails'] = not prefs['show thumbnails']
        self.draw_image()

    def change_hide_all(self, *args):
        prefs['hide all'] = not prefs['hide all']
        sensitive = not prefs['hide all']
        self.actiongroup.get_action('toolbar').set_sensitive(sensitive)
        self.actiongroup.get_action('menubar').set_sensitive(sensitive)
        self.actiongroup.get_action('statusbar').set_sensitive(sensitive)
        self.actiongroup.get_action('scrollbar').set_sensitive(sensitive)
        self.actiongroup.get_action('thumbnails').set_sensitive(sensitive)
        self.draw_image()

    def change_keep_transformation(self, *args):
        prefs['keep transformation'] = not prefs['keep transformation']

    def manual_zoom_in(self, *args):
        self.zoom.zoom_in()

    def manual_zoom_out(self, *args):
        self.zoom.zoom_out()

    def manual_zoom_original(self, *args):
        self.zoom.reset_zoom()

    def _show_scrollbars(self, img_size, screen_size):
        """ Enables scroll bars depending on image size
        and preferences. """

        self._vscroll.hide_all()
        self._hscroll.hide_all()

        if (prefs['show scrollbar']
            and not prefs['hide all']
            and not (self.is_fullscreen and prefs['hide all in fullscreen'])):
            if img_size[0] > screen_size[0]:
                self._hscroll.show_all()
            else:
                self._hscroll.hide_all()

            if img_size[1] > screen_size[1]:
                self._vscroll.show_all()
            else:
                self._vscroll.hide_all()

        else:
            self._vscroll.hide_all()
            self._hscroll.hide_all()

    def is_scrollable_vertically(self):
        """ Returns True when the displayed image does not fit into the display
        port vertically and must be scrolled to be viewed completely. """

        _, screen_height = self.get_visible_area_size()
        left_height = self.left_image.get_pixbuf() and \
                self.left_image.get_pixbuf().get_height() or 0
        right_height = self.right_image.get_pixbuf() and \
                self.right_image.get_pixbuf().get_height() or 0
        image_height = max(left_height, right_height)

        return image_height > screen_height

    def scroll_with_flipping(self, x, y):
        """Returns true if able to scroll without flipping to
        a new page and False otherwise."""
        return self._event_handler._scroll_with_flipping(x, y)

    def scroll(self, x, y, bound=None):
        """Scroll <x> px horizontally and <y> px vertically. If <bound> is
        'first' or 'second', we will not scroll out of the first or second
        page respectively (dependent on manga mode). The <bound> argument
        only makes sense in double page mode.

        Return True if call resulted in new adjustment values, False
        otherwise.
        """
        old_hadjust = self._hadjust.get_value()
        old_vadjust = self._vadjust.get_value()

        visible_width, visible_height = self.get_visible_area_size()

        hadjust_upper = max(0, self._hadjust.upper - visible_width)
        vadjust_upper = max(0, self._vadjust.upper - visible_height)
        hadjust_lower = 0

        if bound is not None and self.is_manga_mode:
            bound = {'first': 'second', 'second': 'first'}[bound]

        if bound == 'first':
            hadjust_upper = max(0, hadjust_upper -
                self.right_image.size_request()[0] - 2)

        elif bound == 'second':
            hadjust_lower = self.left_image.size_request()[0] + 2

        new_hadjust = old_hadjust + x
        new_vadjust = old_vadjust + y

        new_hadjust = max(hadjust_lower, new_hadjust)
        new_vadjust = max(0, new_vadjust)

        new_hadjust = min(hadjust_upper, new_hadjust)
        new_vadjust = min(vadjust_upper, new_vadjust)

        self._vadjust.set_value(new_vadjust)
        self._hadjust.set_value(new_hadjust)

        return old_vadjust != new_vadjust or old_hadjust != new_hadjust

    def scroll_to_fixed(self, horiz=None, vert=None):
        """Scroll using one of several fixed values.

        If either <horiz> or <vert> is as below, the display is scrolled as
        follows:

        horiz: 'left'        = left end of display
               'middle'      = middle of the display
               'right'       = right end of display
               'startfirst'  = start of first page
               'endfirst'    = end of first page
               'startsecond' = start of second page
               'endsecond'   = end of second page

        vert:  'top'         = top of display
               'middle'      = middle of display
               'bottom'      = bottom of display

        What is considered "start" and "end" depends on whether we are
        using manga mode or not.

        Return True if call resulted in new adjustment values.
        """
        old_hadjust = self._hadjust.get_value()
        old_vadjust = self._vadjust.get_value()
        new_vadjust = old_vadjust
        new_hadjust = old_hadjust
        visible_width, visible_height = self.get_visible_area_size()
        vadjust_upper = self._vadjust.upper - visible_height
        hadjust_upper = self._hadjust.upper - visible_width

        if vert == 'top':
            new_vadjust = 0
        elif vert == 'middle':
            new_vadjust = vadjust_upper / 2
        elif vert == 'bottom':
            new_vadjust = vadjust_upper

        if not self.displayed_double():
            horiz = {'startsecond': 'endfirst',
                     'endsecond': 'endfirst'}.get(horiz, horiz)

        # Manga transformations.
        if self.is_manga_mode and self.displayed_double() and horiz is not None:
            horiz = {'left':        'left',
                     'middle':      'middle',
                     'right':       'right',
                     'startfirst':  'endsecond',
                     'endfirst':    'startsecond',
                     'startsecond': 'endfirst',
                     'endsecond':   'startfirst'}[horiz]

        elif self.is_manga_mode and horiz is not None:
            horiz = {'left':        'left',
                     'middle':      'middle',
                     'right':       'right',
                     'startfirst':  'endfirst',
                     'endfirst':    'startfirst'}[horiz]

        if horiz == 'left':
            new_hadjust = 0
        elif horiz == 'middle':
            new_hadjust = hadjust_upper / 2
        elif horiz == 'right':
            new_hadjust = hadjust_upper
        elif horiz == 'startfirst':
            new_hadjust = 0
        elif horiz == 'endfirst':

            if self.displayed_double():
                new_hadjust = self.left_image.size_request()[0] - visible_width
            else:
                new_hadjust = hadjust_upper

        elif horiz == 'startsecond':
            new_hadjust = self.left_image.size_request()[0] + 2
        elif horiz == 'endsecond':
            new_hadjust = hadjust_upper

        new_hadjust = max(0, new_hadjust)
        new_vadjust = max(0, new_vadjust)
        new_hadjust = min(hadjust_upper, new_hadjust)
        new_vadjust = min(vadjust_upper, new_vadjust)
        self._vadjust.set_value(new_vadjust)
        self._hadjust.set_value(new_hadjust)

        return old_vadjust != new_vadjust or old_hadjust != new_hadjust

    def is_on_first_page(self):
        """Return True if we are currently viewing the first page, i.e. if we
        are scrolled as far to the left as possible, or if only the left page
        is visible on the main layout. In manga mode it is the other way
        around.
        """
        if not self.displayed_double():
            return True
        width, height = self.get_visible_area_size()
        if self.is_manga_mode:
            return (self._hadjust.get_value() >= self._hadjust.upper - width or
                self._hadjust.get_value() > self.left_image.size_request()[0])
        else:
            return (self._hadjust.get_value() == 0 or
                self._hadjust.get_value() + width <=
                self.left_image.size_request()[0])

    def clear(self):
        """Clear the currently displayed data (i.e. "close" the file)."""
        self.left_image.clear()
        self.right_image.clear()
        self.set_title(constants.APPNAME)
        self.statusbar.set_message('')
        self.set_bg_colour(prefs['bg colour'])
        enhance_dialog.clear_histogram()

    def displayed_double(self):
        """Return True if two pages are currently displayed."""
        return (self.is_double_page and not self.is_virtual_double_page and
            self.imagehandler.get_current_page() !=
            self.imagehandler.get_number_of_pages())

    def get_visible_area_size(self):
        """Return a 2-tuple with the width and height of the visible part
        of the main layout area.
        """
        width, height = self.get_size()

        if not prefs['hide all']:

            if prefs['show toolbar']:
                height -= self.toolbar.size_request()[1]

            if prefs['show statusbar']:
                height -= self.statusbar.size_request()[1]

            if prefs['show thumbnails']:
                width -= self.thumbnailsidebar.get_width()

            if prefs['show menubar']:
                height -= self.menubar.size_request()[1]

            if prefs['show scrollbar']:

                if self._vscroll.get_visible():
                    width -= self._vscroll.size_request()[0]

                if self._hscroll.get_visible():
                    height -= self._hscroll.size_request()[1]

        return width, height

    def get_layout_pointer_position(self):
        """Return a 2-tuple with the x and y coordinates of the pointer
        on the main layout area, relative to the layout.
        """
        x, y = self._main_layout.get_pointer()
        x += self._hadjust.get_value()
        y += self._vadjust.get_value()

        return (x, y)

    def set_cursor(self, mode):
        """Set the cursor on the main layout area to <mode>. You should
        probably use the cursor_handler instead of using this method
        directly.
        """
        self._main_layout.window.set_cursor(mode)
        return False

    def update_title(self):
        """Set the title acording to current state."""
        if self.displayed_double():
            title = i18n.to_unicode('[%d,%d / %d]  %s' % (
                self.imagehandler.get_current_page(),
                self.imagehandler.get_current_page() + 1,
                self.imagehandler.get_number_of_pages(),
                self.imagehandler.get_pretty_current_filename()))
        else:
            title = i18n.to_unicode('[%d / %d]  %s' % (
                self.imagehandler.get_current_page(),
                self.imagehandler.get_number_of_pages(),
                self.imagehandler.get_pretty_current_filename()))

        if self.slideshow.is_running():
            title = '[%s] %s' % (_('SLIDESHOW'), title)

        self.set_title(title)

    def set_bg_colour(self, colour):
        """Set the background colour to <colour>. Colour is a sequence in the
        format (r, g, b). Values are 16-bit.
        """
        self._main_layout.modify_bg(gtk.STATE_NORMAL,
            gtk.gdk.colormap_get_system().alloc_color(gtk.gdk.Color(
            colour[0], colour[1], colour[2]), False, True))

        if prefs['thumbnail bg uses main colour']:
            self.thumbnailsidebar.change_thumbnail_background_color(prefs['bg colour'])

    def _display_active_widgets(self):
        """Hide and/or show main window widgets depending on the current
        state.
        """

        if not prefs['hide all']:

            if prefs['show toolbar']:
                self.toolbar.show_all()
            else:
                self.toolbar.hide_all()

            if prefs['show statusbar']:
                self.statusbar.show_all()
            else:
                self.statusbar.hide_all()

            if prefs['show menubar']:
                self.menubar.show_all()
            else:
                self.menubar.hide_all()

            if prefs['show thumbnails'] and self.filehandler.file_loaded:
                self.thumbnailsidebar.show()
            else:
                self.thumbnailsidebar.hide()

        else:
            self.toolbar.hide_all()
            self.menubar.hide_all()
            self.statusbar.hide_all()
            self.thumbnailsidebar.hide()
            self._vscroll.hide_all()
            self._hscroll.hide_all()

    def extract_page(self, *args):
        """ Derive some sensible filename (archive name + _ + filename should do) and offer
        the user the choice to save the current page with the selected name. """
        if self.filehandler.archive_type is not None:
            archive_name = self.filehandler.get_pretty_current_filename()
            file_name = self.imagehandler.get_path_to_page()
            suggested_name = os.path.splitext(archive_name)[0] + \
                u'_' + os.path.split(file_name)[-1]
        else:
            suggested_name = os.path.split(self.imagehandler.get_path_to_page())[-1]

        save_dialog = gtk.FileChooserDialog(_('Save page as'), self,
            gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
            gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        save_dialog.set_current_name(suggested_name.encode('utf-8'))

        if save_dialog.run() == gtk.RESPONSE_ACCEPT and save_dialog.get_filename():
            shutil.copy(self.imagehandler.get_path_to_page(),
                save_dialog.get_filename().decode('utf-8'))

        save_dialog.destroy()

    def delete(self, *args):
        """ The currently opened file/archive will be deleted after showing
        a confirmation dialog. """

        current_file = self.imagehandler.get_real_path()
        dialog = message_dialog.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                gtk.BUTTONS_NONE)
        dialog.set_should_remember_choice('delete-opend-file', (gtk.RESPONSE_OK,))
        dialog.set_text(
                _('Delete "%s"?') % os.path.basename(current_file),
                _('The file will be deleted from your harddisk.'))
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(gtk.STOCK_DELETE, gtk.RESPONSE_OK)
        dialog.set_default_response(gtk.RESPONSE_OK)
        result = dialog.run()

        if result == gtk.RESPONSE_OK:
            # Go to next page/archive, and delete current file
            if self.filehandler.archive_type is not None:
                self.filehandler.last_read_page.clear_page(current_file)

                next_opened = self.filehandler._open_next_archive()
                if not next_opened:
                    next_opened = self.filehandler._open_previous_archive()
                if not next_opened:
                    self.filehandler.close_file()

                if os.path.isfile(current_file):
                    os.unlink(current_file)
            else:
                if self.imagehandler.get_number_of_pages() > 1:
                    # Open the next/previous file
                    if self.imagehandler.get_current_page() >= self.imagehandler.get_number_of_pages():
                        self.previous_page()
                    else:
                        self.next_page()
                    # Unlink the desired file
                    if os.path.isfile(current_file):
                        os.unlink(current_file)
                    # Refresh the directory
                    self.filehandler.refresh_file()
                else:
                    self.filehandler.close_file()
                    if os.path.isfile(current_file):
                        os.unlink(current_file)

    def show_info_panel(self):
        """ Shows an OSD displaying information about the current page. """

        if not self.filehandler.file_loaded:
            return

        filename = self.imagehandler.get_pretty_current_filename().encode('utf-8')
        page_text = '%s %s' % (_('Page'), self.statusbar.get_page_number())
        if self.statusbar.get_file_number():
            page_text += ' ' + self.statusbar.get_file_number()

        self.osd.show(filename + "\n\n" + page_text)

    def minimize(self, *args):
        """ Minimizes the MComix window. """
        self.iconify()

    def write_config_files(self):

        self.filehandler.write_fileinfo_file()
        preferences.write_preferences_file()
        bookmark_backend.BookmarksStore.write_bookmarks_file()

        # Write keyboard accelerator map
        gtk.accel_map_save(constants.KEYBINDINGS_PATH)
        keybindings.keybinding_manager().save()

    def save_and_terminate_program(self, *args):
        prefs['previous quit was quit and save'] = True

        self.terminate_program(save_current_file=True)

    def close_program(self, *args):
        self.terminate_program(save_current_file=False)

    def terminate_program(self, save_current_file=False):
        """Run clean-up tasks and exit the program."""

        self.hide()

        if gtk.main_level() > 0:
            gtk.main_quit()

        if prefs['auto load last file'] and self.filehandler.file_loaded:
            prefs['path to last file'] = self.imagehandler.get_real_path()
            prefs['page of last file'] = self.imagehandler.get_current_page()

        else:
            prefs['path to last file'] = ''
            prefs['page of last file'] = 1

        if prefs['hide all'] and self.hide_all_forced and self.fullscreen:
            prefs['hide all'] = False

        self.write_config_files()

        self.filehandler.cleanup()
        self.imagehandler.cleanup()
        self.thumbnailsidebar.clear()
        backend.LibraryBackend().close()

        # This hack is to avoid Python issue #1856.
        for thread in threading.enumerate():
            if thread is not threading.currentThread():
                thread.join()

#: Main window instance
__main_window = None


def main_window():
    """ Returns the global main window instance. """
    return __main_window


def set_main_window(window):
    global __main_window
    __main_window = window

# vim: expandtab:sw=4:ts=4

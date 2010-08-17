"""preferences.py - Preference handler."""

import os
import cPickle

import gtk
import pango

import constants
import labels

ZOOM_MODE_BEST = 0
ZOOM_MODE_WIDTH = 1
ZOOM_MODE_HEIGHT = 2
ZOOM_MODE_MANUAL = 3

# All the preferences are stored here.
prefs = {
    'comment extensions': ['txt', 'nfo'],
    'auto load last file': False,
    'page of last file': 1,
    'path to last file': '',
    'auto open next archive': True,
    'bg colour': (5000, 5000, 5000),
    'checkered bg for transparent images': True,
    'cache': True,
    'stretch': False,
    'default double page': False,
    'default fullscreen': False,
    'default zoom mode': ZOOM_MODE_BEST,
    'default manga mode': False,
    'lens magnification': 2,
    'lens size': 200,
    'no double page for wide images': False,
    'double step in double page mode': True,
    'show page numbers on thumbnails': True,
    'thumbnail size': 80,
    'create thumbnails': True,
    'slideshow delay': 3000,
    'smart space scroll': True,
    'flip with wheel': False,
    'smart bg': False,
    'store recent file info': True,
    'hide all': False,
    'hide all in fullscreen': True,
    'stored hide all values': (True, True, True, True, True),
    'path of last browsed in filechooser': constants.HOME_DIR,
    'last filter in main filechooser': 0,
    'last filter in library filechooser': 1,
    'show menubar': True,
    'show scrollbar': True,
    'show statusbar': True,
    'show toolbar': True,
    'show thumbnails': True,
    'rotation': 0,
    'auto rotate from exif': True,
    'vertical flip': False,
    'horizontal flip': False,
    'keep transformation': False,
    'window height': gtk.gdk.screen_get_default().get_height() * 3 // 4,
    'window width': min(gtk.gdk.screen_get_default().get_width() * 3 // 4,
                        gtk.gdk.screen_get_default().get_height() * 5 // 8),
    'library cover size': 128,
    'auto add books into collections': True,
    'last library collection': None,
    'lib window height': gtk.gdk.screen_get_default().get_height() * 3 // 4,
    'lib window width': gtk.gdk.screen_get_default().get_width() * 3 // 4
}

_config_path = os.path.join(constants.CONFIG_DIR, 'preferences.pickle')
_dialog = None


class _PreferencesDialog(gtk.Dialog):
    
    """The preferences dialog where most (but not all) settings that are
    saved between sessions are presented to the user.
    """

    def __init__(self, window):
        self._window = window
        gtk.Dialog.__init__(self, _('Preferences'), window, 0,
            (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))
        self.connect('response', self._response)
        self.set_has_separator(False)
        self.set_resizable(True)
        self.set_default_response(gtk.RESPONSE_CLOSE)
        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook)
        self.set_border_width(4)
        notebook.set_border_width(6)
        
        # ----------------------------------------------------------------
        # The "Appearance" tab.
        # ----------------------------------------------------------------
        page = _PreferencePage(80)
        page.new_section(_('Background'))
        fixed_bg_button = gtk.RadioButton(None, '%s:' %
            _('Use this colour as background'))
        fixed_bg_button.set_tooltip_text(
            _('Always use this selected colour as the background colour.'))
        color_button = gtk.ColorButton(gtk.gdk.Color(*prefs['bg colour']))
        color_button.connect('color_set', self._color_button_cb)
        page.add_row(fixed_bg_button, color_button)
        dynamic_bg_button = gtk.RadioButton(fixed_bg_button,
            _('Use dynamic background colour.'))
        dynamic_bg_button.set_active(prefs['smart bg'])
        dynamic_bg_button.connect('toggled', self._check_button_cb, 'smart bg')
        dynamic_bg_button.set_tooltip_text(
            _('Automatically pick a background colour that fits the viewed image.'))
        page.add_row(dynamic_bg_button)

        page.new_section(_('Thumbnails'))
        label = gtk.Label('%s:' % _('Thumbnail size (in pixels)'))
        adjustment = gtk.Adjustment(prefs['thumbnail size'], 20, 128, 1, 10)
        thumb_size_spinner = gtk.SpinButton(adjustment)
        thumb_size_spinner.connect('value_changed', self._spinner_cb,
            'thumbnail size')
        page.add_row(label, thumb_size_spinner)
        thumb_number_button = gtk.CheckButton(
            _('Show page numbers on thumbnails.'))
        thumb_number_button.set_active(
            prefs['show page numbers on thumbnails'])
        thumb_number_button.connect('toggled', self._check_button_cb,
            'show page numbers on thumbnails')
        page.add_row(thumb_number_button)
        
        page.new_section(_('Magnifying Glass'))
        label = gtk.Label('%s:' % _('Magnifying glass size (in pixels)'))
        adjustment = gtk.Adjustment(prefs['lens size'], 50, 400, 1, 10)
        glass_size_spinner = gtk.SpinButton(adjustment)
        glass_size_spinner.connect('value_changed', self._spinner_cb,
            'lens size')
        glass_size_spinner.set_tooltip_text(
            _('Set the size of the magnifying glass. It is a square with a side of this many pixels.'))
        page.add_row(label, glass_size_spinner)
        label = gtk.Label('%s:' % _('Magnification factor'))
        adjustment = gtk.Adjustment(prefs['lens magnification'], 1.1, 10.0,
            0.1, 1.0)
        glass_magnification_spinner = gtk.SpinButton(adjustment, digits=1)
        glass_magnification_spinner.connect('value_changed', self._spinner_cb,
            'lens magnification')
        glass_magnification_spinner.set_tooltip_text(
            _('Set the magnification factor of the magnifying glass.'))
        page.add_row(label, glass_magnification_spinner)

        page.new_section(_('Image scaling'))
        stretch_button = gtk.CheckButton(_('Stretch small images.'))
        stretch_button.set_active(prefs['stretch'])
        stretch_button.connect('toggled', self._check_button_cb, 'stretch')
        stretch_button.set_tooltip_text(
            _('Stretch images to a size that is larger than their original size if the current zoom mode requests it. If this preference is unset, images are never scaled to be larger than their original size.'))
        page.add_row(stretch_button)

        page.new_section(_('Transparency'))
        checkered_bg_button = gtk.CheckButton(
            _('Use checkered background for transparent images.'))
        checkered_bg_button.set_active(
            prefs['checkered bg for transparent images'])
        checkered_bg_button.connect('toggled', self._check_button_cb,
            'checkered bg for transparent images')
        checkered_bg_button.set_tooltip_text(
            _('Use a grey checkered background for transparent images. If this preference is unset, the background is plain white instead.'))
        page.add_row(checkered_bg_button)
        notebook.append_page(page, gtk.Label(_('Appearance')))
        
        # ----------------------------------------------------------------
        # The "Behaviour" tab.
        # ----------------------------------------------------------------
        page = _PreferencePage(150)
        page.new_section(_('Scroll'))
        smart_space_button = gtk.CheckButton(
            _('Use smart space key scrolling.'))
        smart_space_button.set_active(prefs['smart space scroll'])
        smart_space_button.connect('toggled', self._check_button_cb,
            'smart space scroll')
        smart_space_button.set_tooltip_text(
            _('Use smart scrolling with the space key. Normally the space key scrolls only right down (or up when shift is pressed), but with this preference set it also scrolls sideways and so tries to follow the natural reading order of the comic book.'))
        page.add_row(smart_space_button)

        flip_with_wheel_button = gtk.CheckButton(
            _('Flip pages when scrolling off the edges of the page.'))
        flip_with_wheel_button.set_active(prefs['flip with wheel'])
        flip_with_wheel_button.connect('toggled', self._check_button_cb,
            'flip with wheel')
        flip_with_wheel_button.set_tooltip_text(
            _('Flip pages when scrolling "off the page" with the scroll wheel or with the arrow keys. It takes three consecutive "steps" with the scroll wheel or the arrow keys for the pages to be flipped.'))
        page.add_row(flip_with_wheel_button)

        page.new_section(_('Double page mode'))
        step_length_button = gtk.CheckButton(
            _('Flip two pages in double page mode.'))
        step_length_button.set_active(prefs['double step in double page mode'])
        step_length_button.connect('toggled', self._check_button_cb,
            'double step in double page mode')
        step_length_button.set_tooltip_text(
            _('Flip two pages, instead of one, each time we flip pages in double page mode.'))
        page.add_row(step_length_button)
        virtual_double_button = gtk.CheckButton(
            _('Show only one wide image in double page mode.'))
        virtual_double_button.set_active(
            prefs['no double page for wide images'])
        virtual_double_button.connect('toggled', self._check_button_cb,
            'no double page for wide images')
        virtual_double_button.set_tooltip_text(
            _("Display only one image in double page mode, if the image's width exceeds its height. The result of this is that scans that span two pages are displayed properly (i.e. alone) also in double page mode."))
        page.add_row(virtual_double_button)

        page.new_section(_('Files'))
        auto_open_next_button = gtk.CheckButton(
            _('Automatically open the next archive.'))
        auto_open_next_button.set_active(prefs['auto open next archive'])
        auto_open_next_button.connect('toggled', self._check_button_cb,
            'auto open next archive')
        auto_open_next_button.set_tooltip_text(
            _('Automatically open the next archive in the directory when flipping past the last page, or the previous archive when flipping past the first page.'))
        page.add_row(auto_open_next_button)
        auto_open_last_button = gtk.CheckButton(
            _('Automatically open the last viewed file on startup.'))
        auto_open_last_button.set_active(prefs['auto load last file'])
        auto_open_last_button.connect('toggled', self._check_button_cb,
            'auto load last file')
        auto_open_last_button.set_tooltip_text(
            _('Automatically open, on startup, the file that was open when Comix was last closed.'))
        page.add_row(auto_open_last_button)
        store_recent_button = gtk.CheckButton(
            _('Store information about recently opened files.'))
        store_recent_button.set_active(prefs['store recent file info'])
        store_recent_button.connect('toggled', self._check_button_cb,
            'store recent file info')
        store_recent_button.set_tooltip_text(
            _('Add information about all files opened from within Comix to the shared recent files list.'))
        page.add_row(store_recent_button)
        create_thumbs_button = gtk.CheckButton(
            _('Store thumbnails for opened files.'))
        create_thumbs_button.set_active(prefs['create thumbnails'])
        create_thumbs_button.connect('toggled', self._check_button_cb,
            'create thumbnails')
        create_thumbs_button.set_tooltip_text(
            _('Store thumbnails for opened files according to the freedesktop.org specification. These thumbnails are shared by many other applications, such as most file managers.'))
        page.add_row(create_thumbs_button)

        page.new_section(_('Cache'))
        cache_button = gtk.CheckButton(_('Use a cache to speed up browsing.'))
        cache_button.set_active(prefs['cache'])
        cache_button.connect('toggled', self._check_button_cb, 'cache')
        cache_button.set_tooltip_text(
            _('Cache the images that are next to the currently viewed image in order to speed up browsing. Since the speed improvements are quite big, it is recommended that you have this preference set, unless you are running short on free RAM.'))
        page.add_row(cache_button)
        notebook.append_page(page, gtk.Label(_('Behaviour')))

        # ----------------------------------------------------------------
        # The "Display" tab.
        # ----------------------------------------------------------------
        page = _PreferencePage(180)
        page.new_section(_('Default modes'))
        double_page_button = gtk.CheckButton(
            _('Use double page mode by default.'))
        double_page_button.set_active(prefs['default double page'])
        double_page_button.connect('toggled', self._check_button_cb,
            'default double page')
        page.add_row(double_page_button)
        fullscreen_button = gtk.CheckButton(_('Use fullscreen by default.'))
        fullscreen_button.set_active(prefs['default fullscreen'])
        fullscreen_button.connect('toggled', self._check_button_cb,
            'default fullscreen')
        page.add_row(fullscreen_button)
        manga_button = gtk.CheckButton(_('Use manga mode by default.'))
        manga_button.set_active(prefs['default manga mode'])
        manga_button.connect('toggled', self._check_button_cb,
            'default manga mode')
        page.add_row(manga_button)
        label = gtk.Label('%s:' % _('Default zoom mode'))
        zoom_combo = gtk.combo_box_new_text()
        zoom_combo.append_text(_('Best fit mode'))
        zoom_combo.append_text(_('Fit width mode'))
        zoom_combo.append_text(_('Fit height mode'))
        zoom_combo.append_text(_('Manual zoom mode'))
        # Change this if the combobox entries are reordered.
        zoom_combo.set_active(prefs['default zoom mode']) 
        zoom_combo.connect('changed', self._combo_box_cb)
        page.add_row(label, zoom_combo)

        page.new_section(_('Fullscreen'))
        hide_in_fullscreen_button = gtk.CheckButton(
            _('Automatically hide all toolbars in fullscreen.'))
        hide_in_fullscreen_button.set_active(prefs['hide all in fullscreen'])
        hide_in_fullscreen_button.connect('toggled', self._check_button_cb,
            'hide all in fullscreen')
        page.add_row(hide_in_fullscreen_button)

        page.new_section(_('Slideshow'))
        label = gtk.Label('%s:' % _('Slideshow delay (in seconds)'))
        adjustment = gtk.Adjustment(prefs['slideshow delay'] / 1000.0,
            0.5, 3600.0, 0.1, 1)
        delay_spinner = gtk.SpinButton(adjustment, digits=1)
        delay_spinner.connect('value_changed', self._spinner_cb,
            'slideshow delay')
        page.add_row(label, delay_spinner)

        page.new_section(_('Comments'))
        label = gtk.Label('%s:' % _('Comment extensions'))
        extensions_entry = gtk.Entry()
        extensions_entry.set_text(', '.join(prefs['comment extensions']))
        extensions_entry.connect('activate', self._entry_cb)
        extensions_entry.connect('focus_out_event', self._entry_cb)
        extensions_entry.set_tooltip_text(
            _('Treat all files found within archives, that have one of these file endings, as comments.'))
        page.add_row(label, extensions_entry)

        page.new_section(_('Rotation'))
        auto_rotate_button = gtk.CheckButton(
            _('Automatically rotate images according to their metadata.'))
        auto_rotate_button.set_active(prefs['auto rotate from exif'])
        auto_rotate_button.connect('toggled', self._check_button_cb,
            'auto rotate from exif')
        auto_rotate_button.set_tooltip_text(
            _('Automatically rotate images when an orientation is specified in the image metadata, such as in an Exif tag.'))
        page.add_row(auto_rotate_button)
        notebook.append_page(page, gtk.Label(_('Display')))
        self.show_all()

    def _check_button_cb(self, button, preference):
        """Callback for all checkbutton-type preferences."""
        prefs[preference] = button.get_active()
        if preference == 'smart bg':
            if not prefs[preference]:
                self._window.set_bg_colour(prefs['bg colour'])
            else:
                self._window.draw_image(scroll=False)
        elif preference in ('stretch', 'checkered bg for transparent images',
          'no double page for wide images', 'auto rotate from exif'):
            self._window.draw_image(scroll=False)
        elif (preference == 'hide all in fullscreen' and
          self._window.is_fullscreen):
            self._window.draw_image(scroll=False)
        elif preference == 'show page numbers on thumbnails':
            self._window.thumbnailsidebar.clear()
            self._window.thumbnailsidebar.load_thumbnails()

    def _color_button_cb(self, colorbutton):
        """Callback for the background colour selection button."""
        colour = colorbutton.get_color()
        prefs['bg colour'] = colour.red, colour.green, colour.blue
        if not prefs['smart bg'] or not self._window.file_handler.file_loaded:
            self._window.set_bg_colour(prefs['bg colour'])

    def _spinner_cb(self, spinbutton, preference):
        """Callback for spinner-type preferences."""
        value = spinbutton.get_value()
        if preference == 'lens size':
            prefs[preference] = int(value)
        elif preference == 'lens magnification':
            prefs[preference] = value
        elif preference == 'slideshow delay':
            prefs[preference] = int(value * 1000)
            self._window.slideshow.update_delay()
        elif preference == 'thumbnail size':
            prefs[preference] = int(value)
            self._window.thumbnailsidebar.resize()
            self._window.draw_image(scroll=False)

    def _combo_box_cb(self, combobox):
        """Callback for combobox-type preferences."""
        zoom_mode = combobox.get_active()
        prefs['default zoom mode'] = zoom_mode

    def _entry_cb(self, entry, event=None):
        """Callback for entry-type preferences."""
        text = entry.get_text()
        extensions = [e.strip() for e in text.split(',')]
        prefs['comment extensions'] = [e for e in extensions if e]
        self._window.file_handler.update_comment_extensions()

    def _response(self, dialog, response):
        _close_dialog()


class _PreferencePage(gtk.VBox):
    
    """The _PreferencePage is a conveniece class for making one "page"
    in a preferences-style dialog that contains one or more
    _PreferenceSections.
    """
    
    def __init__(self, right_column_width):
        """Create a new page where any possible right columns have the
        width request <right_column_width>.
        """
        gtk.VBox.__init__(self, False, 12)
        self.set_border_width(12)
        self._right_column_width = right_column_width
        self._section = None
    
    def new_section(self, header):
        """Start a new section in the page, with the header text from
        <header>.
        """
        self._section = _PreferenceSection(header, self._right_column_width)
        self.pack_start(self._section, False, False)

    def add_row(self, left_item, right_item=None):
        """Add a row to the page (in the latest section), containing one
        or two items. If the left item is a label it is automatically
        aligned properly.
        """
        if isinstance(left_item, gtk.Label):
            left_item.set_alignment(0, 0.5)
        if right_item is None:
            self._section.contentbox.pack_start(left_item)
        else:
            left_box, right_box = self._section.new_split_vboxes()
            left_box.pack_start(left_item)
            right_box.pack_start(right_item)


class _PreferenceSection(gtk.VBox):
    
    """The _PreferenceSection is a convenience class for making one
    "section" of a preference-style dialog, e.g. it has a bold header
    and a number of rows which are indented with respect to that header.
    """
    
    def __init__(self, header, right_column_width=150):
        """Contruct a new section with the header set to the text in
        <header>, and the width request of the (possible) right columns
        set to that of <right_column_width>.
        """
        gtk.VBox.__init__(self, False, 0)
        self._right_column_width = right_column_width
        self.contentbox = gtk.VBox(False, 6)
        label = labels.BoldLabel(header)
        label.set_alignment(0, 0.5)
        hbox = gtk.HBox(False, 0)
        hbox.pack_start(gtk.HBox(), False, False, 6)
        hbox.pack_start(self.contentbox)
        self.pack_start(label, False, False)
        self.pack_start(hbox, False, False, 6)

    def new_split_vboxes(self):
        """Return two new VBoxes that are automatically put in the section
        after the previously added items. The right one has a width request
        equal to the right_column_width value passed to the class contructor,
        in order to make it easy for  all "right column items" in a page to
        line up nicely.
        """
        left_box = gtk.VBox(False, 6)
        right_box = gtk.VBox(False, 6)
        right_box.set_size_request(self._right_column_width, -1)
        hbox = gtk.HBox(False, 12)
        hbox.pack_start(left_box)
        hbox.pack_start(right_box, False, False)
        self.contentbox.pack_start(hbox)
        return left_box, right_box


def open_dialog(action, window):
    global _dialog
    if _dialog is None:
        _dialog = _PreferencesDialog(window)
    else:
        _dialog.present()


def _close_dialog(*args):
    global _dialog
    if _dialog is not None:
        _dialog.destroy()
        _dialog = None


def read_preferences_file():
    """Read preferences data from disk."""
    if os.path.isfile(_config_path):
        config = None
        try:
            config = open(_config_path, 'rb')
            version = cPickle.load(config)
            old_prefs = cPickle.load(config)
            config.close()
        except Exception:
            print '! Corrupt preferences file "%s", deleting...' % _config_path
            if config is not None:
                config.close()
            os.remove(_config_path)
        else:
            for key in old_prefs:
                if key in prefs:
                    prefs[key] = old_prefs[key]


def write_preferences_file():
    """Write preference data to disk."""
    config = open(_config_path, 'wb')
    cPickle.dump(constants.VERSION, config, cPickle.HIGHEST_PROTOCOL)
    cPickle.dump(prefs, config, cPickle.HIGHEST_PROTOCOL)
    config.close()

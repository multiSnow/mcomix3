"""preferences_dialog.py - Preferences dialog."""

import operator
import gtk
import gobject

from mcomix.preferences import prefs
from mcomix import preferences_page
from mcomix import image_tools
from mcomix import constants
from mcomix import message_dialog

_dialog = None

class _PreferencesDialog(gtk.Dialog):

    """The preferences dialog where most (but not all) settings that are
    saved between sessions are presented to the user.
    """

    def __init__(self, window):
        gtk.Dialog.__init__(self, _('Preferences'), window, gtk.DIALOG_MODAL)

        self.reset_button = reset = self.add_button(_('Clear dialog choices'), constants.RESPONSE_REVERT_TO_DEFAULT)
        reset.set_tooltip_text(_('Clears all dialog choices that you have previously chosen not to be asked again.'))
        reset.set_sensitive(len(prefs['stored dialog choices']) > 0)
        self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)

        self._window = window
        self.set_has_separator(False)
        self.set_resizable(True)
        self.set_default_response(gtk.RESPONSE_CLOSE)

        self.connect('response', self._response)

        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook)
        self.set_border_width(4)
        notebook.set_border_width(6)

        appearance = self._init_appearance_tab()
        notebook.append_page(appearance, gtk.Label(_('Appearance')))
        behaviour = self._init_behaviour_tab()
        notebook.append_page(behaviour, gtk.Label(_('Behaviour')))
        display = self._init_display_tab()
        notebook.append_page(display, gtk.Label(_('Display')))
        advanced = self._init_advanced_tab()
        notebook.append_page(advanced, gtk.Label(_('Advanced')))

        self.show_all()

    def _init_appearance_tab(self):
        # ----------------------------------------------------------------
        # The "Appearance" tab.
        # ----------------------------------------------------------------
        page = preferences_page._PreferencePage(80)
        page.new_section(_('Background'))

        fixed_bg_button = gtk.RadioButton(None,
            _('Use this colour as background:'))
        fixed_bg_button.set_tooltip_text(
            _('Always use this selected colour as the background colour.'))
        fixed_bg_button.connect('toggled', self._check_button_cb, 'color box bg')
        bg_color_button = gtk.ColorButton(gtk.gdk.Color(*prefs['bg colour']))
        bg_color_button.connect('color_set', self._color_button_cb, 'bg colour')

        page.add_row(fixed_bg_button, bg_color_button)

        dynamic_bg_button = gtk.RadioButton(fixed_bg_button,
            _('Use dynamic background colour'))
        dynamic_bg_button.set_active(prefs['smart bg'])
        dynamic_bg_button.connect('toggled', self._check_button_cb, 'smart bg')
        dynamic_bg_button.set_tooltip_text(
            _('Automatically pick a background colour that fits the viewed image.'))

        page.add_row(dynamic_bg_button)

        page.new_section(_('Thumbnails'))

        thumb_fixed_bg_button = gtk.RadioButton(None,
            _('Use this colour as the thumbnail background:'))
        thumb_fixed_bg_button.set_tooltip_text(
            _('Always use this selected colour as the thumbnail background colour.'))
        thumb_fixed_bg_button.connect('toggled', self._check_button_cb, 'color box thumb bg')
        thumb_bg_color_button = gtk.ColorButton(gtk.gdk.Color(*prefs['thumb bg colour']))
        thumb_bg_color_button.connect('color_set', self._color_button_cb, 'thumb bg colour')

        page.add_row(thumb_fixed_bg_button, thumb_bg_color_button)

        thumb_dynamic_bg_button = gtk.RadioButton(thumb_fixed_bg_button,
            _('Use dynamic background colour'))
        thumb_dynamic_bg_button.set_active(prefs['smart thumb bg'])
        thumb_dynamic_bg_button.set_tooltip_text(
            _('Automatically use the colour that fits the viewed image for the thumbnail background.'))
        thumb_dynamic_bg_button.connect('toggled', self._check_button_cb, 'smart thumb bg')

        page.add_row(thumb_dynamic_bg_button)

        thumb_number_button = gtk.CheckButton(
            _('Show page numbers on thumbnails'))
        thumb_number_button.set_active(
            prefs['show page numbers on thumbnails'])
        thumb_number_button.connect('toggled', self._check_button_cb,
            'show page numbers on thumbnails')
        page.add_row(thumb_number_button)

        thumb_as_preview_icon = gtk.CheckButton(
            _('Use archive thumbnail as application icon'))
        thumb_as_preview_icon.set_tooltip_text(
            _('By enabling this setting, the first page of a book will be used as application icon instead of the standard icon.'))
        thumb_as_preview_icon.set_active(
            prefs['archive thumbnail as icon'])
        thumb_as_preview_icon.connect('toggled', self._check_button_cb,
            'archive thumbnail as icon')
        page.add_row(thumb_as_preview_icon)

        label = gtk.Label(_('Thumbnail size (in pixels):'))
        adjustment = gtk.Adjustment(prefs['thumbnail size'], 20, 500, 1, 10)
        thumb_size_spinner = gtk.SpinButton(adjustment)
        thumb_size_spinner.connect('value_changed', self._spinner_cb,
            'thumbnail size')
        page.add_row(label, thumb_size_spinner)

        page.new_section(_('Transparency'))
        checkered_bg_button = gtk.CheckButton(
            _('Use checkered background for transparent images'))
        checkered_bg_button.set_active(
            prefs['checkered bg for transparent images'])
        checkered_bg_button.connect('toggled', self._check_button_cb,
            'checkered bg for transparent images')
        checkered_bg_button.set_tooltip_text(
            _('Use a grey checkered background for transparent images. If this preference is unset, the background is plain white instead.'))
        page.add_row(checkered_bg_button)

        return page

    def _init_behaviour_tab(self):
        # ----------------------------------------------------------------
        # The "Behaviour" tab.
        # ----------------------------------------------------------------
        page = preferences_page._PreferencePage(None)
        page.new_section(_('Scroll'))
        smart_space_button = gtk.CheckButton(
            _('Use smart space key scrolling'))
        smart_space_button.set_active(prefs['smart space scroll'])
        smart_space_button.connect('toggled', self._check_button_cb,
            'smart space scroll')
        smart_space_button.set_tooltip_text(
            _('Use smart scrolling with the space key. Normally the space key scrolls only right down (or up when shift is pressed), but with this preference set it also scrolls sideways and so tries to follow the natural reading order of the comic book.'))
        page.add_row(smart_space_button)

        flip_with_wheel_button = gtk.CheckButton(
            _('Flip pages when scrolling off the edges of the page'))
        flip_with_wheel_button.set_active(prefs['flip with wheel'])
        flip_with_wheel_button.connect('toggled', self._check_button_cb,
            'flip with wheel')
        flip_with_wheel_button.set_tooltip_text(
            _('Flip pages when scrolling "off the page" with the scroll wheel or with the arrow keys. It takes n consecutive "steps" with the scroll wheel or the arrow keys for the pages to be flipped.'))
        page.add_row(flip_with_wheel_button)

        auto_open_next_button = gtk.CheckButton(
            _('Automatically open the next archive'))
        auto_open_next_button.set_active(prefs['auto open next archive'])
        auto_open_next_button.connect('toggled', self._check_button_cb,
            'auto open next archive')
        auto_open_next_button.set_tooltip_text(
            _('Automatically open the next archive in the directory when flipping past the last page, or the previous archive when flipping past the first page.'))
        page.add_row(auto_open_next_button)

        auto_open_dir_button = gtk.CheckButton(
            _('Automatically open next directory'))
        auto_open_dir_button.set_active(prefs['auto open next directory'])
        auto_open_dir_button.connect('toggled', self._check_button_cb,
            'auto open next directory')
        auto_open_dir_button.set_tooltip_text(
            _('Automatically open the first file in the next sibling directory when flipping past the last page of the last file in a directory, or the previous directory when flipping past the first page of the first file.'))
        page.add_row(auto_open_dir_button)

        label = gtk.Label(_('Number of pixels to scroll per arrow key press:'))
        adjustment = gtk.Adjustment(prefs['number of pixels to scroll per key event'], 1, 500, 1, 3)
        scroll_key_spinner = gtk.SpinButton(adjustment, digits=0)
        scroll_key_spinner.connect('value_changed', self._spinner_cb,
            'number of pixels to scroll per key event')
        scroll_key_spinner.set_tooltip_text(
            _('Set the number of pixels to scroll on a page when using the arrow keys.'))
        page.add_row(label, scroll_key_spinner)

        label = gtk.Label(_('Number of pixels to scroll per mouse wheel turn:'))
        adjustment = gtk.Adjustment(prefs['number of pixels to scroll per mouse wheel event'], 1, 500, 1, 3)
        scroll_key_spinner = gtk.SpinButton(adjustment, digits=0)
        scroll_key_spinner.connect('value_changed', self._spinner_cb,
            'number of pixels to scroll per mouse wheel event')
        scroll_key_spinner.set_tooltip_text(
            _('Set the number of pixels to scroll on a page when using a mouse wheel.'))
        page.add_row(label, scroll_key_spinner)

        label = gtk.Label(_('Number of "steps" to take before flipping the page:'))
        adjustment = gtk.Adjustment(prefs['number of key presses before page turn'], 1, 100, 1, 3)
        flipping_spinner = gtk.SpinButton(adjustment, digits=0)
        flipping_spinner.connect('value_changed', self._spinner_cb,
            'number of key presses before page turn')
        flipping_spinner.set_tooltip_text(
            _('Set the number of "steps" needed to flip to the next or previous page.  Less steps will allow for very fast page turning but you might find yourself accidentally turning pages.'))
        page.add_row(label, flipping_spinner)

        page.new_section(_('Double page mode'))

        step_length_button = gtk.CheckButton(
            _('Flip two pages in double page mode'))
        step_length_button.set_active(prefs['double step in double page mode'])
        step_length_button.connect('toggled', self._check_button_cb,
            'double step in double page mode')
        step_length_button.set_tooltip_text(
            _('Flip two pages, instead of one, each time we flip pages in double page mode.'))
        page.add_row(step_length_button)

        label = gtk.Label(_('Show only one page where appropriate:'))
        doublepage_control = self._create_doublepage_as_one_control()
        doublepage_control.set_tooltip_text(
            _("When showing the first page of an archive, or an image's width "
              "exceeds its height, only a single page will be displayed."))
        page.add_row(label, doublepage_control)
        page.new_section(_('Files'))

        auto_open_last_button = gtk.CheckButton(
            _('Automatically open the last viewed file on startup'))
        auto_open_last_button.set_active(prefs['auto load last file'])
        auto_open_last_button.connect('toggled', self._check_button_cb,
            'auto load last file')
        auto_open_last_button.set_tooltip_text(
            _('Automatically open, on startup, the file that was open when MComix was last closed.'))
        page.add_row(auto_open_last_button)

        store_recent_label = gtk.Label(
            _('Store information about recently opened files:'))
        store_recent_box = self._create_store_recent_combobox()
        store_recent_box.set_tooltip_text(
            _('Add information about all files opened from within MComix to the shared recent files list.'))
        page.add_row(store_recent_label, store_recent_box)

        return page

    def _init_display_tab(self):
        # ----------------------------------------------------------------
        # The "Display" tab.
        # ----------------------------------------------------------------
        page = preferences_page._PreferencePage(None)
        page.new_section(_('Fullscreen'))

        fullscreen_button = gtk.CheckButton(_('Use fullscreen by default'))
        fullscreen_button.set_active(prefs['default fullscreen'])
        fullscreen_button.connect('toggled', self._check_button_cb,
            'default fullscreen')
        page.add_row(fullscreen_button)

        hide_in_fullscreen_button = gtk.CheckButton(
            _('Automatically hide all toolbars in fullscreen'))
        hide_in_fullscreen_button.set_active(prefs['hide all in fullscreen'])
        hide_in_fullscreen_button.connect('toggled', self._check_button_cb,
            'hide all in fullscreen')
        page.add_row(hide_in_fullscreen_button)

        page.new_section(_('Fit to size mode'))

        fitside_label = gtk.Label(_('Fit to width or height:'))
        fitmode = self._create_fitmode_control()
        page.add_row(fitside_label, fitmode)

        fitsize_label = gtk.Label(_('Fixed size for this mode:'))
        adjustment = gtk.Adjustment(prefs['fit to size px'], 10, 10000, 10, 50)
        fitsize_spinner = gtk.SpinButton(adjustment, digits=0)
        fitsize_spinner.set_size_request(80, -1)
        fitsize_spinner.connect('value-changed', self._spinner_cb,
            'fit to size px')
        page.add_row(fitsize_label, fitsize_spinner)

        page.new_section(_('Slideshow'))
        label = gtk.Label(_('Slideshow delay (in seconds):'))
        adjustment = gtk.Adjustment(prefs['slideshow delay'] / 1000.0,
            0.01, 3600.0, 0.1, 1)
        delay_spinner = gtk.SpinButton(adjustment, digits=2)
        delay_spinner.set_size_request(80, -1)
        delay_spinner.connect('value_changed', self._spinner_cb,
            'slideshow delay')
        page.add_row(label, delay_spinner)

        label = gtk.Label(_('Slideshow step (in pixels):'))
        adjustment = gtk.Adjustment(prefs['number of pixels to scroll per slideshow event'],
            -500, 500, 1, 1)
        slideshow_step_spinner = gtk.SpinButton(adjustment, digits=0)
        slideshow_step_spinner.set_size_request(80, -1)
        slideshow_step_spinner.connect('value_changed', self._spinner_cb,
            'number of pixels to scroll per slideshow event')
        slideshow_step_spinner.set_tooltip_text(
            _('Specify the number of pixels to scroll while in slideshow mode. A positive value will scroll forward, a negative value will scroll backwards, and a value of 0 will cause the slideshow to always flip to a new page.'))
        page.add_row(label, slideshow_step_spinner)

        slideshow_auto_open_button = gtk.CheckButton(
            _('During a slideshow automatically open the next archive'))
        slideshow_auto_open_button.set_active(prefs['slideshow can go to next archive'])
        slideshow_auto_open_button.connect('toggled', self._check_button_cb,
            'slideshow can go to next archive')
        slideshow_auto_open_button.set_tooltip_text(
            _('While in slideshow mode allow the next archive to automatically be opened.'))
        page.add_row(slideshow_auto_open_button)

        page.new_section(_('Rotation'))
        auto_rotate_button = gtk.CheckButton(
            _('Automatically rotate images according to their metadata'))
        auto_rotate_button.set_active(prefs['auto rotate from exif'])
        auto_rotate_button.connect('toggled', self._check_button_cb,
            'auto rotate from exif')
        auto_rotate_button.set_tooltip_text(
            _('Automatically rotate images when an orientation is specified in the image metadata, such as in an Exif tag.'))
        page.add_row(auto_rotate_button)

        page.new_section(_('Image quality'))
        label = gtk.Label(_('Scaling mode'))
        scaling_box = self._create_scaling_quality_combobox()
        scaling_box.set_tooltip_text(
            _('Changes how images are scaled. Slower algorithms result in higher quality resizing, but longer page loading times.'))
        page.add_row(label, scaling_box)

        return page

    def _init_advanced_tab(self):
        # ----------------------------------------------------------------
        # The "Advanced" tab.
        # ----------------------------------------------------------------
        page = preferences_page._PreferencePage(None)

        page.new_section(_('User interface'))
        label = gtk.Label(_('Language (needs restart):'))
        language_box = self._create_language_control()
        page.add_row(label, language_box)

        esc_quits = gtk.CheckButton(_('Escape key closes program'))
        esc_quits.set_active(prefs['escape quits'])
        esc_quits.connect('toggled', self._check_button_cb,
            'escape quits')
        esc_quits.set_tooltip_text(
            _('When active, the ESC key closes the program, instead of only '
              'disabling fullscreen mode.'))
        page.add_row(esc_quits)

        page.new_section(_('File order'))

        label = gtk.Label(_('Order files by:'))
        page.add_row(label, self._create_sort_by_control())

        page.new_section(_('Cache'))

        create_thumbs_button = gtk.CheckButton(
            _('Store thumbnails for opened files'))
        create_thumbs_button.set_active(prefs['create thumbnails'])
        create_thumbs_button.connect('toggled', self._check_button_cb,
            'create thumbnails')
        create_thumbs_button.set_tooltip_text(
            _('Store thumbnails for opened files according to the freedesktop.org specification. These thumbnails are shared by many other applications, such as most file managers.'))
        page.add_row(create_thumbs_button)

        label = gtk.Label(_('Maximum number of pages to store in the cache:'))
        adjustment = gtk.Adjustment(prefs['max pages to cache'], -1, 500, 1, 3)
        cache_spinner = gtk.SpinButton(adjustment, digits=0)
        cache_spinner.connect('value-changed', self._spinner_cb,
                                            'max pages to cache')
        cache_spinner.set_tooltip_text(
            _('Set the max number of pages to cache. A value of -1 will cache the entire archive.'))
        page.add_row(label, cache_spinner)

        page.new_section(_('Magnifying Lens'))

        label = gtk.Label(_('Magnifying lens size (in pixels):'))
        adjustment = gtk.Adjustment(prefs['lens size'], 50, 400, 1, 10)
        lens_size_spinner = gtk.SpinButton(adjustment)
        lens_size_spinner.connect('value_changed', self._spinner_cb,
            'lens size')
        lens_size_spinner.set_tooltip_text(
            _('Set the size of the magnifying lens. It is a square with a side of this many pixels.'))
        page.add_row(label, lens_size_spinner)
        label = gtk.Label(_('Magnification factor:'))
        adjustment = gtk.Adjustment(prefs['lens magnification'], 1.1, 10.0,
            0.1, 1.0)
        lens_magnification_spinner = gtk.SpinButton(adjustment, digits=1)
        lens_magnification_spinner.connect('value_changed', self._spinner_cb,
            'lens magnification')
        lens_magnification_spinner.set_tooltip_text(
            _('Set the magnification factor of the magnifying lens.'))
        page.add_row(label, lens_magnification_spinner)

        page.new_section(_('Comments'))
        label = gtk.Label(_('Comment extensions:'))
        extensions_entry = gtk.Entry()
        extensions_entry.set_size_request(200, -1)
        extensions_entry.set_text(', '.join(prefs['comment extensions']))
        extensions_entry.connect('activate', self._entry_cb)
        extensions_entry.connect('focus_out_event', self._entry_cb)
        extensions_entry.set_tooltip_text(
            _('Treat all files found within archives, that have one of these file endings, as comments.'))
        page.add_row(label, extensions_entry)

        return page

    def _response(self, dialog, response):
        if response == gtk.RESPONSE_CLOSE:
            _close_dialog()

        elif response == constants.RESPONSE_REVERT_TO_DEFAULT:
            # Reset stored choices
            prefs['stored dialog choices'] = {}
            self.reset_button.set_sensitive(False)

        else:
            # Other responses close the dialog, e.g. clicking the X icon on the dialog.
            _close_dialog()

    def _create_language_control(self):
        """ Creates and returns the combobox for language selection. """
        languages = [
            (_('Auto-detect (Default)'), 'auto'),
            (_('Catalan'), 'ca'),
            (_('Czech'), 'cs'),
            (_('German'), 'de'),
            (_('Greek'), 'el'),
            (_('English'), 'en'),
            (_('Spanish'), 'es'),
            (_('Persian'), 'fa'),
            (_('French'), 'fr'),
            (_('Galician'), 'gl'),
            (_('Croatian'), 'hr'),
            (_('Hungarian'), 'hu'),
            (_('Indonesian'), 'id'),
            (_('Italian'), 'it'),
            (_('Japanese'), 'ja'),
            (_('Korean'), 'ko'),
            (_('Dutch'), 'nl'),
            (_('Polish'), 'pl'),
            (_('Portuguese'), 'pt_BR'),
            (_('Russian'), 'ru'),
            (_('Swedish'), 'sv'),
            (_('Ukrainian'), 'uk'),
            (_('Chinese (simplified)'), 'zh_CN'),
            (_('Chinese (traditional)'), 'zh_TW')]
        languages.sort(key=operator.itemgetter(0))

        box = self._create_combobox(languages, prefs['language'],
                self._language_changed_cb)

        return box

    def _language_changed_cb(self, combobox, *args):
        """ Called whenever the language was changed. """
        model_index = combobox.get_active()
        if model_index > -1:
            iter = combobox.get_model().iter_nth_child(None, model_index)
            text, lang_code = combobox.get_model().get(iter, 0, 1)
            prefs['language'] = lang_code

    def _create_doublepage_as_one_control(self):
        """ Creates the ComboBox control for selecting virtual double page options. """
        items = (
                (_('Never'), 0),
                (_('Only for title pages'), constants.SHOW_DOUBLE_AS_ONE_TITLE),
                (_('Only for wide images'), constants.SHOW_DOUBLE_AS_ONE_WIDE),
                (_('Always'), constants.SHOW_DOUBLE_AS_ONE_TITLE | constants.SHOW_DOUBLE_AS_ONE_WIDE))

        box = self._create_combobox(items,
                prefs['virtual double page for fitting images'],
                self._double_page_changed_cb)

        return box

    def _double_page_changed_cb(self, combobox, *args):
        """ Called when a new option was selected for the virtual double page option. """
        iter = combobox.get_active_iter()
        if combobox.get_model().iter_is_valid(iter):
            value = combobox.get_model().get_value(iter, 1)
            prefs['virtual double page for fitting images'] = value
            self._window.draw_image()

    def _create_fitmode_control(self):
        """ Combobox for fit to size mode """
        items = (
                (_('Fit to width'), constants.ZOOM_MODE_WIDTH),
                (_('Fit to height'), constants.ZOOM_MODE_HEIGHT))

        box = self._create_combobox(items,
                prefs['fit to size mode'],
                self._fit_to_size_changed_cb)

        return box

    def _fit_to_size_changed_cb(self, combobox, *args):
        """ Change to 'Fit to size' pixels """
        iter = combobox.get_active_iter()
        if combobox.get_model().iter_is_valid(iter):
            value = combobox.get_model().get_value(iter, 1)

            if prefs['fit to size mode'] != value:
                prefs['fit to size mode'] = value
                self._window.change_zoom_mode()

    def _create_sort_by_control(self):
        """ Creates the ComboBox control for selecting archive sort by options. """
        sortkey_items = (
                (_('No sorting'), 0),
                (_('File name'), constants.SORT_NAME),
                (_('File size'), constants.SORT_SIZE),
                (_('Last modified'), constants.SORT_LAST_MODIFIED))

        sortkey_box = self._create_combobox(sortkey_items, prefs['sort by'],
            self._sort_by_changed_cb)

        sortorder_items = (
                (_('Ascending'), constants.SORT_ASCENDING),
                (_('Descending'), constants.SORT_DESCENDING))

        sortorder_box = self._create_combobox(sortorder_items,
                prefs['sort order'],
                self._sort_order_changed_cb)

        box = gtk.HBox()
        box.pack_start(sortkey_box)
        box.pack_start(sortorder_box)

        label = _("Files will be opened and displayed according to the sort order "
              "specified here. This option does not affect ordering within archives.")
        sortkey_box.set_tooltip_text(label)
        sortorder_box.set_tooltip_text(label)

        return box

    def _sort_by_changed_cb(self, combobox, *args):
        """ Called when a new option was selected for the virtual double page option. """
        iter = combobox.get_active_iter()
        if combobox.get_model().iter_is_valid(iter):
            value = combobox.get_model().get_value(iter, 1)
            prefs['sort by'] = value

            self._window.filehandler.refresh_file()

    def _sort_order_changed_cb(self, combobox, *args):
        """ Called when sort order changes (ascending or descending) """
        iter = combobox.get_active_iter()
        if combobox.get_model().iter_is_valid(iter):
            value = combobox.get_model().get_value(iter, 1)
            prefs['sort order'] = value

            self._window.filehandler.refresh_file()

    def _create_store_recent_combobox(self):
        """ Creates the combobox for "Store recently opened files". """
        items = (
                (_('Never'), 0),
                (_('Only file names'), constants.STORE_LAST_PATH),
                (_('File names and last read page'), constants.STORE_LAST_PATH_AND_PAGE))

        # Map legacy true/false values:
        if prefs['store recent file info'] is True:
            selection = constants.STORE_LAST_PATH
        elif prefs['store recent file info'] is False:
            selection = 0
        else:
            selection = prefs['store recent file info']

        box = self._create_combobox(items, selection, self._store_recent_changed_cb)
        return box

    def _store_recent_changed_cb(self, combobox, *args):
        """ Called when option "Store recently opened files" was changed. """
        iter = combobox.get_active_iter()
        if not combobox.get_model().iter_is_valid(iter):
            return

        value = combobox.get_model().get_value(iter, 1)
        last_value = prefs['store recent file info']
        prefs['store recent file info'] = value
        self._window.filehandler.last_read_page.set_enabled(
            value == constants.STORE_LAST_PATH_AND_PAGE)

        # If "Never" was selected, ask to purge recent files.
        if (last_value > 0 and value == 0
            and (self._window.uimanager.recent.count() > 0
                 or self._window.filehandler.last_read_page.count() > 0)):

            dialog = message_dialog.MessageDialog(self, gtk.DIALOG_MODAL,
                gtk.MESSAGE_INFO, gtk.BUTTONS_YES_NO)
            dialog.set_default_response(gtk.RESPONSE_YES)
            dialog.set_text(
                _('Delete information about recently opened files?'),
                _('This will remove all entries from the "Recent" menu,'
                  ' and clear information about last read pages.'))
            response = dialog.run()

            if response == gtk.RESPONSE_YES:
                self._window.uimanager.recent.remove_all()
                self._window.filehandler.last_read_page.clear_all()

    def _create_scaling_quality_combobox(self):
        """ Creates combo box for image scaling quality """
        items = (
                (_('Normal (fast)'), int(gtk.gdk.INTERP_TILES)),
                (_('Bilinear'), int(gtk.gdk.INTERP_BILINEAR)),
                (_('Hyperbolic (slow)'), int(gtk.gdk.INTERP_HYPER)))

        selection = prefs['scaling quality']

        return self._create_combobox(items, selection, self._scaling_quality_changed_cb)

    def _scaling_quality_changed_cb(self, combobox, *args):
        """ Called whan image scaling quality changes. """
        iter = combobox.get_active_iter()
        if combobox.get_model().iter_is_valid(iter):
            value = combobox.get_model().get_value(iter, 1)
            last_value = prefs['scaling quality']
            prefs['scaling quality'] = value

            if value != last_value:
                self._window.draw_image()

    def _create_combobox(self, options, selected_value, change_callback):
        """ Creates a new dropdown combobox and populates it with the items
        passed in C{options}.

        @param options: List of tuples: (Option display text, option value)
        @param selected_value: One of the values passed in C{options} that will
            be pre-selected when the control is created.
        @param change_callback: Function that will be called when the 'changed'
            event is triggered.
        @returns gtk.ComboBox
        """
        assert options and len(options[0]) == 2, "Invalid format for options."

        # Use the first list item to determine typing of model fields.
        # First field is textual description, second field is value.
        model = gtk.ListStore(gobject.TYPE_STRING, type(options[0][1]))
        for text, value in options:
            model.append((text, value))

        box = gtk.ComboBox(model)
        renderer = gtk.CellRendererText()
        box.pack_start(renderer, True)
        box.add_attribute(renderer, "text", 0)

        # Set active box option
        iter = model.get_iter_first()
        while iter:
            if model.get_value(iter, 1) == selected_value:
                box.set_active_iter(iter)
                break
            else:
                iter = model.iter_next(iter)

        if change_callback:
            box.connect('changed', change_callback)

        return box

    def _check_button_cb(self, button, preference):
        """Callback for all checkbutton-type preferences."""

        prefs[preference] = button.get_active()

        if preference == 'color box bg' and button.get_active():

            if not prefs['smart bg'] or not self._window.filehandler.file_loaded:
                self._window.set_bg_colour(prefs['bg colour'])

        elif preference == 'smart bg' and button.get_active():

            # if the color is no longer using the smart background then return it to the chosen color
            if not prefs[preference]:
                self._window.set_bg_colour(prefs['bg colour'])
            else:
                # draw_image() will set the main background to the smart background
                self._window.draw_image()

        elif preference == 'color box thumb bg' and button.get_active():

            if prefs[preference]:
                prefs['smart thumb bg'] = False
                prefs['thumbnail bg uses main colour'] = False

                self._window.thumbnailsidebar.change_thumbnail_background_color(prefs['thumb bg colour'])
            else:
                self._window.draw_image()

        elif preference == 'smart thumb bg' and button.get_active():

            if prefs[preference]:
                prefs['color box thumb bg'] = False
                prefs['thumbnail bg uses main colour'] = False

                pixbuf = self._window.left_image.get_pixbuf()
                if pixbuf:
                    bg_color = image_tools.get_most_common_edge_colour(pixbuf)
                    self._window.thumbnailsidebar.change_thumbnail_background_color(bg_color)
            else:
                self._window.draw_image()

        elif preference in ('checkered bg for transparent images',
          'no double page for wide images', 'auto rotate from exif'):
            self._window.draw_image()

        elif (preference == 'hide all in fullscreen' and
            self._window.is_fullscreen):
            self._window.draw_image()

        elif preference == 'show page numbers on thumbnails':
            self._window.thumbnailsidebar.toggle_page_numbers_visible()

    def _color_button_cb(self, colorbutton, preference):
        """Callback for the background colour selection button."""

        colour = colorbutton.get_color()

        if preference == 'bg colour':
            prefs['bg colour'] = colour.red, colour.green, colour.blue

            if not prefs['smart bg'] or not self._window.filehandler.file_loaded:
                self._window.set_bg_colour(prefs['bg colour'])

        elif preference == 'thumb bg colour':

            prefs['thumb bg colour'] = colour.red, colour.green, colour.blue

            if not prefs['smart thumb bg'] or not self._window.filehandler.file_loaded:
                self._window.thumbnailsidebar.change_thumbnail_background_color( prefs['thumb bg colour'] )

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

        elif preference == 'number of pixels to scroll per slideshow event':
            prefs[preference] = int(value)

        elif preference == 'number of pixels to scroll per key event':
            prefs[preference] = int(value)

        elif preference == 'number of pixels to scroll per mouse wheel event':
            prefs[preference] = int(value)

        elif preference == 'thumbnail size':
            prefs[preference] = int(value)
            self._window.thumbnailsidebar.resize()
            self._window.draw_image()

        elif preference == 'max pages to cache':
            prefs[preference] = int(value)
            self._window.imagehandler.do_cacheing()

        elif preference == 'number of key presses before page turn':
            prefs['number of key presses before page turn'] = int(value)
            self._window._event_handler._extra_scroll_events = 0

        elif preference == 'fit to size px':
            prefs[preference] = int(value)
            self._window.change_zoom_mode()


    def _entry_cb(self, entry, event=None):
        """Callback for entry-type preferences."""
        text = entry.get_text()
        extensions = [e.strip() for e in text.split(',')]
        prefs['comment extensions'] = [e for e in extensions if e]
        self._window.filehandler.update_comment_extensions()

def open_dialog(action, window):
    """Create and display the preference dialog."""

    global _dialog

    # if the dialog window is not created then create the window
    if _dialog is None:
        _dialog = _PreferencesDialog(window)
    else:
        # if the dialog window already exists bring it to the forefront of the screen
        _dialog.present()

def _close_dialog():

    global _dialog

    # if the dialog window exists then destroy it
    if _dialog is not None:
        _dialog.destroy()
        _dialog = None


# vim: expandtab:sw=4:ts=4

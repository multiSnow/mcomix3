'''enhance_dialog.py - Image enhancement dialog.'''

from gi.repository import Gtk

from mcomix import histogram
from mcomix import image_tools
from mcomix.preferences import prefs

_dialog = None

class _EnhanceImageDialog(Gtk.Dialog):

    '''A Gtk.Dialog which allows modification of the values belonging to
    an ImageEnhancer.
    '''

    def __init__(self, window):
        super(_EnhanceImageDialog, self).__init__(title=_('Enhance image'))
        self.set_transient_for(window)
        self._window = window

        reset = Gtk.Button.new_from_stock(Gtk.STOCK_REVERT_TO_SAVED)
        reset.set_tooltip_text(_('Reset to defaults.'))
        self.add_action_widget(reset, Gtk.ResponseType.REJECT)
        save = Gtk.Button.new_from_stock(Gtk.STOCK_SAVE)
        save.set_tooltip_text(_('Save the selected values as default for future files.'))
        self.add_action_widget(save, Gtk.ResponseType.APPLY)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        self.set_resizable(False)
        self.connect('response', self._response)
        self.set_default_response(Gtk.ResponseType.OK)

        self._enhancer = window.enhancer
        self._block = False

        vbox = Gtk.VBox(homogeneous=False, spacing=10)
        self.set_border_width(4)
        vbox.set_border_width(6)
        self.vbox.add(vbox)

        self._hist_image = Gtk.Image()
        self._hist_image.set_size_request(262, 170)
        vbox.pack_start(self._hist_image, True, True, 0)
        vbox.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), True, True, 0)

        hbox = Gtk.HBox(homogeneous=False, spacing=4)
        vbox.pack_start(hbox, False, False, 2)
        vbox_left = Gtk.VBox(homogeneous=False, spacing=4)
        vbox_right = Gtk.VBox(homogeneous=False, spacing=4)
        hbox.pack_start(vbox_left, False, False, 2)
        hbox.pack_start(vbox_right, True, True, 2)

        def _create_scale(label_text):
            label = Gtk.Label(label=label_text)
            label.set_alignment(1, 0.5)
            label.set_use_underline(True)
            vbox_left.pack_start(label, True, False, 2)
            adj = Gtk.Adjustment(value=0.0, lower=-1.0, upper=1.0, step_increment=0.01, page_increment=0.1)
            scale = Gtk.HScale.new(adj)
            scale.set_digits(2)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            scale.connect('value-changed', self._change_values)
            # FIXME
            # scale.set_update_policy(Gtk.UPDATE_DELAYED)
            label.set_mnemonic_widget(scale)
            vbox_right.pack_start(scale, True, False, 2)
            return scale

        self._brightness_scale = _create_scale(_('_Brightness:'))
        self._contrast_scale = _create_scale(_('_Contrast:'))
        self._saturation_scale = _create_scale(_('S_aturation:'))
        self._sharpness_scale = _create_scale(_('S_harpness:'))

        vbox.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), True, True, 0)

        self._autocontrast_button = \
            Gtk.CheckButton.new_with_mnemonic(_('_Automatically adjust contrast'))
        self._autocontrast_button.set_tooltip_text(
            _('Automatically adjust contrast (both lightness and darkness), separately for each colour band.'))
        vbox.pack_start(self._autocontrast_button, False, False, 2)
        self._autocontrast_button.connect('toggled', self._change_values)

        self._block = True
        self._brightness_scale.set_value(self._enhancer.brightness - 1)
        self._contrast_scale.set_value(self._enhancer.contrast - 1)
        self._saturation_scale.set_value(self._enhancer.saturation - 1)
        self._sharpness_scale.set_value(self._enhancer.sharpness - 1)
        self._autocontrast_button.set_active(self._enhancer.autocontrast)
        self._block = False
        self._contrast_scale.set_sensitive(
            not self._autocontrast_button.get_active())

        self._window.imagehandler.page_available += self._on_page_available
        self._window.filehandler.file_closed += self._on_book_close
        self._window.page_changed += self._on_page_change
        self._on_page_change()

        self.show_all()

    def _on_book_close(self):
        self.clear_histogram()

    def _on_page_change(self):
        if not self._window.imagehandler.page_is_available():
            self.clear_histogram()
            return
        # XXX transitional(double page limitation)
        pixbuf = self._window.imagehandler.get_pixbufs(1)[0]
        self.draw_histogram(pixbuf)

    def _on_page_available(self, page_number):
        current_page_number = self._window.imagehandler.get_current_page()
        if current_page_number == page_number:
            self._on_page_change()

    def draw_histogram(self, pixbuf):
        '''Draw a histogram representing <pixbuf> in the dialog.'''
        pixbuf = image_tools.static_image(pixbuf)
        histogram_pixbuf = histogram.draw_histogram(pixbuf, text=False)
        self._hist_image.set_from_pixbuf(histogram_pixbuf)

    def clear_histogram(self):
        '''Clear the histogram in the dialog.'''
        self._hist_image.clear()

    def _change_values(self, *args):
        if self._block:
            return

        self._enhancer.brightness = self._brightness_scale.get_value() + 1
        self._enhancer.contrast = self._contrast_scale.get_value() + 1
        self._enhancer.saturation = self._saturation_scale.get_value() + 1
        self._enhancer.sharpness = self._sharpness_scale.get_value() + 1
        self._enhancer.autocontrast = self._autocontrast_button.get_active()
        self._contrast_scale.set_sensitive(
            not self._autocontrast_button.get_active())
        self._enhancer.signal_update()

    def _response(self, dialog, response):

        if response in [Gtk.ResponseType.OK, Gtk.ResponseType.DELETE_EVENT]:
            _close_dialog()

        elif response == Gtk.ResponseType.APPLY:
            self._change_values(self)
            prefs['brightness'] = self._enhancer.brightness
            prefs['contrast'] = self._enhancer.contrast
            prefs['saturation'] = self._enhancer.saturation
            prefs['sharpness'] = self._enhancer.sharpness
            prefs['auto contrast'] = self._enhancer.autocontrast

        elif response == Gtk.ResponseType.REJECT:
            self._block = True
            self._brightness_scale.set_value(prefs['brightness'] - 1.0)
            self._contrast_scale.set_value(prefs['contrast'] - 1.0)
            self._saturation_scale.set_value(prefs['saturation'] - 1.0)
            self._sharpness_scale.set_value(prefs['sharpness'] - 1.0)
            self._autocontrast_button.set_active(prefs['auto contrast'])
            self._block = False
            self._change_values(self)


def open_dialog(action, window):
    '''Create and display the (singleton) image enhancement dialog.'''
    global _dialog

    if _dialog is None:
        _dialog = _EnhanceImageDialog(window)
    else:
        _dialog.present()

def _close_dialog(*args):
    '''Destroy the image enhancement dialog.'''
    global _dialog

    if _dialog is not None:
        _dialog.destroy()
        _dialog = None


# vim: expandtab:sw=4:ts=4

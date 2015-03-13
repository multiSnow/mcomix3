"""enhance_dialog.py - Image enhancement dialog."""

import gtk
import histogram

from mcomix.preferences import prefs

_dialog = None

class _EnhanceImageDialog(gtk.Dialog):

    """A gtk.Dialog which allows modification of the values belonging to
    an ImageEnhancer.
    """

    def __init__(self, window):
        gtk.Dialog.__init__(self, _('Enhance image'), window, 0)

        self._window = window

        reset = gtk.Button(None, gtk.STOCK_REVERT_TO_SAVED)
        reset.set_tooltip_text(_('Reset to defaults.'))
        self.add_action_widget(reset, gtk.RESPONSE_REJECT)
        save = gtk.Button(None, gtk.STOCK_SAVE)
        save.set_tooltip_text(_('Save the selected values as default for future files.'))
        self.add_action_widget(save, gtk.RESPONSE_APPLY)
        self.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)

        self.set_has_separator(False)
        self.set_resizable(False)
        self.connect('response', self._response)
        self.set_default_response(gtk.RESPONSE_OK)

        self._enhancer = window.enhancer
        self._block = False

        vbox = gtk.VBox(False, 10)
        self.set_border_width(4)
        vbox.set_border_width(6)
        self.vbox.add(vbox)

        self._hist_image = gtk.Image()
        self._hist_image.set_size_request(262, 170)
        vbox.pack_start(self._hist_image)
        vbox.pack_start(gtk.HSeparator())

        hbox = gtk.HBox(False, 4)
        vbox.pack_start(hbox, False, False, 2)
        vbox_left = gtk.VBox(False, 4)
        vbox_right = gtk.VBox(False, 4)
        hbox.pack_start(vbox_left, False, False, 2)
        hbox.pack_start(vbox_right, True, True, 2)

        def _create_scale(label_text):
            label = gtk.Label(label_text)
            label.set_alignment(1, 0.5)
            label.set_use_underline(True)
            vbox_left.pack_start(label, True, False, 2)
            adj = gtk.Adjustment(0.0, -1.0, 1.0, 0.01, 0.1)
            scale = gtk.HScale(adj)
            scale.set_digits(2)
            scale.set_value_pos(gtk.POS_RIGHT)
            scale.connect('value-changed', self._change_values)
            scale.set_update_policy(gtk.UPDATE_DELAYED)
            label.set_mnemonic_widget(scale)
            vbox_right.pack_start(scale, True, False, 2)
            return scale

        self._brightness_scale = _create_scale(_('_Brightness:'))
        self._contrast_scale = _create_scale(_('_Contrast:'))
        self._saturation_scale = _create_scale(_('S_aturation:'))
        self._sharpness_scale = _create_scale(_('S_harpness:'))

        vbox.pack_start(gtk.HSeparator())

        self._autocontrast_button = \
            gtk.CheckButton(_('_Automatically adjust contrast'))
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
        """Draw a histogram representing <pixbuf> in the dialog."""
        histogram_pixbuf = histogram.draw_histogram(pixbuf, text=False)
        self._hist_image.set_from_pixbuf(histogram_pixbuf)

    def clear_histogram(self):
        """Clear the histogram in the dialog."""
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

        if response in [gtk.RESPONSE_OK, gtk.RESPONSE_DELETE_EVENT]:
            _close_dialog()

        elif response == gtk.RESPONSE_APPLY:
            self._change_values(self)
            prefs['brightness'] = self._enhancer.brightness
            prefs['contrast'] = self._enhancer.contrast
            prefs['saturation'] = self._enhancer.saturation
            prefs['sharpness'] = self._enhancer.sharpness
            prefs['auto contrast'] = self._enhancer.autocontrast

        elif response == gtk.RESPONSE_REJECT:
            self._block = True
            self._brightness_scale.set_value(prefs['brightness'] - 1.0)
            self._contrast_scale.set_value(prefs['contrast'] - 1.0)
            self._saturation_scale.set_value(prefs['saturation'] - 1.0)
            self._sharpness_scale.set_value(prefs['sharpness'] - 1.0)
            self._autocontrast_button.set_active(prefs['auto contrast'])
            self._block = False
            self._change_values(self)


def open_dialog(action, window):
    """Create and display the (singleton) image enhancement dialog."""
    global _dialog

    if _dialog is None:
        _dialog = _EnhanceImageDialog(window)
    else:
        _dialog.present()

def _close_dialog(*args):
    """Destroy the image enhancement dialog."""
    global _dialog

    if _dialog is not None:
        _dialog.destroy()
        _dialog = None


# vim: expandtab:sw=4:ts=4

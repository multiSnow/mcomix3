"""labels.py - Gtk.Label convenience classes."""

from gi.repository import GLib, Gtk, Pango

class FormattedLabel(Gtk.Label):

    """FormattedLabel keeps a label always formatted with some pango weight,
    style and scale, even when new text is set using set_text().
    """

    _STYLES = {
        Pango.Style.NORMAL : 'normal',
        Pango.Style.OBLIQUE: 'oblique',
        Pango.Style.ITALIC : 'italic',
    }

    def __init__(self, text='', weight=Pango.Weight.NORMAL,
      style=Pango.Style.NORMAL, scale=1.0):
        super(FormattedLabel, self).__init__()
        self._weight = weight
        self._style = style
        self._scale = scale
        self.set_text(text)

    def set_text(self, text):
        markup = '<span font_size="%u" font_weight="%u" font_style="%s">%s</span>' % (
            int(self._scale * 10 * 1024),
            self._weight,
            self._STYLES[self._style],
            GLib.markup_escape_text(text)
        )
        self.set_markup(markup)

class BoldLabel(FormattedLabel):

    """A FormattedLabel that is always bold and otherwise normal."""

    def __init__(self, text=''):
        super(BoldLabel, self).__init__(text=text, weight=Pango.Weight.BOLD)

class ItalicLabel(FormattedLabel):

    """A FormattedLabel that is always italic and otherwise normal."""

    def __init__(self, text=''):
        super(ItalicLabel, self).__init__(text=text, style=Pango.Style.ITALIC)


# vim: expandtab:sw=4:ts=4

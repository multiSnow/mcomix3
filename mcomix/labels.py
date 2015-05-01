"""labels.py - gtk.Label convenience classes."""

import gtk
import pango

class FormattedLabel(gtk.Label):

    """FormattedLabel keeps a label always formatted with some pango weight,
    style and scale, even when new text is set using set_text().
    """

    def __init__(self, text='', weight=pango.WEIGHT_NORMAL,
      style=pango.STYLE_NORMAL, scale=1.0):
        super(FormattedLabel, self).__init__(text)
        self._weight = weight
        self._style = style
        self._scale = scale
        self._format()

    def set_text(self, text):
        gtk.Label.set_text(self, text)
        self._format()

    def _format(self):
        text_len = len(self.get_text())
        attrlist = pango.AttrList()
        attrlist.insert(pango.AttrWeight(self._weight, 0, text_len))
        attrlist.insert(pango.AttrStyle(self._style, 0, text_len))
        attrlist.insert(pango.AttrScale(self._scale, 0, text_len))
        self.set_attributes(attrlist)

class BoldLabel(FormattedLabel):

    """A FormattedLabel that is always bold and otherwise normal."""

    def __init__(self, text=''):
        super(BoldLabel, self).__init__(text=text, weight=pango.WEIGHT_BOLD)

class ItalicLabel(FormattedLabel):

    """A FormattedLabel that is always italic and otherwise normal."""

    def __init__(self, text=''):
        super(ItalicLabel, self).__init__(text=text, style=pango.STYLE_ITALIC)


# vim: expandtab:sw=4:ts=4

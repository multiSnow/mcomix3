"""properties_page.py - A page to put in the properties dialog window."""

import gtk

from mcomix import i18n
from mcomix import image_tools
from mcomix import labels

class _Page(gtk.ScrolledWindow):

    """A page to put in the gtk.Notebook. Contains info about a file (an
    image or an archive.)
    """

    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._vbox = gtk.VBox(False, 12)
        self.add_with_viewport(self._vbox)

        self.set_border_width(12)
        topbox = gtk.HBox(False, 12)
        self._vbox.pack_start(topbox, False)
        self._thumb = gtk.Image()
        topbox.pack_start(self._thumb, False, False)
        borderbox = gtk.Frame()
        borderbox.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        borderbox.set_size_request(-1, 130)
        topbox.pack_start(borderbox)
        insidebox = gtk.EventBox()
        insidebox.set_border_width(1)
        insidebox.set_state(gtk.STATE_ACTIVE)
        borderbox.add(insidebox)
        self._mainbox = gtk.VBox(False, 5)
        self._mainbox.set_border_width(10)
        insidebox.add(self._mainbox)

    def set_thumbnail(self, pixbuf):
        pixbuf = image_tools.add_border(pixbuf, 1)
        self._thumb.set_from_pixbuf(pixbuf)

    def set_filename(self, filename):
        """Set the filename to be displayed to <filename>. Call this before
        set_main_info().
        """
        label = labels.BoldLabel(i18n.to_unicode(filename))
        label.set_alignment(0, 0.5)
        label.set_selectable(True)
        self._mainbox.pack_start(label, False, False)
        self._mainbox.pack_start(gtk.VBox()) # Just to add space (better way?)

    def set_main_info(self, info):
        """Set the information in the main info box (below the filename) to
        the values in the sequence <info>.
        """
        for text in info:
            label = gtk.Label(text)
            label.set_alignment(0, 0.5)
            label.set_selectable(True)
            self._mainbox.pack_start(label, False, False)

    def set_secondary_info(self, info):
        """Set the information below the main info box to the values in the
        sequence <info>. Each entry in info should be a tuple (desc, value).
        """
        hbox = gtk.HBox(False, 10)
        self._vbox.pack_start(hbox, False, False)
        left_box = gtk.VBox(True, 8)
        right_box = gtk.VBox(True, 8)
        hbox.pack_start(left_box, False, False)
        hbox.pack_start(right_box, False, False)
        for desc, value in info:
            desc_label = labels.BoldLabel('%s:' % desc)
            desc_label.set_alignment(1.0, 1.0)
            left_box.pack_start(desc_label, True, True)
            value_label = gtk.Label(value)
            value_label.set_alignment(0, 1.0)
            value_label.set_selectable(True)
            right_box.pack_start(value_label, True, True)

# vim: expandtab:sw=4:ts=4

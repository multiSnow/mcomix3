"""status.py - Statusbar for main window."""

import gtk
import gobject

import i18n
from preferences import prefs

class Statusbar(gtk.CellView):

    def __init__(self):
        gtk.CellView.__init__(self)
        for i in range(4):
            cell = gtk.CellRendererText()
            cell.set_property("xpad", 20)
            self.pack_start(cell, False)
            self.add_attribute(cell, "text", i)

        self._page_info = ''
        self._resolution = ''
        self._root = ''
        self._filename = ''

    def set_message(self, message):
        """Set a specific message (such as an error message) on the statusbar,
        replacing whatever was there earlier.
        """
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
            gobject.TYPE_STRING, gobject.TYPE_STRING)
        model.append((message, '', '', ''))
        self.set_model(model)
        self.set_displayed_row(0)

    def set_page_number(self, page, total, double_page=False):
        """Update the page number."""
        if double_page:
            self._page_info = '%d,%d / %d' % (page, page + 1, total)
        else:
            self._page_info = '%d / %d' % (page, total)

    def set_resolution(self, left_dimensions, right_dimensions=None):
        """Update the resolution data.

        Takes one or two tuples, (x, y, scale), describing the original
        resolution of an image as well as the currently displayed scale
        in percent.
        """
        self._resolution = '%dx%d (%.1f%%)' % left_dimensions
        if right_dimensions is not None:
            self._resolution += ', %dx%d (%.1f%%)' % right_dimensions


    def set_root(self, root):
        """Set the name of the root (directory or archive)."""
        self._root = i18n.to_unicode(root)

    def set_filename(self, filename):
        """Update the filename."""
        self._filename = i18n.to_unicode(filename)

    def update(self):
        """Set the statusbar to display the current state."""
        #self.pop(0)
        #self.push(0, ' %s      |      %s      |      %s      |      %s' %
        #    (self._page_info, self._resolution, self._root, self._filename))

        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING,
            gobject.TYPE_STRING, gobject.TYPE_STRING)
        model.append((self._page_info, self._resolution, self._root, self._filename))
        self.set_model(model)
        self.set_displayed_row(0)



# vim: expandtab:sw=4:ts=4

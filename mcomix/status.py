"""status.py - Statusbar for main window."""

import gtk
import encoding
from preferences import prefs

class Statusbar(gtk.Statusbar):

    def __init__(self):
        gtk.Statusbar.__init__(self)
        self.set_has_resize_grip(True)
        self._page_info = ''
        self._resolution = ''
        self._root = ''
        self._filename = ''

    def set_message(self, message):
        """Set a specific message (such as an error message) on the statusbar,
        replacing whatever was there earlier.
        """
        self.pop(0)
        self.push(0, ' %s' % encoding.to_unicode(message))

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
        self._root = encoding.to_unicode(root)

    def set_filename(self, filename):
        """Update the filename."""
        self._filename = encoding.to_unicode(filename)

    def update(self):
        """Set the statusbar to display the current state."""
        self.pop(0)
        self.push(0, ' %s      |      %s      |      %s      |      %s' %
            (self._page_info, self._resolution, self._root, self._filename))


# vim: expandtab:sw=4:ts=4

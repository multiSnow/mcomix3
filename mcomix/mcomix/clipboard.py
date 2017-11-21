"""clipboard.py - Clipboard handler"""

from gi.repository import Gdk, Gtk

from mcomix import image_tools


class Clipboard(object):

    """The Clipboard takes care of all necessary copy-paste functionality
    """

    def __init__(self, window):
        self._clipboard = Gtk.Clipboard.get(Gdk.Atom.intern("CLIPBOARD", False))
        self._window = window

    def copy(self, text, pixbuf):
        """ Copies C{text} and C{pixbuf} to clipboard. """
        self._clipboard.set_text(text, len(text))
        self._clipboard.set_image(pixbuf)

    def copy_page(self, *args):
        """ Copies the currently opened page and pixbuf to clipboard. """

        if self._window.filehandler.file_loaded:
            # Get pixbuf for current page
            current_page_pixbufs = self._window.imagehandler.get_pixbufs(
                2 if self._window.displayed_double() else 1) # XXX limited to at most 2 pages

            if len(current_page_pixbufs) == 1:
                pixbuf = current_page_pixbufs[ 0 ]
            else:
                pixbuf = image_tools.combine_pixbufs(
                        current_page_pixbufs[ 0 ],
                        current_page_pixbufs[ 1 ],
                        self._window.is_manga_mode )

            path = self._window.imagehandler.get_path_to_page()
            self.copy(path, pixbuf)

# vim: expandtab:sw=4:ts=4

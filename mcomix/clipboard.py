"""clipboard.py - Clipboard handler"""

import gtk
import image_tools

class Clipboard(gtk.Clipboard):

    """The Clipboard takes care of all necessary copy-paste functionality
    """

    def __init__(self, window):
        self._window = window
        gtk.Clipboard.__init__(self, display=gtk.gdk.display_get_default(),
            selection="CLIPBOARD")

    def copy_page(self, *args):

        if self._window.filehandler.file_loaded:
            # Get pixbuf for current page
            current_page_pixbufs = self._window.imagehandler.get_pixbufs()

            if len(current_page_pixbufs) == 1:
                pixbuf = current_page_pixbufs[ 0 ]
            else:
                pixbuf = image_tools.combine_pixbufs(
                        current_page_pixbufs[ 0 ],
                        current_page_pixbufs[ 1 ],
                        self._window.is_manga_mode )

            # Get path for current page
            path = self._window.imagehandler.get_path_to_page().encode('utf-8')

            # Register various clipboard formats for either the text or the pixbuf.
            clipboard_targets = ("image/bmp", "text/plain", "STRING", "UTF8_STRING")
            self.set_with_data(
                [ (target, 0, 0) for target in clipboard_targets ],
                self._get_clipboard_content,
                self._clear_clipboard_content,
                (pixbuf, path))

    def _get_clipboard_content(self, clipboard, selectiondata, info, data):
        """ Called whenever an application requests the content of the clipboard.
        selectiondata.target will contain one of the targets that have previously been
        registered. Currently, only "image/bmp" provides pixbuf data, while all
        other types point to the currently opened file as UTF-8 string. """

        if selectiondata.target == "image/bmp":
            selectiondata.set_pixbuf(data[0])
        else:
            selectiondata.set_text(data[1])

    def _clear_clipboard_content(self, clipboard, data):
        """ Called when clipboard ownership changes. """
        pass

# vim: expandtab:sw=4:ts=4

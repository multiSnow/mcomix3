"""clipboard.py - Clipboard handler"""

import gtk
import ctypes
import cStringIO
import sys

from mcomix import log
from mcomix import image_tools


class Clipboard(gtk.Clipboard):

    """The Clipboard takes care of all necessary copy-paste functionality
    """

    def __init__(self, window):
        self._window = window
        gtk.Clipboard.__init__(self, display=gtk.gdk.display_get_default(),
            selection="CLIPBOARD")

    def copy(self, text, pixbuf):
        """ Copies C{text} and C{pixbuf} to clipboard. """
        if sys.platform == 'win32':
            self._copy_windows(pixbuf, text)
        else:
            self._copy_linux(pixbuf, text.encode('utf-8'))

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

            # Get path for current page
            path = self._window.imagehandler.get_path_to_page()
            self.copy(path, pixbuf)

    def _copy_windows(self, pixbuf, path):
        """ Copies pixbuf and path to the clipboard.
        Uses native Win32 API, as GTK+ doesn't seem to work. """

        windll = ctypes.windll
        OpenClipboard = windll.user32.OpenClipboard
        EmptyClipboard = windll.user32.EmptyClipboard
        SetClipboardData = windll.user32.SetClipboardData
        CloseClipboard = windll.user32.CloseClipboard
        GlobalAlloc = windll.kernel32.GlobalAlloc
        GlobalLock = windll.kernel32.GlobalLock
        GlobalLock.restype = ctypes.c_void_p
        GlobalUnlock = windll.kernel32.GlobalUnlock

        def buffer_to_handle(buffer, buffer_size):
            """ Creates a memory handle for the passed data.
            This handle doesn't need to be freed by the application. """
            global_mem = GlobalAlloc(
                0x0042,  # GMEM_MOVEABLE | GMEM_ZEROINIT
                buffer_size)
            lock = GlobalLock(global_mem)
            ctypes.memmove(lock, ctypes.addressof(buffer), buffer_size)
            GlobalUnlock(global_mem)

            return global_mem

        # Paste the text as Unicode string
        text_buffer = ctypes.create_unicode_buffer(path)
        text_handle = buffer_to_handle(text_buffer,
                ctypes.sizeof(text_buffer))
        # Paste the image as Win32 DIB structure
        pil = image_tools.pixbuf_to_pil(pixbuf)
        output = cStringIO.StringIO()
        pil.convert("RGB").save(output, "BMP")
        dibdata = output.getvalue()[14:]
        output.close()

        image_buffer = ctypes.create_string_buffer(dibdata)
        image_handle = buffer_to_handle(image_buffer,
                ctypes.sizeof(image_buffer))

        # Actually copy data to clipboard
        if OpenClipboard(self._window.window.handle):
            EmptyClipboard()
            SetClipboardData(13,  # CF_UNICODETEXT
                text_handle)
            SetClipboardData(8,  # CF_DIB
                image_handle)
            CloseClipboard()
        else:
            log.warning('Could not open clipboard.')

    def _copy_linux(self, pixbuf, path):
        # Register various clipboard formats for either the
        # text or the pixbuf.
        clipboard_targets = ("image/bmp",
                "text/plain", "STRING", "UTF8_STRING")
        self.set_with_data(
            [ (target, 0, 0) for target in clipboard_targets ],
            self._get_clipboard_content,
            self._clear_clipboard_content,
            (pixbuf, path))

    def _get_clipboard_content(self, clipboard, selectiondata, info, data):
        """ Called whenever an application requests the content of the
        clipboard. selectiondata.target will contain one of the targets
        that have previously been registered. Currently, only "image/bmp"
        provides pixbuf data, while all other types point to the currently
        opened file as UTF-8 string. """

        if selectiondata.target == "image/bmp":
            selectiondata.set_pixbuf(data[0])
        else:
            selectiondata.set_text(data[1])

    def _clear_clipboard_content(self, clipboard, data):
        """ Called when clipboard ownership changes. """
        pass

# vim: expandtab:sw=4:ts=4

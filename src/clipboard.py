"""clipboard.py - Clipboard handler"""

import gtk
import image_tools
import threading
import constants

class Clipboard(gtk.Clipboard):

    """The Clipboard takes care of all necessary copy-paste functionality
    """

    def __init__(self, window):
        self._window = window
        self.clipboard = gtk.Clipboard.__init__(self, display=gtk.gdk.display_get_default(),
            selection="CLIPBOARD")

    def copy_page(self, *args):
        copy_thread = threading.Thread(target=self.thread_copy_page, args=())
        copy_thread.setDaemon(False)
        copy_thread.start()
        
    def thread_copy_page(self):

        if self._window.filehandler.file_loaded:
            current_page_pixbufs = self._window.imagehandler.get_pixbufs()
            
            if len(current_page_pixbufs) == 1:
                self._window.clipboard.set_image( current_page_pixbufs[ 0 ] )

            else:
                new_pix_buf = image_tools.combine_pixbufs( current_page_pixbufs[ 0 ], current_page_pixbufs[ 1 ], self._window.is_manga_mode )

                self._window.clipboard.set_image( new_pix_buf )

                del new_pix_buf
           
                constants.RUN_GARBAGE_COLLECTOR

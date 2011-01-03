"""slideshow.py - Slideshow handler."""

import gtk
import gobject
from preferences import prefs

class Slideshow:
    
    """Slideshow handler that manages starting and stopping of slideshows."""

    def __init__(self, window):
        self._window = window
        self._running = False
        self._id = None

    def _start(self):
        if not self._running:
            self._id = gobject.timeout_add(prefs['slideshow delay'], self._next)
            self._running = True
            self._window.update_title()

    def _stop(self):
        if self._running:
            gobject.source_remove(self._id)
            self._running = False
            self._window.update_title()

    def _next(self):
        if prefs['number of pixels to scroll per slideshow event'] != 0:
        
            self._window.scroll_with_flipping(0, prefs['number of pixels to scroll per slideshow event'])
        else:
            self._window.next_page()
        
        return True

    def toggle(self, action):
        """Toggle a slideshow on or off."""
        if action.get_active():
            self._start()            
            self._window.uimanager.get_widget('/Tool/slideshow').set_stock_id( gtk.STOCK_MEDIA_STOP )
            self._window.uimanager.get_widget('/Tool/slideshow').set_tooltip_text( _('Stop slideshow')  )
        else:
            self._stop()
            self._window.uimanager.get_widget('/Tool/slideshow').set_stock_id( gtk.STOCK_MEDIA_PLAY )
            self._window.uimanager.get_widget('/Tool/slideshow').set_tooltip_text( _('Start slideshow') )

    def is_running(self):
        """Return True if a slideshow is currently running."""
        return self._running

    def update_delay(self):
        """Update the delay time a started slideshow is using."""
        if self.is_running():
            self._stop()
            self._start()


# vim: expandtab:sw=4:ts=4

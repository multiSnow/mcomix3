'''slideshow.py - Slideshow handler.'''

from gi.repository import Gtk

from mcomix.lib import mt
from mcomix.preferences import prefs

class Slideshow(object):

    '''Slideshow handler that manages starting and stopping of slideshows.'''

    def __init__(self, window):
        self._window = window
        self._interval = mt.Interval(
            prefs['slideshow delay'], Slideshow._next,
            args=(self._window,
                  prefs['number of pixels to scroll per slideshow event']))

    def start(self):
        if self.is_running():
            return
        self._interval.start()
        self._window.update_title()

    def stop(self):
        if not self.is_running():
            return
        self._interval.stop()
        self._window.update_title()

    def is_running(self):
        return self._interval.is_running()

    @staticmethod
    def _next(window, pixels):
        if pixels:
            window.scroll_with_flipping(0, pixels)
        else:
            window.flip_page(+1)
        return

    def toggle(self, action):
        '''Toggle a slideshow on or off.'''
        if action.get_active():
            self.start()
            self._window.uimanager.get_widget('/Tool/slideshow').set_stock_id( Gtk.STOCK_MEDIA_STOP )
            self._window.uimanager.get_widget('/Tool/slideshow').set_tooltip_text( _('Stop slideshow')  )
        else:
            self.stop()
            self._window.uimanager.get_widget('/Tool/slideshow').set_stock_id( Gtk.STOCK_MEDIA_PLAY )
            self._window.uimanager.get_widget('/Tool/slideshow').set_tooltip_text( _('Start slideshow') )

    def update_delay(self):
        '''Update the delay time a started slideshow is using.'''
        if not self.is_running():
            return
        self._interval.reset()


# vim: expandtab:sw=4:ts=4

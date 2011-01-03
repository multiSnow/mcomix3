"""recent.py - Recent files handler."""

import urllib
import gtk
import preferences
import sys
import encoding
import portability

class RecentFilesMenu(gtk.RecentChooserMenu):

    def __init__(self, ui, window):
        self._window = window
        self._manager = gtk.recent_manager_get_default()
        gtk.RecentChooserMenu.__init__(self, self._manager)

        self.set_sort_type(gtk.RECENT_SORT_MRU)
        self.set_show_tips(True)
        # Missing icons crash GTK on Win32
        if sys.platform == 'win32':
            self.set_show_icons(False)
            self.set_show_numbers(True)

        rfilter = gtk.RecentFilter()
        rfilter.add_pixbuf_formats()
        rfilter.add_mime_type('application/x-zip')
        rfilter.add_mime_type('application/zip')
        rfilter.add_mime_type('application/x-rar')
        rfilter.add_mime_type('application/x-tar')
        rfilter.add_mime_type('application/x-gzip')
        rfilter.add_mime_type('application/x-bzip2')
        rfilter.add_mime_type('application/x-cbz')
        rfilter.add_mime_type('application/x-cbr')
        rfilter.add_mime_type('application/x-cbt')
        # Win32 prefers file patterns instead of MIME types
        rfilter.add_pattern('*.zip')
        rfilter.add_pattern('*.rar')
        rfilter.add_pattern('*.cbz')
        rfilter.add_pattern('*.cbr')
        rfilter.add_pattern('*.tar')
        rfilter.add_pattern('*.gz')
        rfilter.add_pattern('*.bz2')
        self.add_filter(rfilter)

        self.connect('item_activated', self._load)

    def _load(self, *args):
        uri = self.get_current_uri()
        path = urllib.url2pathname(uri[7:])
        did_file_load = self._window.filehandler.open_file(path.decode('utf-8'))

        if not did_file_load:
            self.remove(path)

    def add(self, path):
        if not preferences.prefs['store recent file info']:
            return
        uri = portability.uri_prefix() + urllib.pathname2url(encoding.to_utf8(path))
        self._manager.add_item(uri)

    def remove(self, path):
        if not preferences.prefs['store recent file info']:
            return
        uri = portability.uri_prefix() + urllib.pathname2url(encoding.to_utf8(path))
        self._manager.remove_item(uri)


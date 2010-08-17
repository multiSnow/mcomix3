"""recent.py - Recent files handler."""

import urllib

import gtk

import preferences


class RecentFilesMenu(gtk.RecentChooserMenu):

    def __init__(self, ui, window):
        self._window = window
        self._manager = gtk.recent_manager_get_default()
        gtk.RecentChooserMenu.__init__(self, self._manager)

        self.set_sort_type(gtk.RECENT_SORT_MRU)
        self.set_show_tips(True)

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
        self.add_filter(rfilter)

        self.connect('item_activated', self._load)

    def _load(self, *args):
        uri = self.get_current_uri()
        path = urllib.url2pathname(uri[7:])
        self._window.file_handler.open_file(path)

    def add(self, path):
        if not preferences.prefs['store recent file info']:
            return
        uri = 'file://' + urllib.pathname2url(path)
        self._manager.add_item(uri)

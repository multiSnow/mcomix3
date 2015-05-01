"""recent.py - Recent files handler."""

import urllib
import itertools
import gtk
import glib
import gobject
import sys

from mcomix import preferences
from mcomix import i18n
from mcomix import portability
from mcomix import archive_tools
from mcomix import image_tools
from mcomix import log

class RecentFilesMenu(gtk.RecentChooserMenu):

    def __init__(self, ui, window):
        self._window = window
        self._manager = gtk.recent_manager_get_default()
        super(RecentFilesMenu, self).__init__(self._manager)

        self.set_sort_type(gtk.RECENT_SORT_MRU)
        self.set_show_tips(True)
        # Missing icons crash GTK on Win32
        if sys.platform == 'win32':
            self.set_show_icons(False)
            self.set_show_numbers(True)

        rfilter = gtk.RecentFilter()
        supported_formats = {}
        supported_formats.update(image_tools.get_supported_formats())
        supported_formats.update(archive_tools.get_supported_formats())
        for name in sorted(supported_formats):
            mime_types, patterns = supported_formats[name]
            for mime in mime_types:
                rfilter.add_mime_type(mime)
            for pat in patterns:
                rfilter.add_pattern(pat)
        self.add_filter(rfilter)

        self.connect('item_activated', self._load)

    def _load(self, *args):
        uri = self.get_current_uri()
        path = urllib.url2pathname(uri[7:])
        did_file_load = self._window.filehandler.open_file(path.decode('utf-8'))

        if not did_file_load:
            self.remove(path)

    def count(self):
        """ Returns the amount of stored entries. """
        return len(self._manager.get_items())

    def add(self, path):
        if not preferences.prefs['store recent file info']:
            return
        uri = portability.uri_prefix() + urllib.pathname2url(i18n.to_utf8(path))
        self._manager.add_item(uri)

    def remove(self, path):
        if not preferences.prefs['store recent file info']:
            return
        uri = portability.uri_prefix() + urllib.pathname2url(i18n.to_utf8(path))
        try:
            self._manager.remove_item(uri)
        except glib.GError:
            # Could not remove item
            pass

    def remove_all(self):
        """ Removes all entries to recently opened files. """
        try:
            self._manager.purge_items()
        except gobject.GError, error:
            log.debug(error)


# vim: expandtab:sw=4:ts=4

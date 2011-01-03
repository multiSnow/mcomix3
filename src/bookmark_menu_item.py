"""bookmark_menu_item.py - A signle bookmark item."""

import gtk

class _Bookmark(gtk.ImageMenuItem):

    """_Bookmark represents one bookmark. It extends the gtk.ImageMenuItem
    and is thus put directly in the bookmarks menu.
    """

    def __init__(self, window, file_handler, name, path, page, numpages, archive_type):
        self._name = name
        self._path = path
        self._page = page
        self._numpages = numpages
        self._window = window
        self._archive_type = archive_type
        self._file_handler = file_handler

        gtk.MenuItem.__init__(self, str(self), False)
        
        if self._archive_type is not None:
            im = gtk.image_new_from_stock('mcomix-archive', gtk.ICON_SIZE_MENU)

        else:
            im = gtk.image_new_from_stock('mcomix-image', gtk.ICON_SIZE_MENU)
            
        self.set_image(im)
        self.connect('activate', self._load)

    def __str__(self):
        return '%s, (%d / %d)' % (self._name, self._page, self._numpages)

    def _load(self, *args):
        """Open the file and page the bookmark represents."""
        
        if self._file_handler._base_path != self._path:
            self._file_handler.open_file(self._path, self._page)
        else:
            self._window.set_page(self._page)
            
            self._window.toolbar.hide()
            self._window.toolbar.show()

    def same_path(self, path):
        """Return True if the bookmark is for the file <path>."""
        return path == self._path

    def same_page(self, page):
        """Return True if the bookmark is for the same page."""
        return page == self._page

    def to_row(self):
        """Return a tuple corresponding to one row in the _BookmarkDialog's
        ListStore.
        """
        stock = self.get_image().get_stock()
        pixbuf = self.render_icon(*stock)
        page = '%d / %d' % (self._page, self._numpages)

        return (pixbuf, self._name, page, self)
    
    def pack(self):
        """Return a tuple suitable for pickling. The bookmark can be fully
        re-created using the values in the tuple.
        """
        return (self._name, self._path, self._page, self._numpages,
            self._archive_type)

# vim: expandtab:sw=4:ts=4

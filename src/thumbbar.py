"""thumbbar.py - Thumbnail sidebar for main window."""

import urllib

import gtk
import gobject
import Image
import ImageDraw

import image
from preferences import prefs
import thumbnail


class ThumbnailSidebar(gtk.HBox):

    """A thumbnail sidebar including scrollbar for the main window."""

    def __init__(self, window):
        gtk.HBox.__init__(self, False, 0)
        self._window = window
        self._loaded = False
        self._load_task = None
        self._height = 0

        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf)
        self._treeview = gtk.TreeView(self._liststore)

        self._treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
            [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)

        self._column = gtk.TreeViewColumn(None)
        cellrenderer = gtk.CellRendererPixbuf()
        self._layout = gtk.Layout()
        self._layout.put(self._treeview, 0, 0)
        self._column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self._treeview.append_column(self._column)
        self._column.pack_start(cellrenderer, True)
        self._column.set_attributes(cellrenderer, pixbuf=0)
        self._column.set_fixed_width(prefs['thumbnail size'] + 7)
        self._layout.set_size_request(prefs['thumbnail size'] + 7, 0)
        self._treeview.set_headers_visible(False)
        self._vadjust = self._layout.get_vadjustment()
        self._vadjust.step_increment = 15
        self._vadjust.page_increment = 1
        self._scroll = gtk.VScrollbar(None)
        self._scroll.set_adjustment(self._vadjust)
        self._selection = self._treeview.get_selection()

        self.pack_start(self._layout)
        self.pack_start(self._scroll)
        
        self._treeview.connect_after('drag_begin', self._drag_begin)
        self._treeview.connect('drag_data_get', self._drag_data_get)
        self._selection.connect('changed', self._selection_event)
        self._layout.connect('scroll_event', self._scroll_event)

    def get_width(self):
        """Return the width in pixels of the ThumbnailSidebar."""
        return self._layout.size_request()[0] + self._scroll.size_request()[0]

    def show(self, *args):
        """Show the ThumbnailSidebar."""
        self.show_all()

    def hide(self):
        """Hide the ThumbnailSidebar."""
        self.hide_all()

    def clear(self):
        """Clear the ThumbnailSidebar of any loaded thumbnails."""
        self._liststore.clear()
        self._layout.set_size(0, 0)
        self._height = 0
        self._loaded = False
        self._stop_update = True

    def resize(self):
        """Reload the thumbnails with the size specified by in the
        preferences.
        """
        self._column.set_fixed_width(prefs['thumbnail size'] + 7)
        self._layout.set_size_request(prefs['thumbnail size'] + 7, 0)
        self.clear()
        self.load_thumbnails()

    def load_thumbnails(self):
        """Load the thumbnails, if it is appropriate to do so."""
        if (self._loaded or not self._window.file_handler.file_loaded or
          not prefs['show thumbnails'] or prefs['hide all'] or
          (self._window.is_fullscreen and prefs['hide all in fullscreen'])):
            return

        self._loaded = True
        if self._load_task is not None:
            gobject.source_remove(self._load_task)
        self._load_task = gobject.idle_add(self._load)

    def update_select(self):
        """Select the thumbnail for the currently viewed page and make sure
        that the thumbbar is scrolled so that the selected thumb is in view.
        """
        if not self._loaded:
            return
        self._selection.select_path(
            self._window.file_handler.get_current_page() - 1)
        rect = self._treeview.get_background_area(
            self._window.file_handler.get_current_page() - 1, self._column)
        if (rect.y < self._vadjust.get_value() or rect.y + rect.height >
          self._vadjust.get_value() + self._vadjust.page_size):
            value = rect.y + (rect.height // 2) - (self._vadjust.page_size // 2)
            value = max(0, value)
            value = min(self._vadjust.upper - self._vadjust.page_size, value)
            self._vadjust.set_value(value)

    def _load(self):
        if self._window.file_handler.archive_type is not None:
            create = False
        else:
            create = prefs['create thumbnails']
        self._stop_update = False
        for i in xrange(1, self._window.file_handler.get_number_of_pages() + 1):
            pixbuf = self._window.file_handler.get_thumbnail(i,
                prefs['thumbnail size'], prefs['thumbnail size'], create)
            if prefs['show page numbers on thumbnails']:
                _add_page_number(pixbuf, i)
            pixbuf = image.add_border(pixbuf, 1)
            self._liststore.append([pixbuf])
            while gtk.events_pending():
                gtk.main_iteration(False)
            if self._stop_update:
                return
            self._height += self._treeview.get_background_area(i - 1,
                self._column).height
            self._layout.set_size(0, self._height)
        self._stop_update = True
        self.update_select()
    
    def _get_selected_row(self):
        """Return the index of the currently selected row."""
        try:
            return self._selection.get_selected_rows()[1][0][0]
        except Exception:
            return None

    def _selection_event(self, tree_selection):
        """Handle events due to changed thumbnail selection."""
        try:
            self._window.set_page(self._get_selected_row() + 1)
        except Exception:
            pass

    def _scroll_event(self, widget, event):
        """Handle scroll events on the thumbnail sidebar."""
        if event.direction == gtk.gdk.SCROLL_UP:
            self._vadjust.set_value(self._vadjust.get_value() - 60)
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            upper = self._vadjust.upper - self._vadjust.page_size
            self._vadjust.set_value(min(self._vadjust.get_value() + 60, upper))

    def _drag_data_get(self, treeview, context, selection, *args):
        """Put the URI of the selected file into the SelectionData, so that
        the file can be copied (e.g. to a file manager).
        """
        try:
            selected = self._get_selected_row()
            path = self._window.file_handler.get_path_to_page(selected + 1)
            uri = 'file://localhost' + urllib.pathname2url(path)
            selection.set_uris([uri])
        except Exception:
            pass

    def _drag_begin(self, treeview, context):
        """We hook up on drag_begin events so that we can set the hotspot
        for the cursor at the top left corner of the thumbnail (so that we
        might actually see where we are dropping!).
        """
        path = treeview.get_cursor()[0]
        pixmap = treeview.create_row_drag_icon(path)
        # context.set_icon_pixmap() seems to cause crashes, so we do a
        # quick and dirty conversion to pixbuf.
        pointer = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
            *pixmap.get_size())
        pointer = pointer.get_from_drawable(pixmap, treeview.get_colormap(),
            0, 0, 0, 0, *pixmap.get_size())
        context.set_icon_pixbuf(pointer, -5, -5)


def _add_page_number(pixbuf, page):
    """Add page number <page> in a black rectangle in the top left corner of
    <pixbuf>. This is highly dependent on the dimensions of the built-in
    font in PIL (bad). If the PIL font was changed, this function would
    likely produce badly positioned numbers on the pixbuf.
    """
    text = str(page)
    width = min(6 * len(text) + 2, pixbuf.get_width())
    height = min(10, pixbuf.get_height())
    im = Image.new('RGB', (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    draw.text((1, -1), text, fill=(255, 255, 255))
    num_pixbuf = image.pil_to_pixbuf(im)
    num_pixbuf.copy_area(0, 0, width, height, pixbuf, 0, 0)

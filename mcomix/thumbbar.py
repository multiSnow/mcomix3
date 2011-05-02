"""thumbbar.py - Thumbnail sidebar for main window."""

import urllib
import Queue
import gtk
import gobject
import image_tools
import tools
import constants
from preferences import prefs
import threading
import callback

class ThumbnailSidebar(gtk.HBox):

    """A thumbnail sidebar including scrollbar for the main window."""

    def __init__(self, window):
        gtk.HBox.__init__(self, False, 0)

        self._window = window
        # Cache/thumbnail load status
        self._loaded = False
        self._is_loading = False
        self._stop_cacheing = False
        # Caching threads
        self._cache_threads = None

        self._currently_selected_page = 0
        self._selection_is_forced = False

        # models - contains data
        self._thumbnail_liststore = gtk.ListStore(gobject.TYPE_INT, gtk.gdk.Pixbuf)

        # view - responsible for laying out the columns
        self._treeview = gtk.TreeView(self._thumbnail_liststore)

        # enable drag and dropping of images from thumbnail bar to some file
        # manager
        self._treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
            [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)

        self._thumbnail_page_treeviewcolumn = gtk.TreeViewColumn(None)
        self._thumbnail_image_treeviewcolumn = gtk.TreeViewColumn(None)

        self._treeview.append_column(self._thumbnail_page_treeviewcolumn)
        self._treeview.append_column(self._thumbnail_image_treeviewcolumn)

        self._text_cellrenderer = gtk.CellRendererText()
        self._pixbuf_cellrenderer = gtk.CellRendererPixbuf()

        bg_colour = prefs['thumb bg colour']

        self._pixbuf_cellrenderer.set_property('cell-background-gdk', gtk.gdk.colormap_get_system().alloc_color(gtk.gdk.Color(
                    bg_colour[0], bg_colour[1], bg_colour[2]), False, True))
        self._text_cellrenderer.set_property('background-gdk', gtk.gdk.colormap_get_system().alloc_color(gtk.gdk.Color(
                    bg_colour[0], bg_colour[1], bg_colour[2]), False, True))

        self._thumbnail_page_treeviewcolumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        self._thumbnail_page_treeviewcolumn.pack_start(self._text_cellrenderer, False)
        self._thumbnail_page_treeviewcolumn.add_attribute(self._text_cellrenderer, 'text', 0 )

        if not prefs['show page numbers on thumbnails']:
            self._thumbnail_page_treeviewcolumn.set_property('visible',False)

        self._thumbnail_image_treeviewcolumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._thumbnail_image_treeviewcolumn.pack_start(self._pixbuf_cellrenderer, True)
        self._thumbnail_image_treeviewcolumn.add_attribute(self._pixbuf_cellrenderer, 'pixbuf', 1)
        self._thumbnail_image_treeviewcolumn.set_alignment(0.0)

        self._layout = gtk.Layout()
        self._layout.put(self._treeview, 0, 0)

        self.update_layout_size()

        self._treeview.set_headers_visible(False)

        self._vadjust = self._layout.get_vadjustment()
        self._vadjust.step_increment = 15
        self._vadjust.page_increment = 1
        self._scroll = gtk.VScrollbar(None)
        self._scroll.set_adjustment(self._vadjust)

        self._selection = self._treeview.get_selection()

        self.pack_start(self._layout)
        self.pack_start(self._scroll)

        self._treeview.connect('columns-changed', self.refresh)
        self._treeview.connect('expose-event', self.refresh)
        self._treeview.connect_after('drag_begin', self._drag_begin)
        self._treeview.connect('drag_data_get', self._drag_data_get)
        self._selection.connect('changed', self._selection_event)
        self._layout.connect('scroll_event', self._scroll_event)

        self.show_all()

    def toggle_page_numbers_visible(self):

        if prefs['show page numbers on thumbnails']:
            self._thumbnail_page_treeviewcolumn.set_property('visible',True)
        else:
            self._thumbnail_page_treeviewcolumn.set_property('visible',False)

        self.update_layout_size()

    def update_layout_size(self):

        new_width = prefs['thumbnail size'] + 9

        if self._window.filehandler.file_loaded and prefs['show page numbers on thumbnails']:
            new_width += tools.number_of_digits(self._window.imagehandler.get_number_of_pages()) * 10

            if prefs['thumbnail size'] <= 65:
                new_width += 8

        self._layout.set_size_request(new_width, -1)
        self._treeview.set_size_request(new_width, -1)

    def get_width(self):
        """Return the width in pixels of the ThumbnailSidebar."""
        return self._layout.size_request()[0] + self._scroll.size_request()[0]

    def show(self, *args):
        """Show the ThumbnailSidebar."""
        self.show_all()
        self.load_thumbnails(True)

    def hide(self):
        """Hide the ThumbnailSidebar."""
        self.hide_all()

    def clear(self):
        """Clear the ThumbnailSidebar of any loaded thumbnails."""

        self._stop_cacheing = True
        if self._cache_threads is not None:
            for thread in self._cache_threads:
                thread.join()

        self._thumbnail_liststore.clear()
        self._layout.set_size(0, 0)
        self.hide()
        self._loaded = False
        self._is_loading = False
        self._stop_cacheing = False
        self._cache_threads = None
        self._currently_selected_page = 0

    def load_thumbnails(self, force_load=False):
        """Load the thumbnails, if it is appropriate to do so."""

        if (not self._window.filehandler.file_loaded or
            self._window.imagehandler.get_number_of_pages() == 0 or
            self._is_loading or self._loaded or self._stop_cacheing):
            return

        self._load(force_load)

    def refresh(self, *args):
        if not self._is_loading:
            self._layout.set_size(0, self.get_needed_thumbnail_height())

    def remove_thumbnail(self, num_of_thumbnail):

        if not self._loaded and len(self._window.filehandler._image_files) > 1:
            return

        iterator = self._thumbnail_liststore.iter_nth_child( None, num_of_thumbnail )
        self._thumbnail_liststore.remove( iterator )

        image_height = self._treeview.get_background_area(num_of_thumbnail,
            self._thumbnail_image_treeviewcolumn).height + 2

        self._layout.set_size(0, self._layout.get_size()[1] - image_height)

    def resize(self):
        """Reload the thumbnails with the size specified by in the
        preferences.
        """
        self.clear()
        self.load_thumbnails()

    def update_select(self):
        """Select the thumbnail for the currently viewed page and make sure
        that the thumbbar is scrolled so that the selected thumb is in view.
        """

        # this is set to True so that when the event 'scroll-event' is triggered
        # the function _scroll_event will not automatically jump to that page.
        # this allows for the functionality that when going to a previous page the
        # main window will start at the bottom of the image.
        self._selection_is_forced = True
        self._selection.select_path(
            self._window.imagehandler.get_current_page() - 1)

        rect = self._treeview.get_background_area(
            self._window.imagehandler.get_current_page() - 1, self._thumbnail_image_treeviewcolumn)

        if (rect.y < self._vadjust.get_value() or rect.y + rect.height >
          self._vadjust.get_value() + self._vadjust.page_size):

            value = rect.y + (rect.height // 2) - (self._vadjust.page_size // 2)
            value = max(0, value)
            value = min(self._vadjust.upper - self._vadjust.page_size, value)

            self._vadjust.set_value(value)

    def thread_cache_thumbnails(self):
        """Start threaded thumb cacheing.
        """

        # Get numbers of pages that need to be cached.
        thumbnails_needed = Queue.Queue()
        page_count = self._window.imagehandler.get_number_of_pages()
        for page in xrange(1, page_count + 1):
            thumbnails_needed.put(page)

        # Start worker threads
        thread_count = 3
        self._cache_threads = [
            threading.Thread(target=self.cache_thumbnails, args=(thumbnails_needed,))
            for _ in range(thread_count) ]

        for thread in self._cache_threads:
            thread.setDaemon(True)
            thread.start()

    def cache_thumbnails(self, pages):
        """ Done by worker threads to create pixbufs for the
        pages passed into <pages>. """
        while not self._stop_cacheing and not pages.empty():
            try:
                page = pages.get_nowait()
            except Queue.Empty:
                break
            pixbuf = self._window.imagehandler.get_thumbnail(page,
                prefs['thumbnail size'], prefs['thumbnail size']) or \
                    constants.MISSING_IMAGE_ICON
            pixbuf = image_tools.add_border(pixbuf, 1)
            pages.task_done()

            if not self._stop_cacheing:
                self.thumbnail_loaded(page, pixbuf)

        if not self._stop_cacheing:
            pages.join()
            self._loaded = True

        self._is_loading = False

    @callback.Callback
    def thumbnail_loaded(self, page, pixbuf):
        """ Callback when a new thumbnail has been created.
        <pixbuf_info> is a tuple of (page, pixbuf). """
        iter = self._thumbnail_liststore.iter_nth_child(None, page - 1)
        if iter and self._thumbnail_liststore.iter_is_valid(iter):
            self._thumbnail_liststore.set(iter, 0, page, 1, pixbuf)

        if self._loaded:
            # Update height
            self._layout.set_size(0, self.get_needed_thumbnail_height())

    def _load(self, force_load=False):
        # Create empty preview thumbnails.
        filler = self.get_empty_thumbnail()
        page_count = self._window.imagehandler.get_number_of_pages()
        while len(self._thumbnail_liststore) < page_count:
            self._thumbnail_liststore.append([len(self._thumbnail_liststore) + 1, filler])

        if force_load or prefs['show thumbnails'] or not prefs['delay thumbnails']:
            # Start threads for thumbnailing.
            self._loaded = False
            self._is_loading = True
            self._stop_cacheing = False
            self.thread_cache_thumbnails()

        if not prefs['show thumbnails']:
            # The control needs to be exposed at least once to enable height
            # calculation.
            self.show_all()
            self.hide_all()

        # Update layout and current image selection in the thumb bar.
        self.update_layout_size()
        self.update_select()
        # Set height appropriate for dummy pixbufs.
        if not self._loaded:
            pixbuf_padding = 2
            self._layout.set_size(0,
                filler.get_height() * page_count +
                pixbuf_padding * page_count)

    def get_thumbnail(self, page):
        """ Gets the thumbnail pixbuf for the selected <page>.
        Numbering of <page> starts with 1. """

        iter = self._thumbnail_liststore.iter_nth_child(None, page - 1)
        if iter and self._thumbnail_liststore.iter_is_valid(iter):
            return self._thumbnail_liststore.get_value(iter, 1)
        else:
            return get_empty_thumbnail()

    def get_needed_thumbnail_height(self):
        """ Gets the height for all thumbnails, as indicated by the treeview. """
        pages = len(self._thumbnail_liststore)
        height = 0
        for page in xrange(pages):
            height += self._treeview.get_background_area(page,
                self._thumbnail_image_treeviewcolumn).height
        return height

    def _get_selected_row(self):
        """Return the index of the currently selected row."""
        try:
            return self._selection.get_selected_rows()[1][0][0]

        except Exception:
            return None

    def _selection_event(self, tree_selection, *args):
        """Handle events due to changed thumbnail selection."""

        if not self._window.was_out_of_focus:
            try:
                selected_row = self._get_selected_row()
                self._currently_selected_page = selected_row

                if not self._selection_is_forced:
                    self._window.set_page(selected_row + 1)

            except Exception:
                pass

        else:

            # if the window was out of focus and the user clicks on
            # the thumbbar then do not select that page because they
            # more than likely have many pages open and are simply trying
            # to give mcomix focus again
            self._selection.select_path(self._currently_selected_page)
            self._window.was_out_of_focus = False

        self._selection_is_forced = False

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
            path = self._window.imagehandler.get_path_to_page(selected + 1)
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

    def change_thumbnail_background_color(self, colour):

        self.set_thumbnail_background(colour)

        # this hides or shows the HBox and quickly hides/shows it.
        # this allows the thumbnail background to update
        # when changing the color.  if there is a better
        # or easier way to force a refresh I have not found it.

        if prefs['show thumbnails'] and not (self._window.is_fullscreen and prefs['hide all in fullscreen']):
            self.hide_all()
            self.show_all()
        else:
            self.show_all()
            self.hide_all()

        while gtk.events_pending():
            gtk.main_iteration(False)

    def get_empty_thumbnail(self):
        """ Create an empty filler pixmap. """
        pixbuf = gtk.gdk.Pixbuf(colorspace=gtk.gdk.COLORSPACE_RGB,
                has_alpha=True,
                bits_per_sample=8,
                width=prefs['thumbnail size'], height=prefs['thumbnail size'])

        # Make the pixbuf transparent.
        pixbuf.fill(0)

        return pixbuf

    def set_thumbnail_background(self, colour):

        self._pixbuf_cellrenderer.set_property(
                'cell-background-gdk',
                gtk.gdk.colormap_get_system().alloc_color(
                    gtk.gdk.Color(colour[0], colour[1], colour[2]),
                    False, True))

        self._text_cellrenderer.set_property(
                'background-gdk',
                gtk.gdk.colormap_get_system().alloc_color(
                    gtk.gdk.Color(colour[0], colour[1], colour[2]),
                    False, True))

# vim: expandtab:sw=4:ts=4

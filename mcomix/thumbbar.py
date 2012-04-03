"""thumbbar.py - Thumbnail sidebar for main window."""

import urllib
import Queue
import gtk
import gobject
import threading

from mcomix.preferences import prefs
from mcomix import image_tools
from mcomix import tools
from mcomix import constants
from mcomix import callback
from mcomix import thumbnail_view


class ThumbnailSidebar(gtk.ScrolledWindow):

    """A thumbnail sidebar including scrollbar for the main window."""

    def __init__(self, window):
        gtk.ScrolledWindow.__init__(self)

        self._window = window
        #: Thumbnail load status
        self._loaded = False
        #: Selected page in treeview
        self._currently_selected_page = 0
        self._selection_is_forced = False

        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_ALWAYS)
        self.get_vadjustment().step_increment = 15
        self.get_vadjustment().page_increment = 1

        # models - contains data
        self._thumbnail_liststore = gtk.ListStore(gobject.TYPE_INT,
            gtk.gdk.Pixbuf, gobject.TYPE_BOOLEAN)

        # view - responsible for laying out the columns
        self._treeview = thumbnail_view.ThumbnailTreeView(self._thumbnail_liststore)
        self._treeview.unset_flags(gtk.DOUBLE_BUFFERED) # Prevents flickering on update
        self._treeview.set_headers_visible(False)
        self._treeview.pixbuf_column = 1
        self._treeview.status_column = 2
        # This method isn't necessary, as generate_thumbnail doesn't need the path
        self._treeview.get_file_path_from_model = lambda *args: None
        self._treeview.generate_thumbnail = self._generate_thumbnail

        self._treeview.connect_after('drag_begin', self._drag_begin)
        self._treeview.connect('drag_data_get', self._drag_data_get)
        self._treeview.get_selection().connect('changed', self._selection_event)

        # enable drag and dropping of images from thumbnail bar to some file
        # manager
        self._treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
            [('text/uri-list', 0, 0)], gtk.gdk.ACTION_COPY)

        bg_colour = prefs['thumb bg colour']

        # Page column
        self._thumbnail_page_treeviewcolumn = gtk.TreeViewColumn(None)
        self._treeview.append_column(self._thumbnail_page_treeviewcolumn)

        self._text_cellrenderer = gtk.CellRendererText()
        self._text_cellrenderer.set_property('background-gdk',
            gtk.gdk.colormap_get_system().alloc_color(gtk.gdk.Color(
                bg_colour[0], bg_colour[1], bg_colour[2]), False, True))

        self._thumbnail_page_treeviewcolumn.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        self._thumbnail_page_treeviewcolumn.pack_start(self._text_cellrenderer, False)
        self._thumbnail_page_treeviewcolumn.add_attribute(self._text_cellrenderer, 'text', 0)

        if not prefs['show page numbers on thumbnails']:
            self._thumbnail_page_treeviewcolumn.set_property('visible', False)

        # Pixbuf column
        self._thumbnail_image_treeviewcolumn = gtk.TreeViewColumn(None)
        self._treeview.append_column(self._thumbnail_image_treeviewcolumn)

        self._pixbuf_cellrenderer = gtk.CellRendererPixbuf()
        self._pixbuf_cellrenderer.set_property('cell-background-gdk',
            gtk.gdk.colormap_get_system().alloc_color(gtk.gdk.Color(
                bg_colour[0], bg_colour[1], bg_colour[2]), False, True))

        self._thumbnail_image_treeviewcolumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._thumbnail_image_treeviewcolumn.pack_start(self._pixbuf_cellrenderer, True)
        self._thumbnail_image_treeviewcolumn.add_attribute(self._pixbuf_cellrenderer, 'pixbuf', 1)
        self._thumbnail_image_treeviewcolumn.set_alignment(0.0)

        self.add(self._treeview)
        self.update_layout_size()
        self.show_all()

    def toggle_page_numbers_visible(self):
        """ Enables or disables page numbers on the thumbnail bar. """

        if prefs['show page numbers on thumbnails']:
            self._thumbnail_page_treeviewcolumn.set_property('visible', True)
        else:
            self._thumbnail_page_treeviewcolumn.set_property('visible', False)

        self.update_layout_size()

    def update_layout_size(self):
        """ Updates the thumbnail bar's width to fit to thumbnail size. """

        new_width = prefs['thumbnail size'] + 9

        if (self._window.filehandler.file_loaded and
            prefs['show page numbers on thumbnails']):

            new_width += tools.number_of_digits(
                self._window.imagehandler.get_number_of_pages()) * 10

            if prefs['thumbnail size'] <= 65:
                new_width += 8

        self._treeview.set_size_request(new_width, -1)

    def get_width(self):
        """Return the width in pixels of the ThumbnailSidebar."""
        return self.size_request()[0]

    def show(self, *args):
        """Show the ThumbnailSidebar."""
        self.show_all()
        self.load_thumbnails()

    def hide(self):
        """Hide the ThumbnailSidebar."""
        self.hide_all()

    def clear(self):
        """Clear the ThumbnailSidebar of any loaded thumbnails."""

        self._treeview.stop_update()
        self._thumbnail_liststore.clear()
        self.hide()
        self._loaded = False
        self._currently_selected_page = 0

    def load_thumbnails(self):
        """Load the thumbnails, if it is appropriate to do so."""

        if (not self._window.filehandler.file_loaded or
            self._window.imagehandler.get_number_of_pages() == 0 or
            self._loaded):
            return

        self._load()

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
        path = self._window.imagehandler.get_current_page() - 1
        self._treeview.get_selection().select_path(path)
        self._treeview.scroll_to_cell(path)

    def change_thumbnail_background_color(self, colour):
        """ Changes the background color of the thumbnail bar. """

        self.set_thumbnail_background(colour)

        # this hides or shows the control and quickly hides/shows it.
        # this allows the thumbnail background to update
        # when changing the color.  if there is a better
        # or easier way to force a refresh I have not found it.

        if (prefs['show thumbnails'] and
            not (self._window.is_fullscreen and
                 prefs['hide all in fullscreen'])):
            self.hide_all()
            self.show_all()
        else:
            self.show_all()
            self.hide_all()

        while gtk.events_pending():
            gtk.main_iteration(False)

    def set_thumbnail_background(self, colour):

        color = gtk.gdk.colormap_get_system().alloc_color(
                    gtk.gdk.Color(colour[0], colour[1], colour[2]),
                    False, True)
        self._pixbuf_cellrenderer.set_property('cell-background-gdk',
                color)
        self._text_cellrenderer.set_property('background-gdk',
                color)

    def _load(self):
        # Detach model for performance reasons
        model = self._treeview.get_model()
        self._treeview.set_model(None)

        # Create empty preview thumbnails.
        filler = self._get_empty_thumbnail()
        page_count = self._window.imagehandler.get_number_of_pages()
        while len(self._thumbnail_liststore) < page_count:
            self._thumbnail_liststore.append(
                [len(self._thumbnail_liststore) + 1, filler, False])

        self._loaded = True

        # Re-attach model
        self._treeview.set_model(model)

        if not prefs['show thumbnails']:
            # The control needs to be exposed at least once to enable height
            # calculation.
            self.show_all()
            self.hide_all()

        # Update layout and current image selection in the thumb bar.
        self.update_layout_size()
        self.update_select()

    def _generate_thumbnail(self, file_path, model, path):
        """ Generate the pixbuf for C{path} at demand. """
        if isinstance(path, tuple):
            page = path[0] + 1
        elif isinstance(path, int):
            page = path + 1
        elif path is None:
            return constants.MISSING_IMAGE_ICON
        else:
            assert False, "Expected int or tuple as tree path."

        pixbuf = self._window.imagehandler.get_thumbnail(page,
                prefs['thumbnail size'], prefs['thumbnail size']) or \
            constants.MISSING_IMAGE_ICON
        pixbuf = image_tools.add_border(pixbuf, 1)

        return pixbuf

    def _get_selected_row(self):
        """Return the index of the currently selected row."""
        try:
            return self._treeview.get_selection().get_selected_rows()[1][0][0]

        except IndexError:
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
            path = self._currently_selected_page
            self._treeview.get_selection().select_path(path)
            self._treeview.scroll_to_cell(path)
            self._window.was_out_of_focus = False

        self._selection_is_forced = False

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


    def _get_empty_thumbnail(self):
        """ Create an empty filler pixmap. """
        pixbuf = gtk.gdk.Pixbuf(colorspace=gtk.gdk.COLORSPACE_RGB,
                has_alpha=True,
                bits_per_sample=8,
                width=prefs['thumbnail size'], height=prefs['thumbnail size'])

        # Make the pixbuf transparent.
        pixbuf.fill(0)

        return pixbuf


# vim: expandtab:sw=4:ts=4

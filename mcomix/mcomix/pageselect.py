"""pageselect.py - The dialog window for the page selector."""

from gi.repository import Gtk

from mcomix.preferences import prefs
from mcomix.worker_thread import WorkerThread
from mcomix import callback


class Pageselector(Gtk.Dialog):

    """The Pageselector takes care of the popup page selector
    """

    def __init__(self, window):
        self._window = window
        super(Pageselector, self).__init__("Go to page...", window,
                                     Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)
        self.add_buttons(_('_Go'), Gtk.ResponseType.OK,
                         _('_Cancel'), Gtk.ResponseType.CANCEL,)
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect('response', self._response)
        self.set_resizable(True)

        self._number_of_pages = self._window.imagehandler.get_number_of_pages()

        self._selector_adjustment = Gtk.Adjustment(value=self._window.imagehandler.get_current_page(),
                              lower=1,upper=self._number_of_pages,
                              step_incr=1, page_incr=1 )

        self._page_selector = Gtk.VScale.new(self._selector_adjustment)
        self._page_selector.set_draw_value(False)
        self._page_selector.set_digits( 0 )

        self._page_spinner = Gtk.SpinButton.new(self._selector_adjustment, 0.0, 0)
        self._page_spinner.connect( 'changed', self._page_text_changed )
        self._page_spinner.set_activates_default(True)
        self._page_spinner.set_numeric(True)
        self._pages_label = Gtk.Label(label=_(' of %s') % self._number_of_pages)
        self._pages_label.set_alignment(0, 0.5)

        self._image_preview = Gtk.Image()
        self._image_preview.set_size_request(
            prefs['thumbnail size'], prefs['thumbnail size'])

        self.connect('configure-event', self._size_changed_cb)
        self.set_size_request(prefs['pageselector width'],
                prefs['pageselector height'])

        # Group preview image and page selector next to each other
        preview_box = Gtk.HBox()
        preview_box.set_border_width(5)
        preview_box.set_spacing(5)
        preview_box.pack_start(self._image_preview, True, True, 0)
        preview_box.pack_end(self._page_selector, False, True, 0)
        # Below them, group selection spinner and current page label
        selection_box = Gtk.HBox()
        selection_box.set_border_width(5)
        selection_box.pack_start(self._page_spinner, True, True, 0)
        selection_box.pack_end(self._pages_label, False, True, 0)

        self.get_content_area().pack_start(preview_box, True, True, 0)
        self.get_content_area().pack_end(selection_box, False, True, 0)
        self.show_all()

        self._selector_adjustment.connect('value-changed', self._cb_value_changed)

        # Set focus on the input box.
        self._page_spinner.select_region(0, -1)
        self._page_spinner.grab_focus()

        # Currently displayed thumbnail page.
        self._thumbnail_page = 0
        self._thread = WorkerThread(self._generate_thumbnail, name='preview')
        self._update_thumbnail(int(self._selector_adjustment.props.value))
        self._window.imagehandler.page_available += self._page_available

    def _cb_value_changed(self, *args):
        """ Called whenever the spinbox value changes. Updates the preview thumbnail. """
        page = int(self._selector_adjustment.props.value)
        if page != self._thumbnail_page:
            self._update_thumbnail(page)

    def _size_changed_cb(self, *args):
        # Window cannot be scaled down unless the size request is reset
        self.set_size_request(-1, -1)
        # Store dialog size
        prefs['pageselector width'] = self.get_allocation().width
        prefs['pageselector height'] = self.get_allocation().height

        self._update_thumbnail(int(self._selector_adjustment.props.value))

    def _page_text_changed(self, control, *args):
        """ Called when the page selector has been changed. Used to instantly update
            the preview thumbnail when entering page numbers by hand. """
        if control.get_text().isdigit():
            page = int(control.get_text())
            if page > 0 and page <= self._number_of_pages:
                control.set_value(page)

    def _response(self, widget, event, *args):
        if event == Gtk.ResponseType.OK:
            self._window.set_page(int(self._selector_adjustment.props.value))

        self._window.imagehandler.page_available -= self._page_available
        self._thread.stop()
        self.destroy()

    def _update_thumbnail(self, page):
        """ Trigger a thumbnail update. """
        width = self._image_preview.get_allocation().width
        height = self._image_preview.get_allocation().height
        self._thumbnail_page = page
        self._thread.clear_orders()
        self._thread.append_order((page, width, height))

    def _generate_thumbnail(self, params):
        """ Generate the preview thumbnail for the page selector.
        A transparent image will be used if the page is not yet available. """
        page, width, height = params

        pixbuf = self._window.imagehandler.get_thumbnail(page,
            width=width, height=height, nowait=True)
        self._thumbnail_finished(page, pixbuf)

    @callback.Callback
    def _thumbnail_finished(self, page, pixbuf):
        # Don't bother if we changed page in the meantime.
        if page == self._thumbnail_page:
            self._image_preview.set_from_pixbuf(pixbuf)

    def _page_available(self, page):
        if page == int(self._selector_adjustment.props.value):
            self._update_thumbnail(page)

# vim: expandtab:sw=4:ts=4

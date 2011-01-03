"""pageselect.py - The dialog window for the page selector."""

import gtk
import image_tools

class Pageselector(gtk.Dialog):

    """The Pageselector takes care of the popup page selector
    """

    def __init__(self, window):
        self._window = window
        self._page_selector_dialog = gtk.Dialog.__init__(self, "Go to page...", window,
                                     gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        self.add_buttons(_('_Go'), gtk.RESPONSE_OK,
                         _('_Cancel'), gtk.RESPONSE_CANCEL,)
        self.set_default_response(gtk.RESPONSE_OK)        
        self.set_has_separator(False)
        self.connect('response', self._response)
        self.set_has_separator(False)
        self.set_resizable(True)
        self.set_default_response(gtk.RESPONSE_CLOSE)

        self._number_of_pages = self._window.imagehandler.get_number_of_pages()

        self._selector_adjustment = gtk.Adjustment(value=self._window.imagehandler.get_current_page(),
                              lower=1,upper=self._number_of_pages,
                              step_incr=1, page_incr=1 )

        self._selector_adjustment.connect( 'value-changed', self._cb_value_changed )

        self._page_selector = gtk.VScale(self._selector_adjustment)
        self._page_selector.set_draw_value(False)

        self._page_selector.set_digits( 0 )

        self._page_spinner = gtk.SpinButton(self._selector_adjustment)
        self._page_spinner.connect( 'value-changed', self._cb_value_changed )
        self._page_spinner.set_activates_default(True)
        self._pages_label = gtk.Label(' of %s' % _(self._number_of_pages))
        self._pages_label.set_alignment(0, 1)

        preview_box = gtk.HBox()
        preview_box.set_size_request(200, 150)

        self._image_preview = gtk.Image()
        self._image_preview.set_from_pixbuf(
                    image_tools.add_border(
                       self._window.thumbnailsidebar._thumb_cache[ 
                            int(self._selector_adjustment.value) - 1 ], 
                        1) )
        preview_box.pack_start(self._image_preview)

        spinner_box = gtk.HBox()
        spinner_box.set_border_width(5)
        spinner_box.pack_start(self._page_spinner, True)
        spinner_box.pack_start(self._pages_label, False)

        left_box = gtk.VBox()
        left_box.pack_start(preview_box, False)
        left_box.pack_start(spinner_box, True)

        main_box = gtk.HBox()
        main_box.pack_start(left_box, False)
        main_box.pack_start(self._page_selector, False, False, 5)

        self.vbox.pack_start(main_box, False)

        self.show_all()

    def _cb_value_changed(self, *args):
        self._image_preview.set_from_pixbuf(
                    image_tools.add_border(
                       self._window.thumbnailsidebar._thumb_cache[ 
                            int(self._selector_adjustment.value) - 1 ], 
                        1) )

        while gtk.events_pending():
            gtk.main_iteration(False)
        
    def _response(self, widget, event, *args):
        if event == gtk.RESPONSE_OK:
            self._window.set_page(int(self._selector_adjustment.value))
            self.emit('close')
        elif event == gtk.RESPONSE_CANCEL: 
            self.emit('close')


# vim: expandtab:sw=4:ts=4

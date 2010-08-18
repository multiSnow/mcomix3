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

        if self._number_of_pages >= 70:
            self.set_size_request(700,250)
        else:
            self.set_size_request(self._number_of_pages * 10,250)

        self._selector_adjustment = gtk.Adjustment(value=self._window.imagehandler.get_current_page(),
                              lower=1,upper=self._number_of_pages,
                              step_incr=1, page_incr=1 )

        self._selector_adjustment.connect( 'value-changed', self._cb_value_changed )

        self._page_selector = gtk.HScale(self._selector_adjustment)

        for i in range(0, self._number_of_pages + 1):
            self._page_selector.add_mark(i,gtk.POS_BOTTOM,None)
            self._page_selector.add_mark(i,gtk.POS_TOP,None)

        self._page_selector.set_digits( 0 )
        self._page_selector.set_size_request(200, 50)

        self.vbox.pack_start(self._page_selector, True)
        self.vbox.pack_start(gtk.HSeparator(), False)
        
        preview_box = gtk.HBox()
        preview_box.set_size_request(200, 150)

        self._image_preview = gtk.Image()
        self._image_preview.set_from_pixbuf(
                    image_tools.add_border(
                       self._window.thumbnailsidebar._thumb_cache[ 
                            int(self._selector_adjustment.value) - 1 ], 
                        1) )
        preview_box.pack_start(self._image_preview)
        
        self.vbox.pack_start(preview_box, True)

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


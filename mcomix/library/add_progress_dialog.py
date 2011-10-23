"""library_add_progress_dialog.py - Progress bar for the library."""

import gtk
import pango

from mcomix import labels

_dialog = None
# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1

class _AddLibraryProgressDialog(gtk.Dialog):

    """Dialog with a ProgressBar that adds books to the library."""

    def __init__(self, library, window, paths, collection):
        """Adds the books at <paths> to the library, and also to the
        <collection>, unless it is None.
        """
        gtk.Dialog.__init__(self, _('Adding books'), library,
            gtk.DIALOG_MODAL, (gtk.STOCK_STOP, gtk.RESPONSE_CLOSE))

        self._window = window
        self._destroy = False
        self.set_size_request(400, -1)
        self.set_has_separator(False)
        self.set_resizable(False)
        self.set_border_width(4)
        self.connect('response', self._response)
        self.set_default_response(gtk.RESPONSE_CLOSE)

        main_box = gtk.VBox(False, 5)
        main_box.set_border_width(6)
        self.vbox.pack_start(main_box, False, False)
        hbox = gtk.HBox(False, 10)
        main_box.pack_start(hbox, False, False, 5)
        left_box = gtk.VBox(True, 5)
        right_box = gtk.VBox(True, 5)
        hbox.pack_start(left_box, False, False)
        hbox.pack_start(right_box, False, False)

        label = labels.BoldLabel(_('Added books:'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True)
        number_label = gtk.Label('0')
        number_label.set_alignment(0, 1.0)
        right_box.pack_start(number_label, True, True)

        bar = gtk.ProgressBar()
        main_box.pack_start(bar, False, False)

        added_label = labels.ItalicLabel()
        added_label.set_alignment(0, 0.5)
        added_label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        main_box.pack_start(added_label, False, False)
        self.show_all()

        total_paths_int = len(paths)
        total_paths_float = float(len(paths))
        total_added = 0

        for path in paths:

            if library.backend.add_book(path, collection):
                total_added += 1

                number_label.set_text('%d / %d' % (total_added, total_paths_int))

            added_label.set_text(_("Adding '%s'...") % path)
            bar.set_fraction(total_added / total_paths_float)

            while gtk.events_pending():
                gtk.main_iteration(False)

            if self._destroy:
                return

        self._response()

    def _response(self, *args):
        self._destroy = True
        self.destroy()

# vim: expandtab:sw=4:ts=4

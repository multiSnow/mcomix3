"""library_add_progress_dialog.py - Progress bar for the library."""

from gi.repository import Gtk
from gi.repository import Pango

from mcomix import labels

_dialog = None
# The "All books" collection is not a real collection stored in the library,
# but is represented by this ID in the library's TreeModels.
_COLLECTION_ALL = -1

class _AddLibraryProgressDialog(Gtk.Dialog):

    """Dialog with a ProgressBar that adds books to the library."""

    def __init__(self, library, window, paths, collection):
        """Adds the books at <paths> to the library, and also to the
        <collection>, unless it is None.
        """
        super(_AddLibraryProgressDialog, self).__init__(_('Adding books'), library,
            Gtk.DialogFlags.MODAL, (Gtk.STOCK_STOP, Gtk.ResponseType.CLOSE))

        self._window = window
        self._destroy = False
        self.set_size_request(400, -1)
        self.set_resizable(False)
        self.set_border_width(4)
        self.connect('response', self._response)
        self.set_default_response(Gtk.ResponseType.CLOSE)

        main_box = Gtk.VBox(False, 5)
        main_box.set_border_width(6)
        self.vbox.pack_start(main_box, False, False, 0)
        hbox = Gtk.HBox(False, 10)
        main_box.pack_start(hbox, False, False, 5)
        left_box = Gtk.VBox(True, 5)
        right_box = Gtk.VBox(True, 5)
        hbox.pack_start(left_box, False, False, 0)
        hbox.pack_start(right_box, False, False, 0)

        label = labels.BoldLabel(_('Added books:'))
        label.set_alignment(1.0, 1.0)
        left_box.pack_start(label, True, True, 0)
        number_label = Gtk.Label(label='0')
        number_label.set_alignment(0, 1.0)
        right_box.pack_start(number_label, True, True, 0)

        bar = Gtk.ProgressBar()
        main_box.pack_start(bar, False, False, 0)

        added_label = labels.ItalicLabel()
        added_label.set_alignment(0, 0.5)
        added_label.set_width_chars(64)
        added_label.set_max_width_chars(64)
        added_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        main_box.pack_start(added_label, False, False, 0)
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

            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

            if self._destroy:
                return

        self._response()

    def _response(self, *args):
        self._destroy = True
        self.destroy()

# vim: expandtab:sw=4:ts=4

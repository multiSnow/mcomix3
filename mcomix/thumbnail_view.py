""" gtk.IconView subclass for dynamically generated thumbnails. """

import Queue
import gtk
import gobject

from mcomix.preferences import prefs
from mcomix.worker_thread import WorkerThread


class ThumbnailViewBase(object):
    """ This class provides shared functionality for gtk.TreeView and
    gtk.IconView. Instantiating this class directly is *impossible*,
    as it depends on methods provided by the view classes. """

    def __init__(self, model):
        """ Constructs a new ThumbnailView.
        @param model: L{gtk.TreeModel} instance. The model needs a pixbuf
                      and a boolean column for internal calculations.
        """

        #: Model index of the thumbnail status field (gobject.BOOLEAN)
        self.status_column = -1
        #: Model index of the pixbuf field
        self.pixbuf_column = -1

        #: Worker thread
        self._thread = WorkerThread(self._pixbuf_worker,
                                    name='thumbview',
                                    unique_orders=True,
                                    max_threads=prefs["max threads"])

    def generate_thumbnail(self, file_path, model, path):
        """ This function must return the thumbnail for C{file_path}.
        C{model} and {path} point at the relevant model line. """
        raise NotImplementedError()

    def get_file_path_from_model(self, model, iter):
        """ This function should retrieve a file path from C{model},
        the current row being specified by C{iter}. """
        raise NotImplementedError()

    def get_visible_range(self):
        """ See L{gtk.IconView.get_visible_range}. """
        raise NotImplementedError()

    def stop_update(self):
        """ Stops generation of pixbufs. """
        self._thread.stop()

    def draw_thumbnails_on_screen(self, *args):
        """ Prepares valid thumbnails for currently displayed icons.
        This method is supposed to be called from the expose-event
        callback function. """

        visible = self.get_visible_range()
        if not visible:
            # No valid paths available
            return

        # Flush current pixmap generation orders.
        self._thread.clear_orders()

        pixbufs_needed = []
        start = visible[0][0]
        end = visible[1][0]
        # Read ahead/back and start caching a few more icons. Currently invisible
        # icons are always cached only after the visible icons have been completed.
        additional = (end - start) // 2
        required = range(start, end + additional + 1) + \
                   range(max(0, start - additional), start)
        model = self.get_model()
        for path in required:
            try:
                iter = model.get_iter(path)
            except ValueError:
                iter = None

            # Do not queue again if cover was already created
            if (iter is not None and
                not model.get_value(iter, self.status_column)):

                file_path = self.get_file_path_from_model(model, iter)
                pixbufs_needed.append((file_path, path))

        if len(pixbufs_needed) > 0:
            self._thread.extend_orders(pixbufs_needed)

    def _pixbuf_worker(self, order):
        """ Run by a worker thread to generate the thumbnail for a path."""
        file_path, path = order
        pixbuf = self.generate_thumbnail(file_path, path)
        if pixbuf is not None:
            gobject.idle_add(self._pixbuf_finished, path, pixbuf)

    def _pixbuf_finished(self, path, pixbuf):
        """ Executed when a pixbuf was created, to actually insert the pixbuf
        into the view store. C{pixbuf_info} is a tuple containing
        (index, pixbuf). """

        model = self.get_model()
        if model is None:
            return 0
        iter = model.get_iter(path)
        model.set(iter, self.pixbuf_column, pixbuf)
        # Mark as generated
        model.set_value(iter, self.status_column, True)

        # Remove this idle handler.
        return 0

class ThumbnailIconView(gtk.IconView, ThumbnailViewBase):
    def __init__(self, model):
        gtk.IconView.__init__(self, model)
        ThumbnailViewBase.__init__(self, model)

        # Connect events
        self.connect('expose-event', self.draw_thumbnails_on_screen)

    def get_visible_range(self):
        return gtk.IconView.get_visible_range(self)

class ThumbnailTreeView(gtk.TreeView, ThumbnailViewBase):
    def __init__(self, model):
        gtk.TreeView.__init__(self, model)
        ThumbnailViewBase.__init__(self, model)

        # Connect events
        self.connect('expose-event', self.draw_thumbnails_on_screen)

    def get_visible_range(self):
        return gtk.TreeView.get_visible_range(self)

# vim: expandtab:sw=4:ts=4

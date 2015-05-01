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

    def __init__(self, uid_column, pixbuf_column, status_column):
        """ Constructs a new ThumbnailView.
        @param uid_column: index of unique identifer column.
        @param pixbuf_column: index of pixbuf column.
        @param status_column: index of status boolean column
                              (True if pixbuf is not temporary filler)
        """

        #: Keep track of already generated thumbnails.
        self._uid_column = uid_column
        self._pixbuf_column = pixbuf_column
        self._status_column = status_column

        #: Ignore updates when this flag is True.
        self._updates_stopped = True
        #: Worker thread
        self._thread = WorkerThread(self._pixbuf_worker,
                                    name='thumbview',
                                    unique_orders=True,
                                    max_threads=prefs["max threads"])

    def generate_thumbnail(self, uid):
        """ This function must return the thumbnail for C{uid}. """
        raise NotImplementedError()

    def get_visible_range(self):
        """ See L{gtk.IconView.get_visible_range}. """
        raise NotImplementedError()

    def stop_update(self):
        """ Stops generation of pixbufs. """
        self._updates_stopped = True
        self._thread.stop()

    def draw_thumbnails_on_screen(self, *args):
        """ Prepares valid thumbnails for currently displayed icons.
        This method is supposed to be called from the expose-event
        callback function. """

        visible = self.get_visible_range()
        if not visible:
            # No valid paths available
            return

        pixbufs_needed = []
        start = visible[0][0]
        end = visible[1][0]
        # Read ahead/back and start caching a few more icons. Currently invisible
        # icons are always cached only after the visible icons have been completed.
        additional = (end - start) // 2
        required = range(start, end + additional + 1) + \
                   range(max(0, start - additional), start)
        model = self.get_model()
        # Filter invalid paths.
        required = [path for path in required if 0 <= path < len(model)]
        with self._thread:
            # Flush current pixmap generation orders.
            self._thread.clear_orders()
            for path in required:
                iter = model.get_iter(path)
                uid, generated = model.get(iter,
                                           self._uid_column,
                                           self._status_column)
                # Do not queue again if thumbnail was already created.
                if not generated:
                    pixbufs_needed.append((uid, iter))
            if len(pixbufs_needed) > 0:
                self._updates_stopped = False
                self._thread.extend_orders(pixbufs_needed)

    def _pixbuf_worker(self, order):
        """ Run by a worker thread to generate the thumbnail for a path."""
        uid, iter = order
        pixbuf = self.generate_thumbnail(uid)
        if pixbuf is not None:
            gobject.idle_add(self._pixbuf_finished, iter, pixbuf)

    def _pixbuf_finished(self, iter, pixbuf):
        """ Executed when a pixbuf was created, to actually insert the pixbuf
        into the view store. C{pixbuf_info} is a tuple containing
        (index, pixbuf). """

        if self._updates_stopped:
            return 0

        model = self.get_model()
        model.set(iter, self._status_column, True, self._pixbuf_column, pixbuf)

        # Remove this idle handler.
        return 0

class ThumbnailIconView(gtk.IconView, ThumbnailViewBase):
    def __init__(self, model, uid_column, pixbuf_column, status_column):
        assert gtk.TREE_MODEL_ITERS_PERSIST == (model.get_flags() & gtk.TREE_MODEL_ITERS_PERSIST)
        super(ThumbnailIconView, self).__init__(model)
        ThumbnailViewBase.__init__(self, uid_column, pixbuf_column, status_column)
        self.set_pixbuf_column(pixbuf_column)

        # Connect events
        self.connect('expose-event', self.draw_thumbnails_on_screen)

    def get_visible_range(self):
        return gtk.IconView.get_visible_range(self)

class ThumbnailTreeView(gtk.TreeView, ThumbnailViewBase):
    def __init__(self, model, uid_column, pixbuf_column, status_column):
        assert gtk.TREE_MODEL_ITERS_PERSIST == (model.get_flags() & gtk.TREE_MODEL_ITERS_PERSIST)
        super(ThumbnailTreeView, self).__init__(model)
        ThumbnailViewBase.__init__(self, uid_column, pixbuf_column, status_column)

        # Connect events
        self.connect('expose-event', self.draw_thumbnails_on_screen)

    def get_visible_range(self):
        return gtk.TreeView.get_visible_range(self)

# vim: expandtab:sw=4:ts=4

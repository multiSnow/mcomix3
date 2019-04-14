''' Gtk.IconView subclass for dynamically generated thumbnails. '''

from gi.repository import Gtk
from gi.repository import GLib

from mcomix.lib import mt
from mcomix.preferences import prefs


class ThumbnailViewBase(object):
    ''' This class provides shared functionality for Gtk.TreeView and
    Gtk.IconView. Instantiating this class directly is *impossible*,
    as it depends on methods provided by the view classes. '''

    def __init__(self, uid_column, pixbuf_column, status_column):
        ''' Constructs a new ThumbnailView.
        @param uid_column: index of unique identifer column.
        @param pixbuf_column: index of pixbuf column.
        @param status_column: index of status boolean column
                              (True if pixbuf is not temporary filler)
        '''

        #: Keep track of already generated thumbnails.
        self._uid_column = uid_column
        self._pixbuf_column = pixbuf_column
        self._status_column = status_column

        #: Ignore updates when this flag is True.
        self._updates_stopped = True
        #: Worker thread
        self._threadpool = mt.ThreadPool(
            name='thumbview', processes=prefs['max threads'])
        self._lock = mt.Lock()
        self._done = set()

    def generate_thumbnail(self, uid):
        ''' This function must return the thumbnail for C{uid}. '''
        raise NotImplementedError()

    def stop_update(self):
        ''' Stops generation of pixbufs. '''
        self._updates_stopped = True
        self._done.clear()

    def draw_thumbnails_on_screen(self, *args):
        ''' Prepares valid thumbnails for currently displayed icons.
        This method is supposed to be called from the expose-event
        callback function. '''

        # 'draw' event called too frequently
        if not self._lock.acquire(blocking=False):
            return
        try:
            visible = (args[0] if args else self).get_visible_range()
            if not visible:
                # No valid paths available
                return

            start = visible[0][0]
            end = visible[1][0]

            # Currently invisible icons are always cached
            # only after the visible icons completed.
            mid = (start + end) // 2 + 1
            harf = end - start # twice of current visible length
            required = set(range(mid - harf, mid + harf))

            model = self.get_model()
            required &= set(range(len(model))) # filter invalid paths.
            for path in required:
                iter = model.get_iter(path)
                uid, generated = model.get(
                    iter, self._uid_column, self._status_column)
                # Do not queue again if thumbnail was already created.
                if generated:
                    continue
                if uid in self._done:
                    continue
                self._updates_stopped = False
                self._done.add(uid)
                self._threadpool.apply_async(
                    self._pixbuf_worker, args=(uid, iter, model),
                    callback=self._pixbuf_finished)
        finally:
            self._lock.release()

    def _pixbuf_worker(self, uid, iter, model):
        ''' Run by a worker thread to generate the thumbnail for a path.'''
        if self._updates_stopped:
            raise Exception('stop update, skip callback.')
        pixbuf = self.generate_thumbnail(uid)
        if pixbuf is None:
            self._done.discard(uid)
            raise Exception('no pixbuf, skip callback.')
        return iter, pixbuf, model

    def _pixbuf_finished(self, params):
        ''' Executed when a pixbuf was created, to actually insert the pixbuf
        into the view store. C{params} is a tuple containing
        (index, pixbuf, model). '''

        if self._updates_stopped:
            return 0

        with self._lock:
            iter, pixbuf, model = params
            model.set(iter, self._status_column, True, self._pixbuf_column, pixbuf)

        # Remove this idle handler.
        return 0

class ThumbnailIconView(Gtk.IconView, ThumbnailViewBase):
    def __init__(self, model, uid_column, pixbuf_column, status_column):
        assert 0 != (model.get_flags() & Gtk.TreeModelFlags.ITERS_PERSIST)
        super(ThumbnailIconView, self).__init__(model=model)
        ThumbnailViewBase.__init__(self, uid_column, pixbuf_column, status_column)
        self.set_pixbuf_column(pixbuf_column)

        # Connect events
        self.connect('draw', self.draw_thumbnails_on_screen)

class ThumbnailTreeView(Gtk.TreeView, ThumbnailViewBase):
    def __init__(self, model, uid_column, pixbuf_column, status_column):
        assert 0 != (model.get_flags() & Gtk.TreeModelFlags.ITERS_PERSIST)
        super(ThumbnailTreeView, self).__init__(model=model)
        ThumbnailViewBase.__init__(self, uid_column, pixbuf_column, status_column)

        # Connect events
        self.connect('draw', self.draw_thumbnails_on_screen)

# vim: expandtab:sw=4:ts=4

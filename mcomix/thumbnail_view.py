""" gtk.IconView subclass for dynamically generated thumbnails. """

import threading
import Queue
import gtk
import gobject

from mcomix.preferences import prefs


class ThumbnailView(gtk.IconView):

    def __init__(self, model):
        """ Constructs a new ThumbnailView.
        @param model: L{gtk.TreeModel} instance. The model needs a pixbuf
                      and a boolean column for internal calculations.
        """

        super(ThumbnailView, self).__init__(model)

        #: Model index of the thumbnail status field (gobject.BOOLEAN)
        self._status_column = -1
        #: Internal work queue
        self._queue = Queue.Queue()
        #: Worker threads
        self._threads = []
        #: Maximum thread count
        self._max_threads = prefs["max threads"]
        #: Stop flag that interrupts threads
        self._stop = False

        # Connect events
        self.connect('expose-event', self.draw_thumbnails_on_screen)

    def generate_thumbnail(self, file_path):
        """ This function must return the thumbnail for C{file_path}. """
        raise NotImplementedError()

    def get_file_path_from_model(self, model, iter):
        """ This function should retrieve a file path from C{model},
        the current row being specified by C{iter}. """
        raise NotImplementedError()

    def stop_update(self):
        """ Stops generation of pixbufs. """
        self._stop = True

        for thread in self._threads:
            thread.join()

        self._stop = False

    def get_status_column(self):
        """ Returns the status column in the model. """
        return self._status_column

    def set_status_column(self, column):
        """ Sets the field in the model that should be used for thumbnail
        status. Must be of type L{gobject.BOOLEAN}. """
        self._status_column = column

    def draw_thumbnails_on_screen(self, *args):
        """ Prepares valid thumbnails for currently displayed icons. """

        visible = self.get_visible_range()
        if not visible:
            # No valid paths available
            return

        pixbufs_needed = False
        start = visible[0][0]
        end = visible[1][0]
        # Read ahead and start caching a few more icons
        additional = (end - start) // 2
        model = self.get_model()
        for path in range(start, end + additional + 1):
            try:
                iter = model.get_iter(path)
            except ValueError:
                iter = None

            # Do not queue again if cover was already created
            if (iter is not None and
                not model.get_value(iter, self._status_column)):
                # Mark book cover as generated
                model.set_value(iter, self._status_column, True)

                file_path = self.get_file_path_from_model(model, iter)
                ref = gtk.TreeRowReference(model, (path, ))
                thumbnail_request = (ref, file_path)
                self._queue.put(thumbnail_request)
                pixbufs_needed = True

        if pixbufs_needed:
            self._start_worker_threads()

    def _start_worker_threads(self):
        """ Creates/runs the worker threads for creating pixbufs. """
        running_threads = [thread for thread in self._threads
            if thread.isAlive()]
        new_threads = [threading.Thread(target=self._pixbuf_worker)
            for _ in range(self._max_threads - len(running_threads))]

        self._threads = running_threads + new_threads
        for thread in new_threads:
            thread.setDaemon(True)
            thread.start()

    def _pixbuf_worker(self):
        """ Run by a worker thread to generate the thumbnail for a list
        of paths. """
        while not self._stop and not self._queue.empty():
            try:
                ref, path = self._queue.get_nowait()
            except Queue.Empty:
                break

            self._queue.task_done()
            pixbuf = self.generate_thumbnail(path)
            gobject.idle_add(self._pixbuf_finished, (ref, pixbuf))

    def _pixbuf_finished(self, pixbuf_info):
        """ Executed when a pixbuf was created, to actually insert the pixbuf
        into the view store. C{pixbuf_info} is a tuple containing
        (index, pixbuf). """

        ref, pixbuf = pixbuf_info
        path = ref.get_path()

        if path:
            iter = ref.get_model().get_iter(path)
            ref.get_model().set(iter, self.get_pixbuf_column(), pixbuf)

        # Remove this idle handler.
        del ref
        return 0

# vim: expandtab:sw=4:ts=4

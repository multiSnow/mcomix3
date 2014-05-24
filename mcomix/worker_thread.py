""" Worker thread class. """
from __future__ import with_statement

import threading

class WorkerThread:

    def __init__(self, process_order, name=None, max_threads=1,
                 sort_orders=False, unique_orders=False):
        """Create a new pool of worker threads.

        Optional <name> will be added to spawned thread names.
        <process_order> will be called to process each work order.
        At most <max_threads> will be started for processing.
        If <sort_orders> is True, the orders queue will be sorted
        after each addition. If <unique_orders> is True, duplicate
        orders will not be added to the queue. """
        self._name = name
        self._process_order = process_order
        self._max_threads = max_threads
        self._sort_orders = sort_orders
        self._unique_orders = unique_orders
        self._stop = False
        self._threads = []
        # List of orders waiting for processing.
        self._waiting_orders = []
        # List of orders currently being processed.
        self._processing_orders = []
        self._condition = threading.Condition()

    def __enter__(self):
        return self._condition.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self._condition.__exit__(exc_type, exc_value, traceback)

    def _start(self, nb_threads=1):
        for n in range(nb_threads):
            if len(self._threads) == self._max_threads:
                break
            thread = threading.Thread(target=self._run)
            if self._name is not None:
                thread.name += '-' + self._name
            thread.setDaemon(False)
            thread.start()
            self._threads.append(thread)

    def _run(self):
        order = None
        while True:
            with self._condition:
                if order is not None:
                    self._processing_orders.remove(order)
                while not self._stop and 0 == len(self._waiting_orders):
                    self._condition.wait()
                if self._stop:
                    return
                order = self._waiting_orders.pop(0)
                self._processing_orders.append(order)
            self._process_order(order)

    def clear_orders(self):
        """Clear the current orders queue."""
        with self._condition:
            self._waiting_orders = []

    def append_order(self, order, sort=False):
        """Append work order to the thread orders queue."""
        with self._condition:
            if self._unique_orders:
                if order in self._waiting_orders or \
                   order in self._processing_orders:
                    return
            self._waiting_orders.append(order)
            if self._sort_orders:
                self._waiting_orders.sort()
            self._condition.notifyAll()
            self._start()

    def extend_orders(self, orders):
        """Append work orders to the thread orders queue."""
        with self._condition:
            if self._unique_orders:
                nb_added = 0
                for o in orders:
                    if o in self._waiting_orders or \
                       o in self._processing_orders:
                        continue
                    self._waiting_orders.append(o)
                    nb_added += 1
            else:
                self._waiting_orders.extend(orders)
                nb_added = len(orders)
            if self._sort_orders:
                self._waiting_orders.sort()
            self._condition.notifyAll()
            self._start(nb_threads=nb_added)

    def stop(self):
        """Stop the worker threads and flush the orders queue."""
        self._stop = True
        with self._condition:
            self._condition.notifyAll()
        for thread in self._threads:
            thread.join()
        self._threads = []
        self._stop = False
        self._waiting_orders = []
        self._processing_orders = []

# vim: expandtab:sw=4:ts=4

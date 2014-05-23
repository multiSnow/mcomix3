""" Worker thread class. """
from __future__ import with_statement

import threading

class WorkerThread:

    def __init__(self, process_order, sort_orders=False, unique_orders=False):
        """Create a new worker thread.

        <process_order> will be called to process each work order.
        If <sort_orders> is True, the orders queue will be sorted
        after each addition. If <unique_orders> is True, duplicate
        orders will not be added to the queue. """
        self._process_order = process_order
        self._sort_orders = sort_orders
        self._unique_orders = unique_orders
        self._stop = False
        self._thread = None
        self._orders = []
        self._current_order = None
        self._condition = threading.Condition()

    def __enter__(self):
        return self._condition.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self._condition.__exit__(exc_type, exc_value, traceback)

    def _start(self):
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run)
        self._thread.setDaemon(False)
        self._thread.start()

    def _run(self):
        while True:
            with self._condition:
                self._current_order = None
                while not self._stop and 0 == len(self._orders):
                    self._condition.wait()
                if self._stop:
                    return
                order = self._orders.pop(0)
                self._current_order = order
            self._process_order(order)

    def clear_orders(self):
        """Clear the current orders queue."""
        with self._condition:
            self._orders = []

    def append_order(self, order, sort=False):
        """Append work order to the thread orders queue."""
        with self._condition:
            if self._unique_orders:
                if order == self._current_order \
                   or order in self._orders:
                    return
            self._orders.append(order)
            if self._sort_orders:
                self._orders.sort()
            self._condition.notify()
            self._start()

    def extend_orders(self, orders):
        """Append work orders to the thread orders queue."""
        with self._condition:
            if self._unique_orders:
                for o in orders:
                    if o == self._current_order or \
                       o in self._orders:
                        continue
                    self._orders.append(o)
            else:
                self._orders.extend(orders)
            if self._sort_orders:
                self._orders.sort()
            self._condition.notify()
            self._start()

    def stop(self):
        """Stop the worker thread and flush the orders queue."""
        if self._thread is not None:
            self._stop = True
            with self._condition:
                self._condition.notify()
            self._thread.join()
            self._thread = None
            self._stop = False
        self._orders = []
        self._current_order = None

# vim: expandtab:sw=4:ts=4

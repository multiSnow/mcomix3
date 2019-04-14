# keep this file only for reference
''' Worker thread class. '''

import threading
import traceback

from mcomix import log

class WorkerThread(object):

    def __init__(self, process_order, name=None, max_threads=1,
                 sort_orders=False, unique_orders=False):
        '''Create a new pool of worker threads.

        Optional <name> will be added to spawned thread names.
        <process_order> will be called to process each work order.
        At most <max_threads> will be started for processing.
        If <sort_orders> is True, the orders queue will be sorted
        after each addition. If <unique_orders> is True, duplicate
        orders will not be added to the queue. '''
        self._name = name
        self._process_order = process_order
        self._max_threads = max_threads
        self._sort_orders = sort_orders
        self._unique_orders = unique_orders
        self._stop = False
        self._threads = []
        # Queue of orders waiting for processing.
        self._orders_queue = []
        if self._unique_orders:
            # Track orders.
            self._orders_set = set()
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
            thread.daemon=False
            thread.start()
            self._threads.append(thread)

    def _order_uid(self, order):
        if isinstance(order, tuple) or isinstance(order, list):
            return order[0]
        return order

    def _run(self):
        order_uid = None
        while True:
            with self._condition:
                if order_uid is not None:
                    self._orders_set.remove(order_uid)
                while not self._stop and 0 == len(self._orders_queue):
                    self._condition.wait()
                if self._stop:
                    return
                order = self._orders_queue.pop(0)
                if self._unique_orders:
                    order_uid = self._order_uid(order)
            try:
                self._process_order(order)
            except Exception as e:
                log.error(_('! Worker thread processing %(function)r failed: %(error)s'),
                          { 'function' : self._process_order, 'error' : e })
                log.debug('Traceback:\n%s', traceback.format_exc())

    def must_stop(self):
        '''Return true if we've been asked to stop processing.

        Can be used by the processing function to check if it must abort early.
        '''
        return self._stop

    def clear_orders(self):
        '''Clear the current orders queue.'''
        with self._condition:
            if self._unique_orders:
                # We can't just clear the set, as some orders
                # can be in the process of being processed.
                for order in self._orders_queue:
                    order_uid = self._order_uid(order)
                    self._orders_set.remove(order_uid)
            self._orders_queue = []

    def append_order(self, order):
        '''Append work order to the thread orders queue.'''
        with self._condition:
            if self._unique_orders:
                order_uid = self._order_uid(order)
                if order_uid in self._orders_set:
                    # Duplicate order.
                    return
                self._orders_set.add(order_uid)
            self._orders_queue.append(order)
            if self._sort_orders:
                self._orders_queue.sort()
            self._condition.notifyAll()
            self._start()

    def extend_orders(self, orders_list):
        '''Append work orders to the thread orders queue.'''
        with self._condition:
            if self._unique_orders:
                nb_added = 0
                for order in orders_list:
                    order_uid = self._order_uid(order)
                    if order_uid in self._orders_set:
                        # Duplicate order.
                        continue
                    self._orders_set.add(order_uid)
                    self._orders_queue.append(order)
                    nb_added += 1
            else:
                self._orders_queue.extend(orders_list)
                nb_added = len(orders_list)
            if 0 == nb_added:
                return
            if self._sort_orders:
                self._orders_queue.sort()
            self._condition.notifyAll()
            self._start(nb_threads=nb_added)

    def stop(self):
        '''Stop the worker threads and flush the orders queue.'''
        self._stop = True
        with self._condition:
            self._condition.notifyAll()
        for thread in self._threads:
            thread.join()
        self._threads = []
        self._stop = False
        self._orders_queue = []
        if self._unique_orders:
            self._orders_set.clear()

# vim: expandtab:sw=4:ts=4

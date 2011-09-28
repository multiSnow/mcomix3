""" pixbuf_cache.py - Caches book covers for the library display."""
# -*- coding: utf-8 -*-

from __future__ import with_statement
import threading

__all__ = ["get_pixbuf_cache"]

class _PixbufCache(object):

    """ Pixbuf cache for the library window. Instead of loading book covers
    from disk again after switching collection or using filtering, this class
    stores a pre-defined amount of pixbufs in memory, evicting older pixbufs
    as necessary.
    """

    def __init__(self, size):
        #: Cache size, in images
        assert size > 0
        self.cachesize = size
        #: Store book id => pixbuf
        self._cache = {}
        #: Ensure thread safety
        self._lock = threading.RLock()

    def add(self, id, pixbuf):
        """ Adds a cache object with <id> and associates it with the
        passed pixbuf. """
        
        with self._lock:
            if len(self._cache) > self.cachesize:
                first = self._cache.items()[0]
                self.invalidate(first[0])

            self._cache[id] = pixbuf

    def exists(self, id):
        """ Checks if there is an entry for the given id in the cache. """
        return id in self._cache

    def get(self, id):
        """ Returns the pixbuf for the given cache id, or None, if such
        an entry does not exist. """
        if id in self._cache:
            return self._cache[id]
        else:
            return None

    def invalidate(self, id):
        """ Invalidates the object with the specified cache ID. """
        with self._lock:
            if id in self._cache:
                del self._cache[id]

    def invalidate_all(self):
        """ Invalidates all cached objects. """
        with self._lock:
            self._cache.clear()


_cache = None

def get_pixbuf_cache():
    global _cache

    if _cache:
        return _cache
    else:
        # 500 items is about 130 MB of RAM with 500px thumbnails,
        # and about 35 MB at 250px.
        _cache = _PixbufCache(500)
        return _cache

# vim: expandtab:sw=4:ts=4

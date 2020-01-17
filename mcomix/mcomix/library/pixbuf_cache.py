# -*- coding: utf-8 -*-
''' pixbuf_cache.py - Caches book covers for the library display.'''

from collections import OrderedDict
from threading import Lock

__all__ = ['get_pixbuf_cache']

class _PixbufCache(object):

    ''' Pixbuf cache for the library window. Instead of loading book covers
    from disk again after switching collection or using filtering, this class
    stores a pre-defined amount of pixbufs in memory, evicting older pixbufs
    as necessary.
    '''

    def __init__(self, size):
        #: Cache size, in images
        assert size > 0
        self.cachesize = size
        #: Store book id => pixbuf
        self._cache = OrderedDict()
        #: Ensure thread safety
        self._lock = Lock()

    def add(self, path, pixbuf):
        ''' Add a pixbuf to cache with path as key. '''
        with self._lock:
            if path in self._cache:
                return
            while len(self._cache) > self.cachesize:
                self._cache.popitem(last=False)
            self._cache[path] = pixbuf

    def get(self, path):
        ''' Return the pixbuf for the given cache path, or None if not exists. '''
        with self._lock:
            return self._cache.get(path, None)

    def pop(self, path):
        ''' Remove the object with the given cache path. '''
        with self._lock:
            self._cache.pop(path, None)

    def clear(self):
        ''' Clear all cached objects. '''
        with self._lock:
            self._cache.clear()


_cache = None

def get_pixbuf_cache():
    global _cache

    if _cache is None:
        # 500 items is about 130 MB of RAM with 500px thumbnails,
        # and about 35 MB at 250px.
        _cache = _PixbufCache(500)
    return _cache

# vim: expandtab:sw=4:ts=4

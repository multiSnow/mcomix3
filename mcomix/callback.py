# -*- coding: utf-8 -*-

import traceback
import weakref
import threading
from gi.repository import GObject

from mcomix import log

class CallbackList(object):
    """ Helper class for implementing callbacks within the main thread.
    Add listeners to method calls with method += callback_function. """

    def __init__(self, obj, function):
        self.__callbacks = []
        self.__object = obj
        self.__function = function

    def __call__(self, *args, **kwargs):
        """ Runs the wrapped function. After the funtion has finished,
        callbacks are run. Code within the function and the callback is
        always executed in the main thread. """

        if threading.currentThread().name == 'MainThread':
            if self.__object:
                # Assume that the Callback object is bound to a class method.
                result = self.__function(self.__object, *args, **kwargs)
            else:
                # Otherwise, the callback should be bound to a normal function.
                result = self.__function(*args, **kwargs)

            self.__run_callbacks(*args, **kwargs)
            return result
        else:
            # Call this method again in the main thread.
            GObject.idle_add(self.__mainthread_call, (args, kwargs))

    def __iadd__(self, function):
        """ Support for 'method += callback_function' syntax. """
        obj, func = self.__get_function(function)

        if (obj, func) not in self.__callbacks:
            self.__callbacks.append((obj, func))

        return self

    def __isub__(self, function):
        """ Support for 'method -= callback_function' syntax. """
        obj, func = self.__get_function(function)

        if (obj, func) in self.__callbacks:
            self.__callbacks.remove((obj, func))

        return self

    def __mainthread_call(self, params):
        """ Helper function to execute code in the main thread.
        This will be called by GObject.idle_add, with <params> being a tuple
        of (args, kwargs). """

        result = self(*params[0], **params[1])

        # Remove this function from the idle queue
        return 0

    def __run_callbacks(self, *args, **kwargs):
        """ Executes callback functions. """
        for obj_ref, func in self.__callbacks:

            if obj_ref is None:
                # Callback is a normal function
                callback = func
            elif obj_ref() is not None:
                # Callback is a bound method.
                # Recreate it by binding the function to the object.
                callback = func.__get__(obj_ref())
            else:
                # Callback is a bound method, object
                # no longer exists.
                callback = None

            if callback:
                try:
                    callback(*args, **kwargs)
                except Exception, e:
                    log.error(_('! Callback %(function)r failed: %(error)s'),
                              { 'function' : callback, 'error' : e })
                    log.debug('Traceback:\n%s', traceback.format_exc())

    def __callback_deleted(self, obj_ref):
        """ Called whenever one of the callback objects is collected by gc.
        This removes all callback functions registered by the object. """
        self.__callbacks = filter(lambda callback: callback[0] != obj_ref,
            self.__callbacks)

    def __get_function(self, func):
        """ If <func> is a normal function, return (None, func).
        If <func> is a bound method, return (weakref(obj), func), with <obj>
        being the object <func> is bound to. This is required since
        weak references do not work on bound methods. """

        if hasattr(func, "im_self") and getattr(func, "im_self") is not None:
            return (weakref.ref(func.im_self, self.__callback_deleted), func.im_func)
        else:
            return (None, func)

class Callback(object):
    """ Decorator class for using the CallbackList helper. """

    def __init__(self, function):
        # This is the function the Callback is decorating.
        self.__function = function

    def __get__(self, obj, cls):
        """ This method makes Callback implement the descriptor interface.
        Enables calling bound methods with the correct <self> reference.
        Do not ask me why or how this actually works, I simply do not know. """

        return CallbackList(obj, self.__function)

# vim: expandtab:sw=4:ts=4

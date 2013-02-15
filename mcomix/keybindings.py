# -*- coding: utf-8 -*-

""" Dynamic hotkey management

This module handles global hotkeys that were previously hardcoded in events.py.
All menu accelerators are handled using GTK's built-in accelerator map. The map
doesn't seem to support multiple keybindings for one action, though, so this
module takes care of the problem.

At runtime, other modules can register a callback for a specific action name.
This action name has to be registered in BINDING_INFO, or an Exception will be
thrown. The module can pass a list of default keybindings. If the user hasn't
configured different bindings, the default ones will be used.

Afterwards, the action will be stored together with its keycode/modifier in a
dictionary:
(keycode: int, modifier: GdkModifierType) =>
    (action: string, callback: func, args: list, kwargs: dict)

Default keybindings will be stored here at initialization:
action-name: string => [keycodes: list]


Each action_name can have multiple keybindings.
"""

import gtk
import json

from mcomix import constants
from mcomix import log

#: Bindings defined in this dictionary will appear in the configuration dialog.
#: If 'group' is None, the binding cannot be modified from the preferences dialog.
BINDING_INFO = {
    'previous page' : { 'title' : _('Previous page'), 'group' : _('Reading') },
    'next page' : { 'title' : _('Next page'), 'group' : _('Reading') },

    'scroll left bottom' : { 'title' : _('Scroll to bottom left'), 'group' : _('Page orientation and zoom')},
    'scroll middle bottom' : { 'title' : _('Scroll to bottom center'), 'group' : _('Page orientation and zoom')},
    'scroll right bottom' : { 'title' : _('Scroll to bottom right'), 'group' : _('Page orientation and zoom')},

    'scroll left middle' : { 'title' : _('Scroll to middle left'), 'group' : _('Page orientation and zoom')},
    'scroll middle' : { 'title' : _('Scroll to center'), 'group' : _('Page orientation and zoom')},
    'scroll right middle' : { 'title' : _('Scroll to middle right'), 'group' : _('Page orientation and zoom')},

    'scroll left top' : { 'title' : _('Scroll to top left'), 'group' : _('Page orientation and zoom')},
    'scroll middle top' : { 'title' : _('Scroll to top center'), 'group' : _('Page orientation and zoom')},
    'scroll right top' : { 'title' : _('Scroll to top right'), 'group' : _('Page orientation and zoom')},

    'exit fullscreen' : { 'title' : _('Exit from fullscreen'), 'group' : None},
    'toggle fullscreen' : { 'title' : _('Toggle fullscreen'), 'group' : _('User interface')},

    'zoom in' : { 'title' : _('Zoom in'), 'group' : _('Page orientation and zoom')},
    'zoom out' : { 'title' : _('Zoom out'), 'group' : _('Page orientation and zoom')},
    'zoom original' : { 'title' : _('Normal size'), 'group' : _('Page orientation and zoom')},

    'scroll down' : { 'title' : _('Scroll down'), 'group' : _('Reading') },
    'scroll up' : { 'title' : _('Scroll up'), 'group' : _('Reading') },
    'scroll right' : { 'title' : _('Scroll right'), 'group' : _('Reading') },
    'scroll left' : { 'title' : _('Scroll left'), 'group' : _('Reading') },

    'smart scroll up' : { 'title' : _('Smart scroll up'), 'group' : _('Reading') },
    'smart scroll down' : { 'title' : _('Smart scroll down'), 'group' : _('Reading') },

    'osd panel' : { 'title' : _('Show OSD panel'), 'group' : _('User Interface') },
}

# Generate 9 entries for executing command 1 to 9
for i in range(1, 10):
    BINDING_INFO['execute command %d' %i] = { 'title' : _('Execute external command') + u' (%d)' % i , 'group' : _('User Interface') }


class _KeybindingManager(object):
    def __init__(self, window):
        #: Main window instance
        self._window = window
        #: Stores the current callbacks associated with each key.
        self._callbacks = {}
        #: Mapping from action names to list of keybindings. Loaded from configuration at startup.
        self._action_bindings = {}

        self._initialize()

    def register(self, name, bindings, callback, args=[], kwargs={}):
        """ Registers an action for a predefined keybinding name.
        @param name: Action name, defined in L{BINDING_INFO}.
        @param bindings: List of keybinding strings, as understood
                         by L{gtk.accelerator_parse}. Only used if no
                         bindings were loaded for this action.
        @param callback: Function callback
        @param args: List of arguments to pass to the callback
        @param kwargs: List of keyword arguments to pass to the callback.
        """
        global BINDING_INFO
        assert name in BINDING_INFO, "'%s' isn't a valid keyboard action." % name

        # Load stored keybindings, or fall back to passed arguments
        if self._get_bindings_for_action(name) is not None:
            keycodes = self._get_bindings_for_action(name)
        else:
            keycodes = [ gtk.accelerator_parse(binding) for binding in bindings ]

        for keycode in keycodes:
            if keycode in self._callbacks:
                log.warning(_('Keybinding for "%(action)s" overrides hotkey for another action.'),
                        {"action": name})

            self._callbacks[keycode] = (name, callback, args, kwargs)

    def execute(self, keybinding):
        """ Executes an action that has been registered for the
        passed keyboard event. If no action is bound to the passed key, this
        method is a no-op. """
        if keybinding in self._callbacks:
            action, func, args, kwargs = self._callbacks[keybinding]
            self._window.emit_stop_by_name('key_press_event')
            return func(*args, **kwargs)

        # Some keys enable additional modifiers (NumLock enables GDK_MOD2_MASK),
        # which prevent direct lookup simply by being pressed.
        # XXX: Looking up by key/modifier probably isn't the best implementation
        for binding, value in self._callbacks.iteritems():
            keycode, flags = binding
            if keycode == keybinding[0] and flags & keybinding[1]:
                action, func, args, kwargs = value
                self._window.emit_stop_by_name('key_press_event')
                return func(*args, **kwargs)

        # Some keys may need modifiers to be typeable, but may be registered without.
        if (keybinding[0], 0) in self._callbacks:
            action, func, args, kwargs = self._callbacks[(keybinding[0], 0)]
            self._window.emit_stop_by_name('key_press_event')
            return func(*args, **kwargs)

    def save(self):
        """ Stores the keybindings that have been set to disk. """

        # Collect keybindings for all registered actions
        action_to_keys = {}
        for binding, callback in self._callbacks.iteritems():
            keyval, modifiers = binding
            action, func, args, kwargs = callback

            keyname = gtk.accelerator_name(keyval, modifiers)
            if action in action_to_keys:
                action_to_keys[action].append(keyname)
            else:
                action_to_keys[action] = [keyname]

        fp = file(constants.KEYBINDINGS_CONF_PATH, "w")
        json.dump(action_to_keys, fp, indent=2)
        fp.close()

    def _initialize(self):
        """ Restore keybindings from disk. """
        try:
            fp = file(constants.KEYBINDINGS_CONF_PATH, "r")
            stored_action_bindings = json.load(fp)
            fp.close()
        except Exception, e:
            log.error(_("Couldn't load keybindings: %s"), e)
            stored_action_bindings = {}

        for action in BINDING_INFO.iterkeys():
            if action in stored_action_bindings:
                self._action_bindings[action] = [
                    gtk.accelerator_parse(keyname)
                    for keyname in stored_action_bindings[action] ]
            else:
                self._action_bindings[action] = None

    def _get_bindings_for_action(self, name):
        """ Returns a list of (keycode, modifier) for the action C{name}. """
        if name in self._action_bindings:
            return self._action_bindings[name]
        else:
            return []

_manager = None


def keybinding_manager(window):
    """ Returns a singleton instance of the keybinding manager. """
    global _manager
    if _manager:
        return _manager
    else:
        _manager = _KeybindingManager(window)
        return _manager

# vim: expandtab:sw=4:ts=4

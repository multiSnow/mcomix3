# -*- coding: utf-8 -*-

''' Dynamic hotkey management

This module handles global hotkeys that were previously hardcoded in events.py.
All menu accelerators are handled using GTK's built-in accelerator map. The map
doesn't seem to support multiple keybindings for one action, though, so this
module takes care of the problem.

At runtime, other modules can register a callback for a specific action name.
This action name has to be registered in keybindings_map.BINDING_INFO, or an Exception will be
thrown. The module can pass a list of default keybindings. If the user hasn't
configured different bindings, the default ones will be used.

Afterwards, the action will be stored together with its keycode/modifier in a
dictionary:
(keycode: int, modifier: GdkModifierType) =>
    (action: string, callback: func, args: list, kwargs: dict)

Default keybindings will be stored here at initialization:
action-name: string => [keycodes: list]


Each action_name can have multiple keybindings.
'''

import os
import shutil
import json
from collections import defaultdict

from gi.repository import Gtk

from mcomix import constants
from mcomix import log
from mcomix import keybindings_map

class _KeybindingManager(object):
    def __init__(self, window):
        #: Main window instance
        self._window = window

        self._action_to_callback = {} # action name => (func, args, kwargs)
        self._action_to_bindings = defaultdict(list) # action name => [ (key code, key modifier), ]
        self._binding_to_action = {} # (key code, key modifier) => action name

        self._initialize()

    def register(self, name, callback, args=[], kwargs={}, bindings=[]):
        ''' Registers an action for a predefined keybinding name.
        @param name: Action name, defined in L{keybindings_map.BINDING_INFO}.
        @param bindings: List of keybinding strings, as understood
                         by L{Gtk.accelerator_parse}. Only used if no
                         bindings were loaded for this action.
        @param callback: Function callback
        @param args: List of arguments to pass to the callback
        @param kwargs: List of keyword arguments to pass to the callback.
        '''
        assert name in keybindings_map.BINDING_INFO, '"%s" isn\'t a valid keyboard action.' % name

        # use default bindings if not provided
        if not bindings:
            bindings=keybindings_map.DEFAULT_BINDINGS.get(name,[])

        # Load stored keybindings, or fall back to passed arguments
        keycodes = self._action_to_bindings[name]
        if keycodes == []:
            keycodes = [Gtk.accelerator_parse(binding) for binding in bindings]

        for keycode in keycodes:
            if keycode in self._binding_to_action.keys():
                if self._binding_to_action[keycode] != name:
                    log.warning(_('Keybinding for "%(action)s" overrides hotkey for another action.'),
                                {'action': name})
                    log.warning('Binding %s overrides %r', keycode, self._binding_to_action[keycode])
            else:
                self._binding_to_action[keycode] = name
                self._action_to_bindings[name].append(keycode)

        # Add gtk accelerator for labels in menu
        if len(self._action_to_bindings[name]) > 0:
            key, mod = self._action_to_bindings[name][0]
            Gtk.AccelMap.change_entry('<Actions>/mcomix-main/%s' % name, key, mod, True)

        self._action_to_callback[name] = (callback, args, kwargs)


    def edit_accel(self, name, new_binding, old_binding):
        ''' Changes binding for an action
        @param name: Action name
        @param new_binding: Binding to be assigned to action
        @param old_binding: Binding to be removed from action [ can be empty: "" ]

        @return None: new_binding wasn't in any action
                action name: where new_binding was before
        '''
        assert name in keybindings_map.BINDING_INFO, '"%s" isn\'t a valid keyboard action.' % name

        nb = Gtk.accelerator_parse(new_binding)
        old_action_with_nb = self._binding_to_action.get(nb)
        if old_action_with_nb is not None:
            # The new key is already bound to an action, erase the action
            self._binding_to_action.pop(nb)
            self._action_to_bindings[old_action_with_nb].remove(nb)

        if old_binding and name != old_action_with_nb:
            # The action already had a key that is now being replaced
            ob = Gtk.accelerator_parse(old_binding)
            self._binding_to_action[nb] = name

            # Remove action bound to the key.
            if ob in self._binding_to_action:
                self._binding_to_action.pop(ob)

            if ob in self._action_to_bindings[name]:
                idx = self._action_to_bindings[name].index(ob)
                self._action_to_bindings[name].pop(idx)
                self._action_to_bindings[name].insert(idx, nb)
        else:
            self._binding_to_action[nb] = name
            self._action_to_bindings[name].append(nb)

        self.save()
        return old_action_with_nb

    def clear_accel(self, name, binding):
        ''' Remove binding for an action '''
        assert name in keybindings_map.BINDING_INFO, '"%s" isn\'t a valid keyboard action.' % name

        ob = Gtk.accelerator_parse(binding)
        self._action_to_bindings[name].remove(ob)
        self._binding_to_action.pop(ob)

        self.save()

    def clear_all(self):
        ''' Removes all keybindings. The changes are only persisted if
        save() is called afterwards. '''
        self._action_to_callback = {}
        self._action_to_bindings = defaultdict(list)
        self._binding_to_action = {}

    def execute(self, keybinding):
        ''' Executes an action that has been registered for the
        passed keyboard event. If no action is bound to the passed key, this
        method is a no-op. '''
        if keybinding in self._binding_to_action:
            action = self._binding_to_action[keybinding]
            func, args, kwargs = self._action_to_callback[action]
            self._window.stop_emission_by_name('key_press_event')
            return func(*args, **kwargs)

        # Some keys enable additional modifiers (NumLock enables GDK_MOD2_MASK),
        # which prevent direct lookup simply by being pressed.
        # XXX: Looking up by key/modifier probably isn't the best implementation,
        # so limit possible states to begin with?
        for stored_binding, action in self._binding_to_action.items():
            stored_keycode, stored_flags = stored_binding
            if stored_keycode == keybinding[0] and stored_flags & keybinding[1]:
                func, args, kwargs = self._action_to_callback[action]
                self._window.stop_emission_by_name('key_press_event')
                return func(*args, **kwargs)

    def save(self):
        ''' Stores the keybindings that have been set to disk. '''
        # Collect keybindings for all registered actions
        action_to_keys = {}
        for action, bindings in self._action_to_bindings.items():
            if bindings is not None:
                action_to_keys[action] = [
                    Gtk.accelerator_name(keyval, modifiers) for
                    (keyval, modifiers) in bindings
                ]
        with open(constants.KEYBINDINGS_CONF_PATH, 'w') as fp:
            json.dump(action_to_keys, fp, indent=2)

    def _initialize(self):
        ''' Restore keybindings from disk. '''
        try:
            with open(constants.KEYBINDINGS_CONF_PATH, 'r') as fp:
                stored_action_bindings = json.load(fp)
        except:
            stored_action_bindings = {}

        for action in keybindings_map.BINDING_INFO.keys():
            if action in stored_action_bindings:
                bindings = [
                    Gtk.accelerator_parse(keyname)
                    for keyname in stored_action_bindings[action] ]
                self._action_to_bindings[action] = bindings
                for binding in bindings:
                    self._binding_to_action[binding] = action
            else:
                self._action_to_bindings[action] = []

    def get_bindings_for_action(self, name):
        ''' Returns a list of (keycode, modifier) for the action C{name}. '''
        return self._action_to_bindings[name]

_manager = None


def keybinding_manager(window):
    ''' Returns a singleton instance of the keybinding manager. '''
    global _manager
    if _manager:
        return _manager
    else:
        _manager = _KeybindingManager(window)
        return _manager

# vim: expandtab:sw=4:ts=4

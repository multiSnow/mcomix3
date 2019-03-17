# -*- coding: utf-8 -*-

''' Dynamic hotkey management

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
'''

import os
import shutil
from gi.repository import Gtk
import json
from collections import defaultdict

from mcomix import constants
from mcomix import log

#: Bindings defined in this dictionary will appear in the configuration dialog.
#: If 'group' is None, the binding cannot be modified from the preferences dialog.
BINDING_INFO = {
    # Navigation between pages, archives, directories
    'previous_page' : { 'title' : _('Previous page'), 'group' : _('Navigation') },
    'next_page' : { 'title' : _('Next page'), 'group' : _('Navigation') },
    'previous_page_ff' : { 'title': _('Back ten pages'), 'group': _('Navigation') },
    'next_page_ff' : { 'title': _('Forward ten pages'), 'group': _('Navigation') },
    'previous_page_dynamic' : { 'title': _('Previous page (dynamic)'), 'group': _('Navigation') },
    'next_page_dynamic' : { 'title': _('Next page (dynamic)'), 'group': _('Navigation') },
    'previous_page_singlestep': { 'title': _('Previous page (always one page)'), 'group': _('Navigation') },
    'next_page_singlestep': { 'title': _('Next page (always one page)'), 'group': _('Navigation') },

    'first_page' : { 'title': _('First page'), 'group': _('Navigation') },
    'last_page' : { 'title': _('Last page'), 'group': _('Navigation') },
    'go_to' : { 'title': _('Go to page'), 'group': _('Navigation') },

    'next_archive' : { 'title': _('Next archive'), 'group': _('Navigation') },
    'previous_archive' : { 'title': _('Previous archive'), 'group': _('Navigation') },
    'next_directory' : { 'title': _('Next directory'), 'group': _('Navigation') },
    'previous_directory' : { 'title': _('Previous directory'), 'group': _('Navigation') },

    # Scrolling
    'scroll_left_bottom' : { 'title' : _('Scroll to bottom left'), 'group' : _('Scroll')},
    'scroll_middle_bottom' : { 'title' : _('Scroll to bottom center'), 'group' : _('Scroll')},
    'scroll_right_bottom' : { 'title' : _('Scroll to bottom right'), 'group' : _('Scroll')},

    'scroll_left_middle' : { 'title' : _('Scroll to middle left'), 'group' : _('Scroll')},
    'scroll_middle' : { 'title' : _('Scroll to center'), 'group' : _('Scroll')},
    'scroll_right_middle' : { 'title' : _('Scroll to middle right'), 'group' : _('Scroll')},

    'scroll_left_top' : { 'title' : _('Scroll to top left'), 'group' : _('Scroll')},
    'scroll_middle_top' : { 'title' : _('Scroll to top center'), 'group' : _('Scroll')},
    'scroll_right_top' : { 'title' : _('Scroll to top right'), 'group' : _('Scroll')},

    'scroll_down' : { 'title' : _('Scroll down'), 'group' : _('Scroll') },
    'scroll_up' : { 'title' : _('Scroll up'), 'group' : _('Scroll') },
    'scroll_right' : { 'title' : _('Scroll right'), 'group' : _('Scroll') },
    'scroll_left' : { 'title' : _('Scroll left'), 'group' : _('Scroll') },

    'smart_scroll_up' : { 'title' : _('Smart scroll up'), 'group' : _('Scroll') },
    'smart_scroll_down' : { 'title' : _('Smart scroll down'), 'group' : _('Scroll') },

    # View
    'zoom_in' : { 'title' : _('Zoom in'), 'group' : _('Zoom')},
    'zoom_out' : { 'title' : _('Zoom out'), 'group' : _('Zoom')},
    'zoom_original' : { 'title' : _('Normal size'), 'group' : _('Zoom')},

    'keep_transformation' : { 'title': _('Keep transformation'), 'group': _('Transformation') },
    'rotate_90' : { 'title': _('Rotate 90 degrees CW'), 'group': _('Transformation') },
    'rotate_180' : { 'title': _('Rotate 180 degrees'), 'group': _('Transformation') },
    'rotate_270' : { 'title': _('Rotate 90 degrees CCW'), 'group': _('Transformation') },
    'flip_horiz' : { 'title': _('Flip horizontally'), 'group': _('Transformation') },
    'flip_vert' : { 'title': _('Flip vertically'), 'group': _('Transformation') },
    'no_autorotation' : { 'title': _('Never autorotate'), 'group': _('Transformation') },

    'rotate_90_width' : { 'title': _('Rotate 90 degrees CW'), 'group': _('Autorotate by width') },
    'rotate_270_width' : { 'title': _('Rotate 90 degrees CCW'), 'group': _('Autorotate by width') },
    'rotate_90_height' : { 'title': _('Rotate 90 degrees CW'), 'group': _('Autorotate by height') },
    'rotate_270_height' : { 'title': _('Rotate 90 degrees CCW'), 'group': _('Autorotate by height') },

    'double_page' : { 'title': _('Double page mode'), 'group': _('View mode') },
    'manga_mode' : { 'title': _('Manga mode'), 'group': _('View mode') },
    'invert_scroll' : { 'title': _('Invert smart scroll'), 'group': _('View mode') },

    'lens' : { 'title': _('Magnifying lens'), 'group': _('View mode') },
    'stretch' : { 'title': _('Stretch small images'), 'group': _('View mode') },

    'best_fit_mode' : { 'title': _('Best fit mode'), 'group': _('View mode') },
    'fit_width_mode' : { 'title': _('Fit width mode'), 'group': _('View mode') },
    'fit_height_mode' : { 'title': _('Fit height mode'), 'group': _('View mode') },
    'fit_size_mode' : { 'title': _('Fit size mode'), 'group': _('View mode') },
    'fit_manual_mode' : { 'title': _('Manual zoom mode'), 'group': _('View mode') },

    # General UI
    'exit_fullscreen' : { 'title' : _('Exit from fullscreen'), 'group' : _('User interface')},

    'osd_panel' : { 'title' : _('Show OSD panel'), 'group' : _('User interface') },
    'minimize' : { 'title' : _('Minimize'), 'group' : _('User interface') },
    'fullscreen' : { 'title': _('Fullscreen'), 'group': _('User interface') },
    'toolbar' : { 'title': _('Show/hide toolbar'), 'group': _('User interface') },
    'menubar' : { 'title': _('Show/hide menubar'), 'group': _('User interface') },
    'statusbar' : { 'title': _('Show/hide statusbar'), 'group': _('User interface') },
    'scrollbar' : { 'title': _('Show/hide scrollbars'), 'group': _('User interface') },
    'thumbnails' : { 'title': _('Thumbnails'), 'group': _('User interface') },
    'hide_all' : { 'title': _('Show/hide all'), 'group': _('User interface') },
    'slideshow' : { 'title': _('Start slideshow'), 'group': _('User interface') },

    # File operations
    'delete' : { 'title' : _('Delete'), 'group' : _('File') },
    'refresh_archive' : { 'title': _('Refresh'), 'group': _('File') },
    'close' : { 'title': _('Close'), 'group': _('File') },
    'quit' : { 'title': _('Quit'), 'group': _('File') },
    'save_and_quit' : { 'title': _('Save and quit'), 'group': _('File') },
    'extract_page' : { 'title': _('Save As'), 'group': _('File') },

    'comments' : { 'title': _('Archive comments'), 'group': _('File') },
    'properties' : { 'title': _('Properties'), 'group': _('File') },
    'preferences' : { 'title': _('Preferences'), 'group': _('File') },

    'edit_archive' : { 'title': _('Edit archive'), 'group': _('File') },
    'open' : { 'title': _('Open'), 'group': _('File') },
    'enhance_image' : { 'title': _('Enhance image'), 'group': _('File') },
    'library' : { 'title': _('Library'), 'group': _('File') },
}

# Generate 9 entries for executing command 1 to 9
for i in range(1, 10):
    BINDING_INFO['execute_command_%d' %i] = { 
            'title' : _('Execute external command') + ' (%d)' % i,
            'group' : _('External commands')
    }

DEFAULT_BINDINGS = {
    # Navigation between pages, archives, directories
    'previous_page':['Page_Up','KP_Page_Up','BackSpace'],
    'next_page':['Page_Down','KP_Page_Down'],
    'previous_page_singlestep':['<Ctrl>Page_Up','<Ctrl>KP_Page_Up','<Ctrl>BackSpace'],
    'next_page_singlestep':['<Ctrl>Page_Down','<Ctrl>KP_Page_Down'],
    'previous_page_dynamic':['<Mod1>Left'],
    'next_page_dynamic':['<Mod1>Right'],
    'previous_page_ff':['<Shift>Page_Up','<Shift>KP_Page_Up','<Shift>BackSpace','<Shift><Mod1>Left'],
    'next_page_ff':['<Shift>Page_Down','<Shift>KP_Page_Down','<Shift><Mod1>Right'],

    'first_page':['Home','KP_Home'],
    'last_page':['End','KP_End'],
    'go_to':['G'],

    'next_archive':['<control><shift>N'],
    'previous_archive':['<control><shift>P'],
    'next_directory':['<control>N'],
    'previous_directory':['<control>P'],

    # Scrolling
    'scroll_left_bottom':['KP_1'],
    'scroll_middle_bottom':['KP_2'],
    'scroll_right_bottom':['KP_3'],

    'scroll_left_middle':['KP_4'],
    'scroll_middle':['KP_5'],
    'scroll_right_middle':['KP_6'],

    'scroll_left_top':['KP_7'],
    'scroll_middle_top':['KP_8'],
    'scroll_right_top':['KP_9'],

    'scroll_down':['Down','KP_Down'],
    'scroll_up':['Up','KP_Up'],
    'scroll_right':['Right','KP_Right'],
    'scroll_left':['Left','KP_Left'],

    'smart_scroll_up':['<Shift>space'],
    'smart_scroll_down':['space'],

    # View
    'zoom_in':['plus','KP_Add','equal'],
    'zoom_out':['minus','KP_Subtract'],
    'zoom_original':['<Control>0','KP_0'],

    'keep_transformation':['k'],
    'rotate_90':['r'],
    'rotate_270':['<Shift>r'],
    'rotate_180':[],
    'flip_horiz':[],
    'flip_vert':[],
    'no_autorotation':[],

    'rotate_90_width':[],
    'rotate_270_width':[],
    'rotate_90_height':[],
    'rotate_270_height':[],

    'double_page':['d'],
    'manga_mode':['m'],
    'invert_scroll':['x'],

    'lens':['l'],
    'stretch':['y'],

    'best_fit_mode':['b'],
    'fit_width_mode':['w'],
    'fit_height_mode':['h'],
    'fit_size_mode':['s'],
    'fit_manual_mode':['a'],

    # General UI
    'exit_fullscreen':['Escape'],

    'osd_panel':['Tab'],
    'minimize':['n'],
    'fullscreen':['f','F11'],
    'toolbar':[],
    'menubar':['<Control>M'],
    'statusbar':[],
    'scrollbar':[],
    'thumbnails':['F9'],
    'hide_all':['i'],
    'slideshow':['<Control>S'],

    # File operations
    'delete':['Delete'],
    'refresh_archive':['<control><shift>R'],
    'close':['<Control>W'],
    'quit':['<Control>Q'],
    'save_and_quit':['<Control><shift>q'],
    'extract_page':['<Control><Shift>s'],

    'comments':['c'],
    'properties':['<Alt>Return'],
    'preferences':['F12'],

    'edit_archive':[],
    'open':['<Control>O'],
    'enhance_image':['e'],
    'library':['<Control>L'],
}

# Generate 9 entries for executing command 1 to 9
for i in range(1, 10):
    DEFAULT_BINDINGS['execute_command_%d' % i] = [str(i)]

class _KeybindingManager(object):
    def __init__(self, window):
        #: Main window instance
        self._window = window

        self._action_to_callback = {} # action name => (func, args, kwargs)
        self._action_to_bindings = defaultdict(list) # action name => [ (key code, key modifier), ]
        self._binding_to_action = {} # (key code, key modifier) => action name

        self._migrate_from_old_bindings()
        self._initialize()

    def register(self, name='', bindings=[], callback=None, args=[], kwargs={}):
        ''' Registers an action for a predefined keybinding name.
        @param name: Action name, defined in L{BINDING_INFO}.
        @param bindings: List of keybinding strings, as understood
                         by L{Gtk.accelerator_parse}. Only used if no
                         bindings were loaded for this action.
        @param callback: Function callback
        @param args: List of arguments to pass to the callback
        @param kwargs: List of keyword arguments to pass to the callback.
        '''
        assert name in BINDING_INFO, '"%s" isn\'t a valid keyboard action.' % name

        # Load stored keybindings, or fall back to passed arguments
        keycodes = self._action_to_bindings[name]
        if keycodes == []:
            keycodes = [Gtk.accelerator_parse(binding) for binding in bindings ]

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
        assert name in BINDING_INFO, '"%s" isn\'t a valid keyboard action.' % name

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
        assert name in BINDING_INFO, '"%s" isn\'t a valid keyboard action.' % name

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

        for action in BINDING_INFO.keys():
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

    def _migrate_from_old_bindings(self):
        ''' This method deals with upgrading from MComix 1.0 and older to
        MComix 1.01, which integrated all UI hotkeys into this class. Simply
        remove old files and start from default values. '''
        gtkrc = os.path.join(constants.CONFIG_DIR, 'keybindings-Gtk.rc')
        if os.path.isfile(gtkrc):
            # In case the user has made modifications to his files,
            # keep the old ones around for reference.
            if not os.path.isfile(gtkrc + '.delete-me'):
                shutil.move(gtkrc, gtkrc + '.delete-me')

            if os.path.isfile(constants.KEYBINDINGS_CONF_PATH) and \
                not os.path.isfile(constants.KEYBINDINGS_CONF_PATH + '.delete-me'):
                shutil.move(constants.KEYBINDINGS_CONF_PATH,
                        constants.KEYBINDINGS_CONF_PATH + '.delete-me')

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

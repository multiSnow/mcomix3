"""preferences.py - Contains the preferences and the functions to read and write them."""

import os
import cPickle
import gtk
import constants

# All the preferences are stored here.
prefs = {
    'comment extensions': constants.ACCEPTED_COMMENT_EXTENSIONS,
    'auto load last file': False,
    'page of last file': 1,
    'path to last file': '',
    'number of key presses before page turn': 3,
    'auto open next archive': True,
    'bg colour': (5000, 5000, 5000),
    'thumb bg colour': (5000, 5000, 5000),
    'smart bg': False,
    'smart thumb bg': False,
    'thumbnail bg uses main colour': False,
    'checkered bg for transparent images': True,
    'cache': True,
    'stretch': False,
    'default double page': False,
    'default fullscreen': False,
    'default zoom mode': constants.ZOOM_MODE_BEST,
    'default manga mode': False,
    'lens magnification': 2,
    'lens size': 200,
    'no double page for wide images': False,
    'double step in double page mode': True,
    'show page numbers': True,
    'show page numbers on thumbnails': True,
    'thumbnail size': 80,
    'create thumbnails': True,
    'number of pixels to scroll per key event': 50,
    'number of pixels to scroll per mouse wheel event': 50,
    'slideshow delay': 3000,
    'slideshow can go to next archive': True,
    'number of pixels to scroll per slideshow event': 50,
    'smart space scroll': True,
    'flip with wheel': True,
    'store recent file info': True,
    'hide all': False,
    'hide all in fullscreen': True,
    'stored hide all values': (True, True, True, True, True),
    'path of last browsed in filechooser': constants.HOME_DIR,
    'last filter in main filechooser': 0,
    'last filter in library filechooser': 1,
    'show menubar': True,
    'crash recovery on': True,
    'crash recovery seconds': 30,
    'previous quit was quit and save': False,
    'show scrollbar': True,
    'show statusbar': True,
    'show toolbar': True,
    'show thumbnails': True,
    'rotation': 0,
    'auto rotate from exif': True,
    'vertical flip': False,
    'horizontal flip': False,
    'focus protection': True,
    'keep transformation': False,
    'max pages to cache': 5,
    'window height': gtk.gdk.screen_get_default().get_height() * 3 // 4,
    'window width': min(gtk.gdk.screen_get_default().get_width() * 3 // 4,
                        gtk.gdk.screen_get_default().get_height() * 5 // 8),
    'library cover size': 128,
    'auto add books into collections': True,
    'last library collection': None,
    'lib window height': gtk.gdk.screen_get_default().get_height() * 3 // 4,
    'lib window width': gtk.gdk.screen_get_default().get_width() * 3 // 4
}

def read_preferences_file():
    """Read preferences data from disk."""
    if os.path.isfile(constants.PREFERENCE_PICKLE_PATH):
        config = None
        try:
            config = open(constants.PREFERENCE_PICKLE_PATH, 'rb')
            version = cPickle.load(config)
            old_prefs = cPickle.load(config)
            config.close()
        except Exception:
            print _('! Corrupt preferences file "') + constants.PREFERENCE_PICKLE_PATH + _('", deleting...')
            if config is not None:
                config.close()
            os.remove(constants.PREFERENCE_PICKLE_PATH)
        else:
            for key in old_prefs:
                if key in prefs:
                    prefs[key] = old_prefs[key]

def write_preferences_file():
    """Write preference data to disk."""
    config = open(constants.PREFERENCE_PICKLE_PATH, 'wb')
    cPickle.dump(constants.VERSION, config, cPickle.HIGHEST_PROTOCOL)
    cPickle.dump(prefs, config, cPickle.HIGHEST_PROTOCOL)
    config.close()

# vim: expandtab:sw=4:ts=4

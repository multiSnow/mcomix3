""" preferences.py - Contains the preferences and the functions to read and
write them.  """

import os
import pickle
import json

from mcomix import constants

# All the preferences are stored here.
prefs = {
    'comment extensions': constants.ACCEPTED_COMMENT_EXTENSIONS,
    'auto load last file': False,
    'page of last file': 1,
    'path to last file': '',
    'number of key presses before page turn': 3,
    'auto open next archive': True,
    'auto open next directory': True,
    'sort by': constants.SORT_NAME,  # Normal files obtained by directory listing
    'sort order': constants.SORT_ASCENDING,
    'sort archive by': constants.SORT_NAME,  # Files in archives
    'sort archive order': constants.SORT_ASCENDING,
    'bg colour': [5000, 5000, 5000],
    'thumb bg colour': [5000, 5000, 5000],
    'smart bg': False,
    'smart thumb bg': False,
    'thumbnail bg uses main colour': False,
    'checkered bg for transparent images': True,
    'cache': True,
    'stretch': False,
    'default double page': False,
    'default fullscreen': False,
    'zoom mode': constants.ZOOM_MODE_BEST,
    'default manga mode': False,
    'lens magnification': 2,
    'lens size': 200,
    'virtual double page for fitting images': constants.SHOW_DOUBLE_AS_ONE_TITLE | \
                                              constants.SHOW_DOUBLE_AS_ONE_WIDE,
    'double step in double page mode': True,
    'show page numbers on thumbnails': True,
    'thumbnail size': 80,
    'create thumbnails': True,
    'archive thumbnail as icon' : False,
    'number of pixels to scroll per key event': 50,
    'number of pixels to scroll per mouse wheel event': 50,
    'slideshow delay': 3000,
    'slideshow can go to next archive': True,
    'number of pixels to scroll per slideshow event': 50,
    'smart scroll': True,
    'invert smart scroll': False,
    'smart scroll percentage': 0.5,
    'flip with wheel': True,
    'store recent file info': True,
    'hide all': False,
    'hide all in fullscreen': True,
    'stored hide all values': [True, True, True, True, True],
    'path of last browsed in filechooser': constants.HOME_DIR,
    'last filter in main filechooser': 0,
    'last filter in library filechooser': 1,
    'show menubar': True,
    'previous quit was quit and save': False,
    'show scrollbar': True,
    'show statusbar': True,
    'show toolbar': True,
    'show thumbnails': True,
    'rotation': 0,
    'auto rotate from exif': True,
    'auto rotate depending on size': constants.AUTOROTATE_NEVER,
    'vertical flip': False,
    'horizontal flip': False,
    'keep transformation': False,
    'stored dialog choices': {},
    'brightness': 1.0,
    'contrast': 1.0,
    'saturation': 1.0,
    'sharpness': 1.0,
    'auto contrast': False,
    'max pages to cache': 7,
    'window x': 0,
    'window y': 0,
    'window height': 600,
    'window width': 640,
    'pageselector height': -1,
    'pageselector width': -1,
    'library cover size': 125,
    'last library collection': None,
    'lib window height': 600,
    'lib window width': 500,
    'lib sort key': constants.SORT_PATH,
    'lib sort order': constants.SORT_ASCENDING,
    'language': 'auto',
    'statusbar fields': constants.STATUS_PAGE | constants.STATUS_RESOLUTION | \
                        constants.STATUS_PATH | constants.STATUS_FILENAME | constants.STATUS_FILESIZE,
    'max threads': 3,
    'max extract threads': 1,
    'wrap mouse scroll': False,
    'scaling quality': 2,  # GdkPixbuf.InterpType.BILINEAR
    'escape quits': False,
    'fit to size mode': constants.ZOOM_MODE_HEIGHT,
    'fit to size px': 1800,
    'scan for new books on library startup': True,
    'openwith commands': [],  # (label, command) pairs
    'animation mode': constants.ANIMATION_DISABLED,
}

def read_preferences_file():
    """Read preferences data from disk."""

    saved_prefs = None

    if os.path.isfile(constants.PREFERENCE_PATH):
        try:
            with open(constants.PREFERENCE_PATH, 'r') as config_file:
                saved_prefs = json.load(config_file)
        except:
            # Gettext might not be installed yet at this point.
            corrupt_name = "%s.broken" % constants.PREFERENCE_PATH
            print ('! Corrupt preferences file, moving to "%s".' %
                   corrupt_name)
            if os.path.isfile(corrupt_name):
                os.unlink(corrupt_name)

            os.rename(constants.PREFERENCE_PATH, corrupt_name)

    elif os.path.isfile(constants.PREFERENCE_PICKLE_PATH):
        try:
            with open(constants.PREFERENCE_PICKLE_PATH, 'rb') as config_file:
                version = pickle.load(config_file)
                saved_prefs = pickle.load(config_file)

            # Remove legacy format preferences file
            os.unlink(constants.PREFERENCE_PICKLE_PATH)
        except Exception:
            # Gettext might not be installed yet at this point.
            print ('! Corrupt legacy preferences file "%s", ignoring...' %
                   constants.PREFERENCE_PICKLE_PATH)

    if saved_prefs:
        for key in saved_prefs:
            if key in prefs:
                prefs[key] = saved_prefs[key]

def write_preferences_file():
    """Write preference data to disk."""
    # TODO: it might be better to save only those options that were (ever)
    # explicitly changed by the used, leaving everything else as default
    # and available (if really needed) to change of defaults on upgrade.
    with open(constants.PREFERENCE_PATH, 'w') as config_file:
        # XXX: constants.VERSION? It's *preferable* to not complicate the YAML
        # file by adding a `{'version': constants.VERSION, 'prefs': config}`
        # dict or a list.  Adding an extra init line sounds bad too.
        json.dump(prefs, config_file, indent=2)

# vim: expandtab:sw=4:ts=4

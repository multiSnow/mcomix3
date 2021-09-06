''' preferences.py - Contains the preferences and the functions to read and
write them.  '''

import os
import json

from hashlib import md5

from mcomix import constants
from mcomix import log

_prefs_status={'md5':None}

# All the preferences are stored here.
prefs = {
    'comment extensions': constants.ACCEPTED_COMMENT_EXTENSIONS,
    'auto load last file': False,
    'page of last file': 1,
    'path to last file': '',
    'number of key presses before page turn': 3,
    'auto open next archive': True,
    'auto open next directory': True,
    'open first file in prev archive': False,
    'open first file in prev directory': False,
    'dive into subdir': False,
    'sort by': constants.SORT_NAME,  # Normal files obtained by directory listing
    'sort order': constants.SORT_ASCENDING,
    'sort archive by': constants.SORT_NAME,  # Files in archives
    'sort archive order': constants.SORT_ASCENDING,
    'bg colour': [0, 0, 0, 0],
    'thumb bg colour': [0, 0, 0, 0],
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
    'mouse position affects navigation': True,
    'invert smart scroll': False,
    'smart scroll percentage': 0.5,
    'flip with wheel': True,
    'flip with click': True,
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
    'max thumbnail threads': 3,
    'max extract threads': 1,
    'wrap mouse scroll': False,
    'scaling quality': 2,  # GdkPixbuf.InterpType.BILINEAR
    'pil scaling filter': -1, # Use a PIL filter (just lanczos for now) in main viewing area. -1 to just use GdkPixbuf
    'escape quits': False,
    'fit to size mode': constants.ZOOM_MODE_HEIGHT,
    'fit to size px': 1800,
    'scan for new books on library startup': True,
    'openwith commands': [],  # (label, command) pairs # keep but no longer used
    'external commands': [],  # (label, command) pairs
    'animation mode': constants.ANIMATION_DISABLED,
    'animation background': False,
    'animation transform': False,
    'temporary directory': None,
    'portable allow abspath': False,
    'osd max font size': 16, # hard limited from 8 to 60
    'osd color': [1, 1, 1, 1],
    'osd bg color': [0, 0, 0, 1],
    'osd timeout': 3.0,  # in seconds, hard limited from 0.5 to 30.0
    'userstyle': None,  # None to disable userstyle
    'mount': False,
    'check image mimetype': False,
    'keyhandler cmd': [],
    'keyhandler timeout': 3000, # millisecond
    'keyhandler close delay': 1000, # millisecond
    'keyhandler show result': True,
}

def _md5str(s):
    return md5(s.encode('utf8')).hexdigest()

def check_old_preferences(saved_prefs):
    bookmarks_pickle = os.path.join(constants.DATA_DIR, 'bookmarks.pickle')
    fileinfo_pickle = os.path.join(constants.DATA_DIR, 'file.pickle')

    old_bookmarks = os.path.exists(bookmarks_pickle)
    old_fileinfo = os.path.exists(fileinfo_pickle)
    old_prefs = saved_prefs and 'external commands' not in saved_prefs

    if old_bookmarks or old_fileinfo or old_prefs:
        from mcomix import upgrade_tools
        if old_prefs:
            upgrade_tools.openwith_conv(saved_prefs)
            os.rename(constants.PREFERENCE_PATH, constants.PREFERENCE_PATH+'.bak')
        if old_bookmarks:
            upgrade_tools.bookmarks_conv(
                bookmarks_pickle, constants.BOOKMARK_JSON_PATH)
        if old_fileinfo:
            upgrade_tools.fileinfo_conv(
                fileinfo_pickle, constants.FILEINFO_JSON_PATH)

    if saved_prefs.get('scaling quality')==3:
        # deprecate GdkPixbuf.InterpType.HYPER with GdkPixbuf.InterpType.BILINEAR
        saved_prefs['scaling quality']=2

def read_preferences_file():
    '''Read preferences data from disk.'''

    saved_prefs = {}

    if os.path.isfile(constants.PREFERENCE_PATH):
        try:
            with open(constants.PREFERENCE_PATH, mode='rt') as config_file:
                saved_prefs.update(json.load(config_file))
        except:
            # Gettext might not be installed yet at this point.
            corrupt_name = constants.PREFERENCE_PATH + '.broken'
            log.warning('! Corrupt preferences file, moving to "%s".' %
                        corrupt_name)
            if os.path.isfile(corrupt_name):
                os.unlink(corrupt_name)

            os.rename(constants.PREFERENCE_PATH, corrupt_name)

    check_old_preferences(saved_prefs)

    prefs.update(filter(lambda i:i[0] in prefs,saved_prefs.items()))

    _prefs_status['md5'] = _md5str(json.dumps(prefs, indent=2, sort_keys=True))

def write_preferences_file():
    '''Write preference data to disk.'''
    # XXX: constants.VERSION? It's *preferable* to not complicate the YAML
    # file by adding a `{'version': constants.VERSION, 'prefs': config}`
    # dict or a list.  Adding an extra init line sounds bad too.
    json_prefs = json.dumps(prefs, indent=2, sort_keys=True)
    md5hash = _md5str(json_prefs)
    if md5hash == _prefs_status['md5']:
        # nothing changed, nothing to write
        return
    _prefs_status['md5'] = md5hash
    # TODO: it might be better to save only those options that were (ever)
    # explicitly changed by the used, leaving everything else as default
    # and available (if really needed) to change of defaults on upgrade.
    with open(constants.PREFERENCE_PATH, mode='wt') as config_file:
        print(json_prefs, file=config_file)

# vim: expandtab:sw=4:ts=4

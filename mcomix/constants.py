# -*- coding: utf-8 -*-
"""constants.py - Miscellaneous constants."""

import gtk
import re
import tools
import os
import sys

APPNAME = 'MComix'
VERSION = '0.90.4'

HOME_DIR = tools.get_home_directory()
CONFIG_DIR = tools.get_config_directory()
DATA_DIR = tools.get_data_directory()

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
THUMBNAIL_PATH = os.path.join(HOME_DIR, '.thumbnails/normal')
LIBRARY_DATABASE_PATH = os.path.join(DATA_DIR, 'library.db')
LIBRARY_COVERS_PATH = os.path.join(DATA_DIR, 'library_covers')

BOOKMARK_PICKLE_PATH = os.path.join(DATA_DIR, 'bookmarks.pickle')
PREFERENCE_PICKLE_PATH = os.path.join(CONFIG_DIR, 'preferences.pickle')
FILEINFO_PICKLE_PATH = os.path.join(DATA_DIR, 'file.pickle')
CRASH_PICKLE_PATH = os.path.join(CONFIG_DIR, 'crash.pickle')

ZOOM_MODE_BEST, ZOOM_MODE_WIDTH, ZOOM_MODE_HEIGHT, ZOOM_MODE_MANUAL = range(4)
ZIP, RAR, TAR, GZIP, BZIP2, PDF, SEVENZIP = range(7)
NORMAL_CURSOR, GRAB_CURSOR, WAIT_CURSOR = range(3)
LIBRARY_DRAG_EXTERNAL_ID, LIBRARY_DRAG_BOOK_ID, LIBRARY_DRAG_COLLECTION_ID = range(3)

RESPONSE_SORT_DESCENDING = 1
RESPONSE_SORT_ASCENDING = 2
RESPONSE_REVERT_TO_DEFAULT = 3
RESPONSE_REMOVE = 4
RESPONSE_IMPORT = 5
RESPONSE_APPLY_CHANGES = 6
RESPONSE_SAVE_AS = 7

ACCEPTED_COMMENT_EXTENSIONS = ['txt', 'nfo']
SUPPORTED_IMAGE_REGEX = re.compile(r'\.(jpg|jpeg|png|gif|tif|tiff|bmp|ppm|pgm|pbm)\s*$', re.I)
SUPPORTED_ARCHIVE_REGEX = re.compile(r'\.(cbz|cbr|cbt|zip|rar|tar|gz|bz2|bzip2|7z)\s*$', re.I)

_missing_icon_dialog = gtk.Dialog(None,None,0,None)
_missing_icon_pixbuf = _missing_icon_dialog.render_icon(gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_LARGE_TOOLBAR)
MISSING_IMAGE_ICON = _missing_icon_pixbuf.scale_simple( 128, 128, gtk.gdk.INTERP_TILES )

MAX_LIBRARY_COVER_SIZE = 500

# vim: expandtab:sw=4:ts=4

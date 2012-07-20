# -*- coding: utf-8 -*-
"""constants.py - Miscellaneous constants."""

import re
import os

from mcomix import tools

APPNAME = 'MComix'
VERSION = '0.99'

HOME_DIR = tools.get_home_directory()
CONFIG_DIR = tools.get_config_directory()
DATA_DIR = tools.get_data_directory()

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
THUMBNAIL_PATH = os.path.join(HOME_DIR, '.thumbnails/normal')
LIBRARY_DATABASE_PATH = os.path.join(DATA_DIR, 'library.db')
LASTPAGE_DATABASE_PATH = os.path.join(DATA_DIR, 'lastreadpage.db')
LIBRARY_COVERS_PATH = os.path.join(DATA_DIR, 'library_covers')
PREFERENCE_PATH = os.path.join(CONFIG_DIR, 'preferences.conf')
KEYBINDINGS_PATH = os.path.join(CONFIG_DIR, 'keybindings-gtk.rc')
KEYBINDINGS_CONF_PATH = os.path.join(CONFIG_DIR, 'keybindings.conf')

BOOKMARK_PICKLE_PATH = os.path.join(DATA_DIR, 'bookmarks.pickle')
FILEINFO_PICKLE_PATH = os.path.join(DATA_DIR, 'file.pickle')
# Transitional - used if json preferences are (were) absent.
PREFERENCE_PICKLE_PATH = os.path.join(CONFIG_DIR, 'preferences.pickle')

ZOOM_MODE_BEST, ZOOM_MODE_WIDTH, ZOOM_MODE_HEIGHT, ZOOM_MODE_MANUAL, ZOOM_MODE_SIZE = range(5)
ZIP, RAR, TAR, GZIP, BZIP2, PDF, SEVENZIP, LHA = range(8)
NORMAL_CURSOR, GRAB_CURSOR, WAIT_CURSOR, NO_CURSOR = range(4)
LIBRARY_DRAG_EXTERNAL_ID, LIBRARY_DRAG_BOOK_ID, LIBRARY_DRAG_COLLECTION_ID = range(3)

RESPONSE_REVERT_TO_DEFAULT = 3
RESPONSE_REMOVE = 4
RESPONSE_IMPORT = 5
RESPONSE_SAVE_AS = 6
RESPONSE_REPLACE = 7
RESPONSE_NEW = 8

# These are bit field values, so only use powers of two.
STATUS_PAGE, STATUS_RESOLUTION, STATUS_PATH, STATUS_FILENAME, STATUS_FILENUMBER = \
    1, 2, 4, 8, 16
SHOW_DOUBLE_AS_ONE_TITLE, SHOW_DOUBLE_AS_ONE_WIDE = 1, 2

MAX_LIBRARY_COVER_SIZE = 500
SORT_NAME, SORT_PATH, SORT_SIZE, SORT_LAST_MODIFIED = 1, 2, 3, 4
SORT_DESCENDING, SORT_ASCENDING = 1, 2
SIZE_HUGE, SIZE_LARGE, SIZE_NORMAL, SIZE_SMALL, SIZE_TINY = MAX_LIBRARY_COVER_SIZE, 300, 250, 125, 80

ACCEPTED_COMMENT_EXTENSIONS = ['txt', 'nfo', 'xml']
SUPPORTED_IMAGE_REGEX = re.compile(r'\.(jpg|jpeg|png|gif|tif|tiff|bmp|ppm|pgm|pbm)\s*$', re.I)

ZIP_FORMATS = (
        ('application/x-zip', 'application/zip', 'application/x-zip-compressed', 'application/x-cbz'),
        ('*.zip', '*.cbz'))
RAR_FORMATS = (
        ('application/x-rar', 'application/x-cbr'),
        ('*.rar', '*.cbr'))
TAR_FORMATS = (
        ('application/x-tar', 'application/x-gzip', 'application/x-bzip2', 'application/x-cbt'),
        ('*.tar', '*.gz', '*.bz2', '*.bzip2', '*.cbt'))
SZIP_FORMATS = (
        ('application/x-7z-compressed', 'application/x-cb7'),
        ('*.7z', '*.cb7'))
LHA_FORMATS = (
        ('application/x-lzh', 'application/x-lha', 'application/x-lzh-compressed'),
        ('*.lha', '*.lzh'))



MISSING_IMAGE_ICON = None
try:
    import gtk

    _missing_icon_dialog = gtk.Dialog(None,None,0,None)
    _missing_icon_pixbuf = _missing_icon_dialog.render_icon(
            gtk.STOCK_MISSING_IMAGE, gtk.ICON_SIZE_LARGE_TOOLBAR)

    # Pixbuf is None when running without X server.
    # Setup.py could fail because of this.
    if _missing_icon_pixbuf:
        MISSING_IMAGE_ICON = _missing_icon_pixbuf.scale_simple(
                128, 128, gtk.gdk.INTERP_TILES)
except ImportError:
    # Missing GTK is already handled in mcomixstarter.py,
    # but this file is imported first, so ignore exceptions here.
    pass


# vim: expandtab:sw=4:ts=4

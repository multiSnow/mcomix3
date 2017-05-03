# -*- coding: utf-8 -*-
"""constants.py - Miscellaneous constants."""

import re
import os
import operator

from mcomix import tools

APPNAME = 'MComix'
VERSION = '1.3.dev0'

HOME_DIR = tools.get_home_directory()
CONFIG_DIR = tools.get_config_directory()
DATA_DIR = tools.get_data_directory()

BASE_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
THUMBNAIL_PATH = os.path.join(HOME_DIR, '.thumbnails/normal')
LIBRARY_DATABASE_PATH = os.path.join(DATA_DIR, 'library.db')
LASTPAGE_DATABASE_PATH = os.path.join(DATA_DIR, 'lastreadpage.db')
LIBRARY_COVERS_PATH = os.path.join(DATA_DIR, 'library_covers')
PREFERENCE_PATH = os.path.join(CONFIG_DIR, 'preferences.conf')
KEYBINDINGS_CONF_PATH = os.path.join(CONFIG_DIR, 'keybindings.conf')

BOOKMARK_PICKLE_PATH = os.path.join(DATA_DIR, 'bookmarks.pickle')
FILEINFO_PICKLE_PATH = os.path.join(DATA_DIR, 'file.pickle')
# Transitional - used if json preferences are (were) absent.
PREFERENCE_PICKLE_PATH = os.path.join(CONFIG_DIR, 'preferences.pickle')

ZOOM_MODE_BEST, ZOOM_MODE_WIDTH, ZOOM_MODE_HEIGHT, ZOOM_MODE_MANUAL, ZOOM_MODE_SIZE = range(5)

WIDTH_AXIS, HEIGHT_AXIS = range(2)
DISTRIBUTION_AXIS, ALIGNMENT_AXIS = WIDTH_AXIS, HEIGHT_AXIS
NORMAL_AXES = (0, 1)
SWAPPED_AXES = (1, 0)
WESTERN_ORIENTATION = (1, 1)
MANGA_ORIENTATION = (-1, 1)
SCROLL_TO_CENTER = -2
SCROLL_TO_START = -3
SCROLL_TO_END = -4
FIRST_INDEX = 0
LAST_INDEX = -1
UNION_INDEX = -2

ANIMATION_DISABLED, ANIMATION_NORMAL = range(2)

ZIP, RAR, TAR, GZIP, BZIP2, XZ, PDF, SEVENZIP, LHA, ZIP_EXTERNAL = range(10)
NORMAL_CURSOR, GRAB_CURSOR, WAIT_CURSOR, NO_CURSOR = range(4)
LIBRARY_DRAG_EXTERNAL_ID, LIBRARY_DRAG_BOOK_ID, LIBRARY_DRAG_COLLECTION_ID = range(3)
AUTOROTATE_NEVER, AUTOROTATE_WIDTH_90, AUTOROTATE_WIDTH_270, \
    AUTOROTATE_HEIGHT_90, AUTOROTATE_HEIGHT_270 = range(5)

RESPONSE_REVERT_TO_DEFAULT = 3
RESPONSE_REMOVE = 4
RESPONSE_IMPORT = 5
RESPONSE_SAVE_AS = 6
RESPONSE_REPLACE = 7
RESPONSE_NEW = 8

# These are bit field values, so only use powers of two.
STATUS_PAGE, STATUS_RESOLUTION, STATUS_PATH, STATUS_FILENAME, STATUS_FILENUMBER, STATUS_FILESIZE = \
    1, 2, 4, 8, 16, 32
SHOW_DOUBLE_AS_ONE_TITLE, SHOW_DOUBLE_AS_ONE_WIDE = 1, 2

MAX_LIBRARY_COVER_SIZE = 500
SORT_NAME, SORT_PATH, SORT_SIZE, SORT_LAST_MODIFIED, SORT_NAME_LITERAL = 1, 2, 3, 4, 5
SORT_DESCENDING, SORT_ASCENDING = 1, 2
SIZE_HUGE, SIZE_LARGE, SIZE_NORMAL, SIZE_SMALL, SIZE_TINY = MAX_LIBRARY_COVER_SIZE, 300, 250, 125, 80

ACCEPTED_COMMENT_EXTENSIONS = ['txt', 'nfo', 'xml']

ZIP_FORMATS = (
        ('application/x-zip', 'application/zip', 'application/x-zip-compressed', 'application/x-cbz'),
        ('zip', 'cbz'))
RAR_FORMATS = (
        ('application/x-rar', 'application/x-cbr'),
        ('rar', 'cbr'))
TAR_FORMATS = (
        ('application/x-tar', 'application/x-gzip', 'application/x-bzip2', 'application/x-cbt'),
        ('tar', 'gz', 'bz2', 'bzip2', 'cbt'))
SZIP_FORMATS = (
        ('application/x-7z-compressed', 'application/x-cb7'),
        ('7z', 'cb7', 'xz', 'lzma'))
LHA_FORMATS = (
        ('application/x-lzh', 'application/x-lha', 'application/x-lzh-compressed'),
        ('lha', 'lzh'))
PDF_FORMATS = (
        ('application/pdf',),
        ('pdf',))

# vim: expandtab:sw=4:ts=4

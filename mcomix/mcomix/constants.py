# -*- coding: utf-8 -*-
'''constants.py - Miscellaneous constants.'''

import re
import os
import operator

from mcomix import tools

APPNAME = 'MComix'
VERSION = '1.3.0.dev0'

REQUIRED_PIL_VERSION = '5.1.0'

STARTDIR = os.getcwd()
PORTABLE_MODE = tools.is_portable_mode()

HOME_DIR = tools.get_home_directory()
CONFIG_DIR = tools.get_config_directory()
DATA_DIR = tools.get_data_directory()

BASE_PATH = tools.rootdir()
THUMBNAIL_PATH = tools.get_thumbnails_directory()
LIBRARY_DATABASE_PATH = os.path.join(DATA_DIR, 'library.db')
LIBRARY_COVERS_PATH = os.path.join(DATA_DIR, 'library_covers')
PREFERENCE_PATH = os.path.join(CONFIG_DIR, 'preferences.conf')
KEYBINDINGS_CONF_PATH = os.path.join(CONFIG_DIR, 'keybindings.conf')

BOOKMARK_PICKLE_PATH = os.path.join(DATA_DIR, 'bookmarks.pickle')
FILEINFO_PICKLE_PATH = os.path.join(DATA_DIR, 'file.pickle')

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
ANIMATION_DISABLED = 0
ANIMATION_NORMAL = 1 # loop as animation setting
ANIMATION_ONCE = 1<<1 # loop only once
ANIMATION_INF = 1<<2 # loop infinity

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

# see https://www.freedesktop.org/wiki/Software/shared-mime-info/
# for mimetypes not registed to IANA

ZIP_FORMATS = (
    # https://www.iana.org/assignments/media-types/application/zip
    ('.zip', 'application/zip'),
    # https://www.iana.org/assignments/media-types/application/vnd.comicbook+zip
    ('.cbz', 'application/vnd.comicbook+zip'),
)

RAR_FORMATS = (
    # https://www.iana.org/assignments/media-types/application/vnd.rar
    ('.rar', 'application/vnd.rar'),
    # https://www.iana.org/assignments/media-types/application/vnd.comicbook-rar
    ('.cbr', 'application/vnd.comicbook-rar'),
)

TAR_FORMATS = (
    # not registed in IANA
    ('.tar', 'application/x-tar'),
    # not registed in IANA
    ('.cbt', 'application/x-cbt'),

    # see https://www.gnu.org/software/tar/manual/html_section/tar_68.html#auto_002dcompress
    # and https://git.savannah.gnu.org/cgit/tar.git/commit/?id=2c06a80918019471876956eef4ef22f05c9e0571
    # for compressed tar

    # gzip
    ('.tar.gz',   'application/x-compressed-tar'),
    ('.tgz',      'application/x-compressed-tar'),
    # bzip2
    ('.tar.bz2',  'application/x-bzip-compressed-tar'),
    ('.tar.bz',   'application/x-bzip-compressed-tar'),
    ('.tbz2',     'application/x-bzip-compressed-tar'),
    ('.tbz',      'application/x-bzip-compressed-tar'),
    ('.tb2',      'application/x-bzip-compressed-tar'),
    # lzma
    ('.tar.lzma', 'application/x-lzma-compressed-tar'),
    ('.tlz',      'application/x-lzma-compressed-tar'),
    # xz
    ('.tar.xz',   'application/x-xz-compressed-tar'),
    ('.txz',      'application/x-xz-compressed-tar'),
)

SZIP_FORMATS = (
    # not registed in IANA
    ('.7z',  'application/x-7z-compressed'),
    # not registed in IANA
    ('.cb7', 'application/x-cb7'),
)

LHA_FORMATS = (
    # not registed in IANA
    ('.lha', 'application/x-lha'),
    # not registed in IANA
    ('.lzh', 'application/x-lha'),
)

PDF_FORMATS = (
    # https://www.iana.org/assignments/media-types/application/pdf
    ('.pdf','application/pdf'),
)

ARCHIVE_FORMATS = ZIP_FORMATS + RAR_FORMATS + TAR_FORMATS
ARCHIVE_FORMATS += SZIP_FORMATS + LHA_FORMATS + PDF_FORMATS

# vim: expandtab:sw=4:ts=4

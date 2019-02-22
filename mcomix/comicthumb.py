#!/usr/bin/env python3

"""comicthumb - Thumbnailer for comic book archives, bundled with MComix.

comicthumb is dependent on the Python Imaging Library (PIL).

comicthumb was originally written by Christoph Wolk, this version was
re-written from scratch for Comix 4 by Pontus Ekberg. 

Supported formats: ZIP, RAR and tar (.cbz, .cbr, .cbt)

Usage: comicthumb INFILE OUTFILE [SIZE]
"""
from gi import require_version

require_version('GdkPixbuf', '2.0')
require_version('Gdk', '3.0')
require_version('Gtk', '3.0')

from mcomix import thumbnail_tools
from mcomix import portability

import sys
from urllib.parse import unquote

if __name__ == '__main__':
    argv = sys.argv[1:]
    try:
        in_path = argv[0]
        out_path = argv[1]
        if len(argv) == 3:
            size = int(argv[2])
        else:
            size = 128
    except:
        print(__doc__)
        sys.exit(1)

    if in_path.startswith('file://'):
        in_path = unquote(in_path[7:])

    thumbnailer = thumbnail_tools.Thumbnailer(force_recreation=True,
                                              archive_support=True,
                                              store_on_disk=False,
                                              size=(size, size))
    thumb = thumbnailer.thumbnail(in_path)
    thumb.savev(out_path, 'png', [], [])

    sys.exit(0)


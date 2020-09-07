#!/usr/bin/env python3

'''comicthumb - Thumbnailer for comic book archives, bundled with MComix.

comicthumb use same dependency with MComix.

comicthumb was originally written by Christoph Wolk, this version was
re-written from scratch for Comix 4 by Pontus Ekberg.
'''

import argparse
from os import getcwd
from os.path import exists,join,normpath
from urllib.parse import unquote

from gi import require_version

require_version('GdkPixbuf', '2.0')

CURDIR=getcwd()

from mcomix import tools
tools.nogui()
from mcomix import thumbnail_tools
from mcomix import portability

THUMB_SIZE=128
URL_PREFIX='file://'

def abspath(path):
    return normpath(join(CURDIR,path))

def main():
    parser=argparse.ArgumentParser(
        prog='comicthumb',
        description='Thumbnailer for comic book archives',
        epilog='Supported formats: ZIP, RAR and tar (.cbz, .cbr, .cbt)',
    )
    parser.add_argument('infile',default=None,metavar='INFILE',
                        help='input archive')
    parser.add_argument('outfile',default=None,metavar='OUTFILE',
                        help='output thumbnail')
    parser.add_argument('size',nargs='?',default=THUMB_SIZE,metavar='SIZE',
                        help='size of thumbnail (default: {})'.format(THUMB_SIZE))
    ns=parser.parse_args()
    in_path=abspath(ns.infile)
    out_path=abspath(ns.outfile)
    if in_path.startswith(URL_PREFIX):
        in_path=unquote(in_path[len(URL_PREFIX):])
    if not exists(in_path):
        print('not exists:',ns.infile)
        parser.print_usage()
        return 1
    try:
        size=int(ns.size)
    except ValueError:
        print('invalid SIZE:',ns.size)
        parser.print_usage()
        return 1

    thumbnailer = thumbnail_tools.Thumbnailer(force_recreation=True,
                                              archive_support=True,
                                              store_on_disk=False,
                                              size=(size, size))
    thumb = thumbnailer.thumbnail(in_path)
    if thumb:
        thumb.savev(out_path, 'png', [], [])
    else:
        print('unsupported file:',in_path)
        print('please see https://github.com/multiSnow/mcomix3/blob/gtk3/README.rst')
        print('for supported format and required library/tool.')
        return 1

if __name__ == '__main__':
    exit(main())


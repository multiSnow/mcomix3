"""icons.py - Load Comix specific icons."""

import os
import sys

import gtk

def load_icons():
    _icons = (('gimp-flip-horizontal.png',   'comix-flip-horizontal'),
              ('gimp-flip-vertical.png',     'comix-flip-vertical'),
              ('gimp-rotate-180.png',        'comix-rotate-180'),
              ('gimp-rotate-270.png',        'comix-rotate-270'),
              ('gimp-rotate-90.png',         'comix-rotate-90'),
              ('gimp-thumbnails.png',        'comix-thumbnails'),
              ('gimp-transform.png',         'comix-transform'),
              ('tango-enhance-image.png',    'comix-enhance-image'),
              ('tango-add-bookmark.png',     'comix-add-bookmark'),
              ('tango-archive.png',          'comix-archive'),
              ('tango-image.png',            'comix-image'),
              ('library.png',                'comix-library'),
              ('comments.png',               'comix-comments'),
              ('zoom.png',                   'comix-zoom'),
              ('lens.png',                   'comix-lens'),
              ('double-page.png',            'comix-double-page'),
              ('manga.png',                  'comix-manga'),
              ('fitbest.png',                'comix-fitbest'),
              ('fitwidth.png',               'comix-fitwidth'),
              ('fitheight.png',              'comix-fitheight'),
              ('fitmanual.png',              'comix-fitmanual'))
    
    icon_path = None
    # Some heuristics to find the path to the icon image files.
    base = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
    # Try source directory.
    if os.path.isfile(os.path.join(base, 'images/16x16/comix.png')):
        icon_path = os.path.join(base, 'images')
    else: # Try system directories.
        for prefix in [base, '/usr', '/usr/local', '/usr/X11R6']:
            if os.path.isfile(os.path.join(prefix,
              'share/comix/images/16x16/comix.png')): # Try one
                icon_path = os.path.join(prefix, 'share/comix/images')
                break
    if icon_path is None:
        return
    
    # Load window title icon.
    pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(icon_path,
        '16x16/comix.png'))
    gtk.window_set_default_icon(pixbuf)
    # Load application icons.
    factory = gtk.IconFactory()
    for filename, stockid in _icons:
        try:
            filename = os.path.join(icon_path, filename)
            pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
            iconset = gtk.IconSet(pixbuf)
            factory.add(stockid, iconset)
        except Exception:
            print '! Could not load icon "%s".' % filename
    factory.add_default()

"""icons.py - Load MComix specific icons."""

import os
import gtk
import constants
import image_tools

def load_icons():
    _icons = (('gimp-flip-horizontal.png',   'mcomix-flip-horizontal'),
              ('gimp-flip-vertical.png',     'mcomix-flip-vertical'),
              ('gimp-rotate-180.png',        'mcomix-rotate-180'),
              ('gimp-rotate-270.png',        'mcomix-rotate-270'),
              ('gimp-rotate-90.png',         'mcomix-rotate-90'),
              ('gimp-thumbnails.png',        'mcomix-thumbnails'),
              ('gimp-transform.png',         'mcomix-transform'),
              ('tango-enhance-image.png',    'mcomix-enhance-image'),
              ('tango-add-bookmark.png',     'mcomix-add-bookmark'),
              ('tango-archive.png',          'mcomix-archive'),
              ('tango-image.png',            'mcomix-image'),
              ('library.png',                'mcomix-library'),
              ('comments.png',               'mcomix-comments'),
              ('zoom.png',                   'mcomix-zoom'),
              ('lens.png',                   'mcomix-lens'),
              ('double-page.png',            'mcomix-double-page'),
              ('manga.png',                  'mcomix-manga'),
              ('fitbest.png',                'mcomix-fitbest'),
              ('fitwidth.png',               'mcomix-fitwidth'),
              ('fitheight.png',              'mcomix-fitheight'),
              ('fitmanual.png',              'mcomix-fitmanual'),
              ('gtk-refresh.png',            'mcomix-refresh'),
              ('goto-first-page.png',        'mcomix-goto-first-page'),
              ('goto-last-page.png',         'mcomix-goto-last-page'),
              ('next-page.png',              'mcomix-next-page'),
              ('previous-page.png',          'mcomix-previous-page'),
              ('next-archive.png',           'mcomix-next-archive'),
              ('previous-archive.png',       'mcomix-previous-archive'))
    
    icon_path = None
    # Try source directory.
    if os.path.isfile(os.path.join(constants.BASE_PATH, 'images/16x16/mcomix.png')):
        icon_path = os.path.join(constants.BASE_PATH, 'images')
    else: # Try system directories.
        for prefix in [constants.BASE_PATH, '/usr', '/usr/local', '/usr/X11R6']:
            if os.path.isfile(os.path.join(prefix,
              'share/mcomix/images/16x16/mcomix.png')): # Try one
                icon_path = os.path.join(prefix, 'share/mcomix/images')
                break
    if icon_path is None:
        return
    
    # Load window title icon.
    pixbuf = image_tools.load_pixbuf(os.path.join(icon_path,
        '16x16/mcomix.png'))
    gtk.window_set_default_icon(pixbuf)
    # Load application icons.
    factory = gtk.IconFactory()
    for filename, stockid in _icons:
        try:
            filename = os.path.join(icon_path, filename)
            pixbuf = image_tools.load_pixbuf(filename)
            iconset = gtk.IconSet(pixbuf)
            factory.add(stockid, iconset)
        except Exception:
            print _('! Could not load icon "') + filename + '".'
    factory.add_default()



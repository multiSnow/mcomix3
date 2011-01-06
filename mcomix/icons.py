"""icons.py - Load MComix specific icons."""

import os
import gtk
import constants
import image_tools

from pkg_resources import resource_string

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

    # Load window title icon.
    icon_data = resource_string('mcomix.images', '16x16/mcomix.png')
    pixbuf = image_tools.load_pixbuf_data(icon_data)
    gtk.window_set_default_icon(pixbuf)
    # Load application icons.
    factory = gtk.IconFactory()
    for filename, stockid in _icons:
        try:
            icon_data = resource_string('mcomix.images', filename)
            pixbuf = image_tools.load_pixbuf_data(icon_data)
            iconset = gtk.IconSet(pixbuf)
            factory.add(stockid, iconset)
        except Exception:
            print _('! Could not load icon "%s"') % filename
    factory.add_default()



# vim: expandtab:sw=4:ts=4

"""icons.py - Load MComix specific icons."""

import gtk
import image_tools

from pkg_resources import resource_string

def mcomix_icons():
    """ Returns a list of differently sized pixbufs for the
    application icon. """

    sizes = ('16x16', '32x32', '48x48')
    pixbufs = [ 
        image_tools.load_pixbuf_data(
            resource_string('mcomix.images', size + '/mcomix.png')
        ) for size in sizes
    ]

    return pixbufs

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
              ('goto-first-page.png',        'mcomix-goto-first-page'),
              ('goto-last-page.png',         'mcomix-goto-last-page'),
              ('next-page.png',              'mcomix-next-page'),
              ('previous-page.png',          'mcomix-previous-page'),
              ('next-archive.png',           'mcomix-next-archive'),
              ('previous-archive.png',       'mcomix-previous-archive'),
              ('next-directory.png',         'mcomix-next-directory'),
              ('previous-directory.png',     'mcomix-previous-directory'))

    # Load window title icons.
    pixbufs = mcomix_icons()
    gtk.window_set_default_icon_list(*pixbufs)
    # Load application icons.
    factory = gtk.IconFactory()
    for filename, stockid in _icons:
        try:
            icon_data = resource_string('mcomix.images', filename)
            pixbuf = image_tools.load_pixbuf_data(icon_data)
            iconset = gtk.IconSet(pixbuf)
            factory.add(stockid, iconset)
        except Exception:
            print_( _('! Could not load icon "%s"') % filename )
    factory.add_default()



# vim: expandtab:sw=4:ts=4

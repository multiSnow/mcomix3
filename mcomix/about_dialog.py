# -*- coding: utf-8 -*-
"""about_dialog.py - About dialog."""

import os
import gtk
import constants
import labels

class _AboutDialog(gtk.Dialog):

    def __init__(self, window):
        gtk.Dialog.__init__(self, _('About'), window, 0,
            (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.set_has_separator(False)
        self.set_resizable(False)
        self.set_default_response(gtk.RESPONSE_CLOSE)

        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, False, False, 0)
        self.set_border_width(4)
        notebook.set_border_width(6)

        # ----------------------------------------------------------------
        # About tab.
        # ----------------------------------------------------------------
        box = gtk.VBox(False, 0)
        box.set_border_width(5)

        icon_path = os.path.join(constants.BASE_PATH, 'images/mcomix.png')

        if not os.path.isfile(icon_path):
            for prefix in [constants.BASE_PATH, '/usr', '/usr/local', '/usr/X11R6']:
                icon_path = os.path.join(prefix, 'share/mcomix/images/mcomix.png')

                if os.path.isfile(icon_path):
                    break

        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(icon_path, 200, 200)
            icon = gtk.Image()
            icon.set_from_pixbuf(pixbuf)
            box.pack_start(icon, False, False, 10)
        except Exception:
            print _('! Could not find the icon file "mcomix.png"\n')

        label = gtk.Label()
        label.set_markup(
        '<big><big><big><big><b><span foreground="#7E3517">MC</span>' +
        '<span foreground="#79941b">omix</span> <span foreground="#333333">' +
        constants.VERSION +
        '</span></b></big></big></big></big>\n\n' +
        _('MComix is an image viewer specifically designed to handle comic books.') +
        '\n' +
        _('It reads ZIP, RAR and tar archives, as well as plain image files.') +
        '\n\n' +
        _('MComix is released to the public domain.') +
        '\n\n' +
        '<small>Lead Developer:\n' +
        'Louis Casillas, oxaric@gmail.com\n' +
        'http://mcomix.sourceforge.net</small>\n')

        box.pack_start(label, True, True, 0)
        label.set_justify(gtk.JUSTIFY_CENTER)
        label.set_selectable(True)
        notebook.insert_page(box, gtk.Label(_('About')))

        # ----------------------------------------------------------------
        # Credits tab.
        # ----------------------------------------------------------------
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        hbox = gtk.HBox(False, 5)
        hbox.set_border_width(5)
        scrolled.add_with_viewport(hbox)

        left_box = gtk.VBox(True, 8)
        right_box = gtk.VBox(True, 8)

        hbox.pack_start(left_box, False, False)
        hbox.pack_start(right_box, False, False)

        for nice_person, description in constants.CREDITS:
            name_label = labels.BoldLabel('%s:' % nice_person)
            name_label.set_alignment(1.0, 1.0)

            left_box.pack_start(name_label, True, True)
            desc_label = gtk.Label(description)
            desc_label.set_alignment(0, 1.0)

            right_box.pack_start(desc_label, True, True)

        notebook.insert_page(scrolled, gtk.Label(_('Credits')))
        self.show_all()

# vim: expandtab:sw=4:ts=4

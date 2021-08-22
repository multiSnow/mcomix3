# -*- coding: utf-8 -*-
'''about_dialog.py - About dialog.'''

from gi.repository import Gtk
import webbrowser

from mcomix import constants
from mcomix import strings
from mcomix import image_tools
from mcomix import tools

# Some linux distribution patched the constants.APPNAME but some not.
# So, hard-code program name here for About dialog.

FORK_NAME = 'MComix3'
PROG_NAME = 'MComix'
Y_START   = 2006
Y_CURRENT = 2021
LICENSE   = Gtk.License.GPL_2_0

FORK_URI  = 'https://github.com/multiSnow/mcomix3#readme'
PROG_URI  = 'https://sourceforge.net/p/mcomix/wiki/'

COMMENT   = _(
    '{fork_name} is an image and comic book viewer.\n'
    'It reads image files as well as ZIP and TAR archives.\n'
    '{fork_name} is a fork of {prog_name}.\n({prog_uri})').format(
        fork_name=FORK_NAME, prog_name=PROG_NAME, prog_uri=PROG_URI)

class _AboutDialog(Gtk.AboutDialog):

    def __init__(self, window):
        super(_AboutDialog, self).__init__()
        self.set_transient_for(window)

        self.set_logo(image_tools.load_pixbuf_data(
            tools.read_binary('images', 'mcomix.png')))
        self.set_name(FORK_NAME)
        self.set_program_name(FORK_NAME)
        self.set_version(constants.VERSION)

        self.set_comments(COMMENT)
        self.set_website(FORK_URI)

        self.set_copyright(f'Copyright © {Y_START}-{Y_CURRENT}')
        self.set_license_type(LICENSE)

        self.set_authors([f'{name}: {desc}' for name, desc in strings.AUTHORS])
        self.set_translator_credits(
            '\n'.join(f'{name}: {desc}' for name, desc in strings.TRANSLATORS))
        self.set_artists([f'{name}: {desc}' for name, desc in strings.ARTISTS])

        self.show_all()

    def do_activate_link(self, uri):
        webbrowser.open(uri)
        return True

# vim: expandtab:sw=4:ts=4

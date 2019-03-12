# -*- coding: utf-8 -*-
'''about_dialog.py - About dialog.'''

from gi.repository import Gtk
import webbrowser

from mcomix import constants
from mcomix import strings
from mcomix import image_tools
from mcomix import tools

class _AboutDialog(Gtk.AboutDialog):

    def __init__(self, window):
        super(_AboutDialog, self).__init__()
        self.set_transient_for(window)

        self.set_name(constants.APPNAME)
        self.set_program_name(constants.APPNAME)
        self.set_version(constants.VERSION)
        self.set_website('https://sourceforge.net/p/mcomix/wiki/')
        self.set_copyright('Copyright © 2005-2016')

        icon_data = tools.read_binary('images', 'mcomix.png')
        pixbuf = image_tools.load_pixbuf_data(icon_data)
        self.set_logo(pixbuf)

        comment = \
            _('%s is an image viewer specifically designed to handle comic books.') % \
            constants.APPNAME + ' ' + \
            _('It reads ZIP, RAR and tar archives, as well as plain image files.')
        self.set_comments(comment)

        license = \
            _('%s is licensed under the terms of the GNU General Public License.') % constants.APPNAME + \
            ' ' + \
            _('A copy of this license can be obtained from %s') % \
            'http://www.gnu.org/licenses/gpl-2.0.html'
        self.set_wrap_license(True)
        self.set_license(license)

        authors = [ '%s: %s' % (name, description) for name, description in strings.AUTHORS ]
        self.set_authors(authors)

        translators = [ '%s: %s' % (name, description) for name, description in strings.TRANSLATORS ]
        self.set_translator_credits('\n'.join(translators))

        artists = [ '%s: %s' % (name, description) for name, description in strings.ARTISTS ]
        self.set_artists(artists)

        self.connect('activate-link', self._on_activate_link)

        self.show_all()

    def _on_activate_link(self, about_dialog, uri):
        webbrowser.open(uri)
        return True

# vim: expandtab:sw=4:ts=4

# -*- coding: utf-8 -*-
"""about_dialog.py - About dialog."""

import gtk
import constants
import strings
import pkg_resources
import image_tools

class _AboutDialog(gtk.AboutDialog):

    def __init__(self, window):
        gtk.AboutDialog.__init__(self)

        self.set_name(constants.APPNAME)
        self.set_program_name(constants.APPNAME)
        self.set_version(constants.VERSION)
        self.set_website('http://mcomix.sourceforge.net')
        self.set_copyright('Copyright © 2005-2011')

        icon_data = pkg_resources.resource_string('mcomix.images', 'mcomix.png')
        pixbuf = image_tools.load_pixbuf_data(icon_data)
        self.set_logo(pixbuf)

        comment = \
            _('%s is an image viewer specifically designed to handle comic books.') % \
            constants.APPNAME + u' ' + \
            _('It reads ZIP, RAR and tar archives, as well as plain image files.')
        self.set_comments(comment)

        license = \
            _('%s is licensed under the terms of the GNU General Public License.') % constants.APPNAME + \
            ' ' + \
            _('A copy of this license can be obtained from %s') % \
            'http://www.gnu.org/licenses/gpl-2.0.html'
        self.set_wrap_license(True)
        self.set_license(license)

        authors = [ u'%s: %s' % (name, description) for name, description in strings.AUTHORS ]
        self.set_authors(authors)

        translators = [ u'%s: %s' % (name, description) for name, description in strings.TRANSLATORS ]
        self.set_translator_credits("\n".join(translators))

        artists = [ u'%s: %s' % (name, description) for name, description in strings.ARTISTS ]
        self.set_artists(artists)

        self.show_all()

# vim: expandtab:sw=4:ts=4

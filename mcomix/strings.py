# -*- coding: utf-8 -*-
""" strings.py - Constant strings that need internationalization.
    This file should only be imported after gettext has been correctly initialized
    and installed in the global namespace. """

from mcomix.constants import ZIP, TAR, GZIP, BZIP2, RAR, SEVENZIP, LHA

ARCHIVE_DESCRIPTIONS = {
                        ZIP:   _('ZIP archive'),
                        TAR:   _('Tar archive'),
                        GZIP:  _('Gzip compressed tar archive'),
                        BZIP2: _('Bzip2 compressed tar archive'),
                        RAR:   _('RAR archive'),
                        SEVENZIP: _('7z archive'),
                        LHA: _('LHA archive')
                       }

AUTHORS = (
            ('Pontus Ekberg', _('Original vision/developer of Comix')),
            ('Louis Casillas', _('MComix developer')),
            ('Moritz Brunner', _('MComix developer'))
          )
TRANSLATORS = (
            ('Emfox Zhou', _('Simplified Chinese translation')),
            ('Xie Yanbo', _('Simplified Chinese translation')),
            ('Manuel Quiñones', _('Spanish translation')),
            ('Marcelo Góes', _('Brazilian Portuguese translation')),
            ('Christoph Wolk', _('German translation and Nautilus thumbnailer')),
            ('Chris Leick', _('German translation')),
            ('Raimondo Giammanco', _('Italian translation')),
            ('Giovanni Scafora', _('Italian translation')),
            ('GhePeU', _('Italian translation')),
            ('Arthur Nieuwland', _('Dutch translation')),
            ('Achraf Cherti', _('French translation')),
            ('Benoît H.', _('French translation')),
            ('Joseph M. Sleiman', _('French translation')),
            ('Frédéric Chateaux', _('French translation')),
            ('Kamil Leduchowski', _('Polish translatin')),
            ('Darek Jakoniuk', _('Polish translation')),
            ('Paul Chatzidimitriou', _('Greek translation')),
            ('Carles Escrig Royo', _('Catalan translation')),
            ('Hsin-Lin Cheng', _('Traditional Chinese translation')),
            ('Wayne Su', _('Traditional Chinese translation')),
            ('Mamoru Tasaka', _('Japanese translation')),
            ('Keita Haga', _('Japanese translation')),
            ('Toshiharu Kudoh', _('Japanese translation')),
            ('Ernő Drabik', _('Hungarian translation')),
            ('Artyom Smirnov', _('Russian translation')),
            ('Евгений Лежнин', _('Russian translation')),
            ('Adrian C.', _('Croatian translation')),
            ('김민기', _('Korean translation')),
            ('Maryam Sanaat', _('Persian translation')),
            ('Andhika Padmawan', _('Indonesian translation')),
            ('Jan Nekvasil', _('Czech translation')),
            ('Олександр Заяц', _('Ukrainian translation')),
            ('Roxerio Roxo Carrillo', _('Galician translation')),
            ('Martin Karlsson', _('Swedish translation'))
          )
ARTISTS = (
            ('Victor Castillejo', _('Icon design')),
          )

# vim: expandtab:sw=4:ts=4

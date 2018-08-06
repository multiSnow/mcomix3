# -*- coding: utf-8 -*-
""" strings.py - Constant strings that need internationalization.
    This file should only be imported after gettext has been correctly initialized
    and installed in the global namespace. """

from mcomix.constants import ZIP, RAR, TAR, GZIP, BZIP2, XZ, PDF, SEVENZIP, LHA, ZIP_EXTERNAL

ARCHIVE_DESCRIPTIONS = {
                        ZIP         : _('ZIP archive'),
                        RAR         : _('RAR archive'),
                        TAR         : _('Tar archive'),
                        GZIP        : _('Gzip compressed tar archive'),
                        BZIP2       : _('Bzip2 compressed tar archive'),
                        XZ          : _('XZ compressed tar archive'),
                        PDF         : _('PDF document'),
                        SEVENZIP    : _('7z archive'),
                        LHA         : _('LHA archive'),
                        ZIP_EXTERNAL: _('ZIP archive'),
                       }

AUTHORS = (
            (u'Ark', _('MComix developer')),
            (u'Benoit Pierre', _('MComix developer')),
            (u'Louis Casillas', _('MComix developer')),
            (u'Moritz Brunner', _('MComix developer')),
            (u'Pontus Ekberg', _('Original vision/developer of Comix'))
          )
          
TRANSLATORS = (
            (u'Achraf Cherti', _('French translation')),
            (u'Adrian C.', _('Croatian translation')),
            (u'Andhika Padmawan', _('Indonesian translation')),
            (u'Arthur Nieuwland', _('Dutch translation')),
            (u'Artyom Smirnov', _('Russian translation')),
            (u'Benoît H.', _('French translation')),
            (u'Carles Escrig Royo', _('Catalan translation')),
            (u'Carlos Feliu', _('Spanish translation')),
            (u'Chris Leick', _('German translation')),
            (u'Christoph Wolk', _('German translation and Nautilus thumbnailer')),
            (u'Darek Jakoniuk', _('Polish translation')),
            (u'Emfox Zhou', _('Simplified Chinese translation')),
            (u'Ernő Drabik', _('Hungarian translation')),
            (u'Frédéric Chateaux', _('French translation')),
            (u'GhePeU', _('Italian translation')),
            (u'Giovanni Scafora', _('Italian translation')),
            (u'Gyeongmin Bak', _('Korean translation')),
            (u'Hsin-Lin Cheng', _('Traditional Chinese translation')),
            (u'Isratine Citizen', _('Hebrew translation')),
            (u'Jan Nekvasil', _('Czech translation')),
            (u'Jonatan Nyberg', _('Swedish translation')),
            (u'Joseph M. Sleiman', _('French translation')),
            (u'Kamil Leduchowski', _('Polish translatin')),
            (u'Keita Haga', _('Japanese translation')),
            (u'김민기', _('Korean translation')),
            (u'Mamoru Tasaka', _('Japanese translation')),
            (u'Manuel Quiñones', _('Spanish translation')),
            (u'Marcelo Góes', _('Brazilian Portuguese translation')),
            (u'Martin Karlsson', _('Swedish translation')),
            (u'Maryam Sanaat', _('Persian translation')),
            (u'Minho Jeung', _('Korean translation')),
            (u'Paul Chatzidimitriou', _('Greek translation')),
            (u'Raimondo Giammanco', _('Italian translation')),
            (u'Roxerio Roxo Carrillo', _('Galician translation')),
            (u'Toshiharu Kudoh', _('Japanese translation')),
            (u'Wayne Su', _('Traditional Chinese translation')),
            (u'Xie Yanbo', _('Simplified Chinese translation')),
            (u'Zach Cheung', _('Simplified Chinese translation')),
            (u'Zygi Mantus', _('Lithuanian translation')),
            (u'Евгений Лежнин', _('Russian translation')),
            (u'Олександр Заяц', _('Ukrainian translation'))
          )
          
ARTISTS = (
            (u'Victor Castillejo', _('Icon design')),
          )

# vim: expandtab:sw=4:ts=4

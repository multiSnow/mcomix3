#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import sys
import os
import glob
import setuptools

setuptools.setup(
    name='MComix',
    version='0.90.3',
    packages = ['mcomix', 'mcomix.archive'],
    package_data = { 'mcomix.messages' : ['*.mo'], 'mcomix.images' : ['*.png'] },
    entry_points = { 'gui_scripts': [ 'mcomix = mcomix.mcomix:run' ] },
    requires = ['pygtk (>=2.12.0)', 'PIL (>=1.15)'],

    # Package metadata
    maintainer = 'Oddegamra',
    maintainer_email = 'oddegamra@gmx.org',
    url = 'http://www.sourceforge.net/projects/mcomix',
    description = 'MComix is a fork of Comix and is a user-friendly, customizable image viewer. '
        'It is specifically designed to handle comic books.',
    platforms = ['GNU/Linux', 'Win32']
)


# vim: expandtab:sw=4:ts=4

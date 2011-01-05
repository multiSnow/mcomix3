#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import sys
import os
import glob
import setuptools

def get_data_patterns(directory, *patterns):
    """ Build a list of patterns for all subdirectories of <directory>
    to be passed into package_data. """

    olddir = os.getcwd()
    os.chdir(directory)
    allfiles = []
    for dirpath, subdirs, files in os.walk("."):
        for pattern in patterns:
            current_pattern = os.path.normpath(os.path.join(dirpath, pattern))
            if glob.glob(current_pattern):
                # Forward slashes only for distutils. 
                allfiles.append(current_pattern.replace('\\', '/'))
    os.chdir(olddir)
    return allfiles

setuptools.setup(
    name='MComix',
    version='0.90.3',
    packages = ['mcomix', 'mcomix.archive', 'mcomix.messages', 'mcomix.images'],
    package_data = {
        'mcomix.messages' : get_data_patterns('mcomix/messages', '*.mo'),
        'mcomix.images' : get_data_patterns('mcomix/images', '*.png') },
    entry_points = { 
        'gui_scripts' : [ 'mcomix-gui = mcomix.mcomixstarter:run' ],
        'console_scripts' : [ 'mcomix = mcomix.mcomixstarter:run' ] },
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

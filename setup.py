#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import sys
import os
import glob
import setuptools

from mcomix import constants

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
    name = constants.APPNAME.lower(),
    version = constants.VERSION,
    packages = ['mcomix', 'mcomix.archive', 'mcomix.messages', 'mcomix.images'],
    package_data = {
        'mcomix.messages' : get_data_patterns('mcomix/messages', '*.mo', '*.po'),
        'mcomix.images' : get_data_patterns('mcomix/images', '*.png') },
    entry_points = { 
        'console_scripts' : [ 'mcomix = mcomix.mcomixstarter:run' ] },
    requires = ['pygtk (>=2.12.0)', 'PIL (>=1.15)'],
    install_requires = ['setuptools'],
    zip_safe = False,
    
    # Various MIME files that need to be copied to certain system locations on Linux.
    # Note that these files are only installed correctly if
    # --single-version-externally-managed is used as argument to "setup.py install".
    # Otherwise, these files ends up in an MComix egg directory in site-packages.
    # (Thank you, setuptools!)
    data_files = [
        ('share/man/man1', ['mcomix.1.gz', 'mime/comicthumb.1.gz']),
        ('share/applications', ['mime/mcomix.desktop']),
        ('share/mime/packages', ['mime/mcomix.xml']),
        ('share/icons/hicolor/16x16/apps', ['mcomix/images/16x16/mcomix.png']),
        ('share/icons/hicolor/22x22/apps', ['mcomix/images/22x22/mcomix.png']),
        ('share/icons/hicolor/24x24/apps', ['mcomix/images/24x24/mcomix.png']),
        ('share/icons/hicolor/32x32/apps', ['mcomix/images/32x32/mcomix.png']),
        ('share/icons/hicolor/48x48/apps', ['mcomix/images/48x48/mcomix.png']),
        ('share/icons/hicolor/16x16/mimetypes', 
            ['mime/icons/16x16/application-x-cbz.png', 
             'mime/icons/16x16/application-x-cbr.png',
             'mime/icons/16x16/application-x-cbt.png']),
        ('share/icons/hicolor/22x22/mimetypes', 
            ['mime/icons/22x22/application-x-cbz.png', 
             'mime/icons/22x22/application-x-cbr.png',
             'mime/icons/22x22/application-x-cbt.png']),
        ('share/icons/hicolor/24x24/mimetypes', 
            ['mime/icons/24x24/application-x-cbz.png', 
             'mime/icons/24x24/application-x-cbr.png',
             'mime/icons/24x24/application-x-cbt.png']),
        ('share/icons/hicolor/32x32/mimetypes', 
            ['mime/icons/32x32/application-x-cbz.png', 
             'mime/icons/32x32/application-x-cbr.png',
             'mime/icons/32x32/application-x-cbt.png']),
        ('share/icons/hicolor/48x48/mimetypes', 
            ['mime/icons/48x48/application-x-cbz.png', 
             'mime/icons/48x48/application-x-cbr.png',
             'mime/icons/48x48/application-x-cbt.png'])],

    # Package metadata
    maintainer = 'Oddegamra',
    maintainer_email = 'oddegamra@gmx.org',
    url = 'http://www.sourceforge.net/projects/mcomix',
    description = 'MComix is a fork of Comix and is a user-friendly, customizable image viewer. '
        'It is specifically designed to handle comic books.',
    platforms = ['GNU/Linux', 'Win32']
)

# vim: expandtab:sw=4:ts=4

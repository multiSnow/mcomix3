#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" MComix installation routines.

Example usage:
    Normal installation (all files are copied into a directory in python/lib/site-packages/mcomix)
    $ ./setup.py install

    For distribution packaging (All files are installed relative to /tmp/mcomix)
    $ ./setup.py install --single-version-externally-managed --root /tmp/mcomix --prefix /usr
"""

import sys
import os
import glob
import setuptools

try:
    import py2exe
except ImportError:
    pass

from mcomix import constants

def get_data_patterns(directory, *patterns):
    """ Build a list of patterns for all subdirectories of <directory>
    to be passed into package_data. """

    olddir = os.getcwd()
    os.chdir(os.path.join(constants.BASE_PATH, directory))
    allfiles = []
    for dirpath, subdirs, files in os.walk("."):
        for pattern in patterns:
            current_pattern = os.path.normpath(os.path.join(dirpath, pattern))
            if glob.glob(current_pattern):
                # Forward slashes only for distutils.
                allfiles.append(current_pattern.replace('\\', '/'))
    os.chdir(olddir)
    return allfiles

# Filter unnecessary image files. Replace wildcard pattern with actual files.
images = get_data_patterns('mcomix/images', '*.png')
images.remove('*.png')
images.extend([ os.path.basename(img)
    for img in glob.glob(os.path.join(constants.BASE_PATH, 'mcomix/images', '*.png'))
    if os.path.basename(img) not in
        ('mcomix-large.png', )])

setuptools.setup(
    name = constants.APPNAME.lower(),
    version = constants.VERSION,
    packages = ['mcomix', 'mcomix.archive', 'mcomix.library',
        'mcomix.messages', 'mcomix.images'],
    package_data = {
        'mcomix.messages' : get_data_patterns('mcomix/messages', '*.mo'),
        'mcomix.images' : images },
    entry_points = {
        'console_scripts' : [ 'mcomix = mcomix.run:run' ] },
    test_suite = "test",
    requires = ['pygtk (>=2.12.0)', 'PIL (>=1.15)'],
    install_requires = ['setuptools'],
    zip_safe = False,

    # Various MIME files that need to be copied to certain system locations on Linux.
    # Note that these files are only installed correctly if
    # --single-version-externally-managed is used as argument to "setup.py install".
    # Otherwise, these files end up in a MComix egg directory in site-packages.
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
    url = 'http://mcomix.sourceforge.net',
    description = 'GTK comic book viewer',
    long_description = 'MComix is a fork of Comix and is a user-friendly, customizable image viewer. '
        'It is specifically designed to handle comic books.',
    license = "License :: OSI Approved :: GNU General Public License (GPL)",
    download_url = "http://sourceforge.net/projects/mcomix/files",
    platforms = ['Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: BSD'],

    # Py2Exe options
    windows = [{ 'script' : 'win32/mcomix_py2exe.py',
        'icon_resources' : [(1, "mcomix/images/mcomix.ico")]  }],
    options = {
        'py2exe' : {
            'packages' : 'mcomix.messages, mcomix.images, encodings',
            'includes' : 'cairo, pango, pangocairo, atk, gobject, gio, gtk.keysyms',
            'dist_dir' : 'dist_py2exe',
            'excludes' : ['_ssl', 'pyreadline', 'difflib', 'doctest', 
                'calendar', 'pdb', 'unittest', 'inspect']
        }
    }
)

# vim: expandtab:sw=4:ts=4

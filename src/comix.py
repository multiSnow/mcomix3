#!/usr/bin/env python

"""Comix - GTK Comic Book Viewer

Copyright (C) 2005-2009 Pontus Ekberg
<herrekberg@users.sourceforge.net>
"""

# -------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# -------------------------------------------------------------------------

import os
import sys
import gettext
import getopt

#Check for PyGTK and PIL dependencies.
try:
    import pygtk
    pygtk.require('2.0')
    import gtk
    assert gtk.gtk_version >= (2, 12, 0)
    assert gtk.pygtk_version >= (2, 12, 0)
    import gobject
    gobject.threads_init()
except AssertionError:
    print "You don't have the required versions of GTK+ and/or PyGTK",
    print 'installed.'
    print 'Installed GTK+ version is: %s' % (
        '.'.join([str(n) for n in gtk.gtk_version]))
    print 'Required GTK+ version is: 2.12.0 or higher\n'
    print 'Installed PyGTK version is: %s' % (
        '.'.join([str(n) for n in gtk.pygtk_version]))
    print 'Required PyGTK version is: 2.12.0 or higher'
    sys.exit(1)
except ImportError:
    print 'PyGTK version 2.12.0 or higher is required to run Comix.'
    print 'No version of PyGTK was found on your system.'
    sys.exit(1)

try:
    import Image
    assert Image.VERSION >= '1.1.5'
except AssertionError:
    print "You don't have the required version of the Python Imaging",
    print 'Library (PIL) installed.'
    print 'Installed PIL version is: %s' % Image.VERSION
    print 'Required PIL version is: 1.1.5 or higher'
    sys.exit(1)
except ImportError:
    print 'Python Imaging Library (PIL) 1.1.5 or higher is required.'
    print 'No version of the Python Imaging Library was found on your',
    print 'system.'
    sys.exit(1)

import constants
import deprecated
import filehandler
import locale
import main
import icons
import preferences


def print_help():
    """Print the command-line help text and exit."""
    print 'Usage:'
    print '  comix [OPTION...] [PATH]'
    print '\nView images and comic book archives.\n'
    print 'Options:'
    print '  -h, --help              Show this help and exit.'
    print '  -f, --fullscreen        Start the application in fullscreen mode.'
    print '  -l, --library           Show the library on startup.'
    sys.exit(1)


def run():
    """Run the program."""
    # Use gettext translations as found in the source dir, otherwise based on
    # the install path.
    exec_path = os.path.abspath(sys.argv[0])
    base_dir = os.path.dirname(os.path.dirname(exec_path))
    if os.path.isdir(os.path.join(base_dir, 'messages')):
        gettext.install('comix', os.path.join(base_dir, 'messages'),
            unicode=True)
    else:
        gettext.install('comix', os.path.join(base_dir, 'share/locale'),
            unicode=True)

    fullscreen = False
    show_library = False
    open_path = None
    open_page = 1
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'fhl',
            ['fullscreen', 'help', 'library'])
    except getopt.GetoptError:
        print_help()
    for opt, value in opts:
        if opt in ('-h', '--help'):
            print_help()
        elif opt in ('-f', '--fullscreen'):
            fullscreen = True
        elif opt in ('-l', '--library'):
            show_library = True

    if not os.path.exists(constants.DATA_DIR):
        os.makedirs(constants.DATA_DIR, 0700)
    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0700)
    deprecated.move_files_to_xdg_dirs()
    preferences.read_preferences_file()
    icons.load_icons()
    
    if len(args) >= 1:
        param_path = os.path.abspath(args[0])
        if os.path.isdir(param_path):
            dir_files = os.listdir(param_path)
            dir_files.sort(locale.strcoll)
            for filename in dir_files:
                full_path = os.path.join(param_path, filename)
                if filehandler.is_image_file(full_path):
                    open_path = full_path
                    break
        else:
            open_path = param_path
    elif preferences.prefs['auto load last file']:
        open_path = preferences.prefs['path to last file']
        open_page = preferences.prefs['page of last file']
    
    window = main.MainWindow(fullscreen=fullscreen, show_library=show_library,
        open_path=open_path, open_page=open_page)
    deprecated.check_for_deprecated_files(window)
    try:
        gtk.main()
    except KeyboardInterrupt: # Will not always work because of threading.
        window.terminate_program()


if __name__ == '__main__':
    run()

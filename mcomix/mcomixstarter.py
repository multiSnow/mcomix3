#!/usr/bin/env python

"""MComix - GTK Comic Book Viewer
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
import getopt
import signal
import gettext

import constants
import tools
import portability

def wait_and_exit():
    """ Wait for the user pressing ENTER before closing. This should help
    the user find possibly missing dependencies when starting, since the
    Python window will not close down immediately after the error. """

    if sys.platform == 'win32' and not sys.stdin.closed and not sys.stdout.closed:
        print
        raw_input("Press ENTER to continue...")

    sys.exit(1)

try:
    import pkg_resources

except ImportError:
    # gettext isn't initialized yet, since pkg_resources is required to find translation files.
    # Thus, localizing these messages is pointless.
    print "The package 'pkg_resources' could not be found."
    print "You need to install the 'setuptools' package, which also includes pkg_resources."
    print "Note: On most distributions, 'distribute' supersedes 'setuptools'."
    wait_and_exit()

def install_gettext():
    """ Initialize gettext with the correct directory that contains
    MComix translations. This has to be done before any calls to gettext.gettext
    have been made to ensure all strings are actually translated. """

    # Add the sources' base directory to PATH to allow development without
    # explicitly installing the package.
    sys.path.append(constants.BASE_PATH)

    # Get the user's current locale
    code = portability.get_default_locale()
    domain = constants.APPNAME.lower()
    lang_identifiers = gettext._expand_lang(code)

    # Search for .mo files manually, since gettext doesn't support setuptools/pkg_resources.
    for lang in lang_identifiers:
        resource = os.path.join(lang, 'LC_MESSAGES', '%s.mo' % domain)
        if pkg_resources.resource_exists('mcomix.messages', resource):
            translation = gettext.GNUTranslations(pkg_resources.resource_stream('mcomix.messages', resource))
            translation.install(unicode=True)
            return

    # If nothing was found yet, install an empty translation object.
    translation = gettext.NullTranslations()
    translation.install(unicode=True)

def install_print_function():
    """ Add tools.print_ to the built-in namespace as print_.
    This function helps with encoding woes that the print statement has
    by replacing problematic characters with underscore. """

    import __builtin__
    if 'print_' not in __builtin__.__dict__:
        __builtin__.__dict__['print_'] = tools.print_

install_gettext()
install_print_function()

def print_help():
    """Print the command-line help text and exit."""
    print_( _('Usage:') )
    print_( '  mcomix',  _('[OPTION...] [PATH]') )
    print_( _('\nView images and comic book archives.\n') )
    print_( _('Options:') )
    print_( _('  -h, --help              Show this help and exit.') )
    print_( _('  -f, --fullscreen        Start the application in fullscreen mode.') )
    print_( _('  -s, --slideshow         Start the application in slideshow mode.') )
    print_( _('  -l, --library           Show the library on startup.') )
    print_( _('  -m, --manga             Start the application in manga mode.') )
    print_( _('  -d, --double-page       Start the application in double page mode.') )
    print_( _('  -B, --zoom-best         Start the application with zoom set to best fit mode.') )
    print_( _('  -W, --zoom-width        Start the application with zoom set to fit width.') )
    print_( _('  -H, --zoom-height       Start the application with zoom set to fit height.') )
    print_( _('  -v, --version           Show the version number and exit.') )

    sys.exit(1)

def print_version():
    """Print the version number and exit."""
    print_(constants.APPNAME + ' ' + constants.VERSION)

    sys.exit(1)

# Check for PyGTK and PIL dependencies.
try:
    import pygtk
    pygtk.require('2.0')

    import gtk
    assert gtk.gtk_version >= (2, 12, 0)
    assert gtk.pygtk_version >= (2, 12, 0)

    import gobject
    gobject.threads_init()

except AssertionError:
    print_( _("You do not have the required versions of GTK+ and PyGTK installed.") )
    print_( _('Installed GTK+ version is: %s') % \
        '.'.join([str(n) for n in gtk.gtk_version]) )
    print_( _('Required GTK+ version is: 2.12.0 or higher\n') )
    print_( _('Installed PyGTK version is: %s') % \
        '.'.join([str(n) for n in gtk.pygtk_version]) )
    print_( _('Required PyGTK version is: 2.12.0 or higher') )
    wait_and_exit()

except ImportError:
    print_( _('Required PyGTK version is: 2.12.0 or higher') )
    print_( _('No version of PyGTK was found on your system.') )
    print_( _('This error might be caused by missing GTK+ libraries.') )
    wait_and_exit()

# Check PIL library
try:
    import Image
    assert Image.VERSION >= '1.1.5'

except AssertionError:
    print_( _("You don't have the required version of the Python Imaging"), end=' ')
    print_( _('Library (PIL) installed.') )
    print_( _('Installed PIL version is: %s') % Image.VERSION )
    print_( _('Required PIL version is: 1.1.5 or higher') )
    wait_and_exit()

except ImportError:
    print_( _('Python Imaging Library (PIL) 1.1.5 or higher is required.') )
    print_( _('No version of the Python Imaging Library was found on your system.') )
    wait_and_exit()

# Import required mcomix modules for this script.
# This should be done only after install_gettext() has been called.
import deprecated
import main
import icons
import preferences

def run():
    """Run the program."""

    fullscreen = False
    slideshow = False
    show_library = False
    manga_mode = False
    double_page = False
    zoom_mode = None
    open_path = None
    open_page = 1

    try:
        argv = portability.get_commandline_args()
        opts, args = getopt.gnu_getopt(argv[1:], 'fsmdBWHhlv',
            ['fullscreen', 'slideshow', 'manga', 'doublepage', 'zoom-best',
            'zoom-width', 'zoom-height', 'help', 'library', 'version'])

    except getopt.GetoptError:
        print_help()

    for opt, value in opts:

        if opt in ('-h', '--help'):
            print_help()

        elif opt in ('-v', '--version'):
            print_version()

        elif opt in ('-l', '--library'):
            show_library = True

        elif opt in ('-f', '--fullscreen'):
            fullscreen = True

        elif opt in ('-s', '--slideshow'):
            slideshow = True

        elif opt in ('-m', '--manga'):
            manga_mode = True

        elif opt in ('-d', '--double-page'):
            double_page = True

        elif opt in ('-B', '--zoom-best'):
            zoom_mode = constants.ZOOM_MODE_BEST

        elif opt in ('-W', '--zoom-width'):
            zoom_mode = constants.ZOOM_MODE_WIDTH

        elif opt in ('-H', '--zoom-height'):
            zoom_mode = constants.ZOOM_MODE_HEIGHT

    if not os.path.exists(constants.DATA_DIR):
        os.makedirs(constants.DATA_DIR, 0700)

    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0700)

    deprecated.move_files_to_xdg_dirs()
    preferences.read_preferences_file()
    icons.load_icons()

    if len(args) == 1:
        open_path = args[0]
    elif len(args) > 1:
        open_path = args

    elif preferences.prefs['auto load last file']:
        open_path = preferences.prefs['path to last file']
        open_page = preferences.prefs['page of last file']

    window = main.MainWindow(fullscreen = fullscreen, is_slideshow = slideshow,
            show_library = show_library, manga_mode = manga_mode,
            double_page = double_page, zoom_mode = zoom_mode,
            open_path = open_path, open_page = open_page)
    deprecated.check_for_deprecated_files(window)

    signal.signal(signal.SIGTERM, lambda: gobject.idle_add(window.terminate_program))
    try:
        gtk.main()
    except KeyboardInterrupt: # Will not always work because of threading.
        window.save_and_terminate_program()

if __name__ == '__main__':
    run()

# vim: expandtab:sw=4:ts=4

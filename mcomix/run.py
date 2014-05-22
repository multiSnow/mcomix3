
import os
import sys
import optparse
import signal

if __name__ == '__main__':
    print >> sys.stderr, 'PROGRAM TERMINATED'
    print >> sys.stderr, 'Please do not run this script directly! Use mcomixstarter.py instead.'
    sys.exit(1)

# These modules must not depend on GTK, pkg_resources, PIL,
# or any other optional libraries.
from mcomix import constants
from mcomix import portability
from mcomix import preferences

def wait_and_exit():
    """ Wait for the user pressing ENTER before closing. This should help
    the user find possibly missing dependencies when starting, since the
    Python window will not close down immediately after the error. """

    if sys.platform == 'win32' and not sys.stdin.closed and not sys.stdout.closed:
        print
        raw_input("Press ENTER to continue...")

    sys.exit(1)


def print_version(opt, value, parser, *args, **kwargs):
    """Print the version number and exit."""
    print_(constants.APPNAME + ' ' + constants.VERSION)
    sys.exit(0)

def parse_arguments(argv):
    """ Parse the command line passed in <argv>. Returns a tuple containing
    (options, arguments). Errors parsing the command line are handled in
    this function. """

    parser = optparse.OptionParser(
            usage="%%prog %s" % _('[OPTION...] [PATH]'),
            description=_('View images and comic book archives.'),
            add_help_option=False)
    parser.add_option('--help', action='help',
            help=_('Show this help and exit.'))
    parser.add_option('-s', '--slideshow', dest='slideshow', action='store_true',
            help=_('Start the application in slideshow mode.'))
    parser.add_option('-l', '--library', dest='library', action='store_true',
            help=_('Show the library on startup.'))
    parser.add_option('-v', '--version', action='callback', callback=print_version,
            help=_('Show the version number and exit.'))

    viewmodes = optparse.OptionGroup(parser, _('View modes'))
    viewmodes.add_option('-f', '--fullscreen', dest='fullscreen', action='store_true',
            help=_('Start the application in fullscreen mode.'))
    viewmodes.add_option('-m', '--manga', dest='manga', action='store_true',
            help=_('Start the application in manga mode.'))
    viewmodes.add_option('-d', '--double-page', dest='doublepage', action='store_true',
            help=_('Start the application in double page mode.'))
    parser.add_option_group(viewmodes)

    fitmodes = optparse.OptionGroup(parser, _('Zoom modes'))
    fitmodes.add_option('-b', '--zoom-best', dest='zoommode', action='store_const',
            const=constants.ZOOM_MODE_BEST,
            help=_('Start the application with zoom set to best fit mode.'))
    fitmodes.add_option('-w', '--zoom-width', dest='zoommode', action='store_const',
            const=constants.ZOOM_MODE_WIDTH,
            help=_('Start the application with zoom set to fit width.'))
    fitmodes.add_option('-h', '--zoom-height', dest='zoommode', action='store_const',
            const=constants.ZOOM_MODE_HEIGHT,
            help=_('Start the application with zoom set to fit height.'))
    parser.add_option_group(fitmodes)

    debugopts = optparse.OptionGroup(parser, _('Debug options'))
    debugopts.add_option('-W', dest='loglevel', action='store',
            choices=('all', 'warn', 'error'), default='warn',
            metavar='[ all | warn | error ]',
            help=_('Sets the desired output log level.'))
    # This supresses an error when MComix is used with cProfile
    debugopts.add_option('-o', dest='output', action='store',
            default='', help=optparse.SUPPRESS_HELP)
    parser.add_option_group(debugopts)

    opts, args = parser.parse_args(argv)

    # Fix up log level to use constants from log.
    if opts.loglevel == 'all':
        opts.loglevel = log.DEBUG
    elif opts.loglevel == 'warn':
        opts.loglevel = log.WARNING
    elif opts.loglevel == 'error':
        opts.loglevel = log.ERROR

    return opts, args

try:
    import pkg_resources

except ImportError:
    # gettext isn't initialized yet, since pkg_resources is required to find translation files.
    # Thus, localizing these messages is pointless.
    print "The package 'pkg_resources' could not be found."
    print "You need to install the 'setuptools' package, which also includes pkg_resources."
    print "Note: On most distributions, 'distribute' supersedes 'setuptools'."
    wait_and_exit()

preferences.read_preferences_file()

from mcomix import i18n
i18n.install_gettext()

from mcomix.log import print_

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
    import PIL.Image
    assert PIL.Image.VERSION >= '1.1.5'

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
from mcomix import main
from mcomix import icons
from mcomix import log

def run():
    """Run the program."""

    open_path = None
    open_page = 1
    argv = portability.get_commandline_args()
    opts, args = parse_arguments(argv)

    if not os.path.exists(constants.DATA_DIR):
        os.makedirs(constants.DATA_DIR, 0700)

    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0700)

    icons.load_icons()

    if len(args) == 1:
        open_path = args[0]
    elif len(args) > 1:
        open_path = args

    elif preferences.prefs['auto load last file'] \
        and os.path.isfile(preferences.prefs['path to last file']):
        open_path = preferences.prefs['path to last file']
        open_page = preferences.prefs['page of last file']

    log.setLevel(opts.loglevel)

    # Some languages require a RTL layout
    if preferences.prefs['language'] in ('he', 'fa'):
        gtk.widget_set_default_direction(gtk.TEXT_DIR_RTL)

    gtk.gdk.set_program_class('MComix')

    window = main.MainWindow(fullscreen = opts.fullscreen, is_slideshow = opts.slideshow,
            show_library = opts.library, manga_mode = opts.manga,
            double_page = opts.doublepage, zoom_mode = opts.zoommode,
            open_path = open_path, open_page = open_page)
    main.set_main_window(window)

    signal.signal(signal.SIGTERM, lambda: gobject.idle_add(window.terminate_program))
    try:
        gtk.main()
    except KeyboardInterrupt: # Will not always work because of threading.
        window.terminate_program()

# vim: expandtab:sw=4:ts=4

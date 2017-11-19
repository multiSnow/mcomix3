
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
from mcomix import (
    constants,
    log,
    portability,
    preferences,
)

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
    print constants.APPNAME + ' ' + constants.VERSION
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
    if sys.platform == 'win32':
        parser.add_option('--no-update-fontconfig-cache',
                          dest='update_fontconfig_cache',
                          default=True, action='store_false',
                          help=_('Don\'t update fontconfig cache at startup.'))
    else:
        parser.add_option('--update-fontconfig-cache',
                          dest='update_fontconfig_cache',
                          default=False, action='store_true',
                          help=_('Update fontconfig cache at startup.'))

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
            choices=('all', 'debug', 'info', 'warn', 'error'), default='warn',
            metavar='[ all | debug | info | warn | error ]',
            help=_('Sets the desired output log level.'))
    # This supresses an error when MComix is used with cProfile
    debugopts.add_option('-o', dest='output', action='store',
            default='', help=optparse.SUPPRESS_HELP)
    parser.add_option_group(debugopts)

    opts, args = parser.parse_args(argv)

    # Fix up log level to use constants from log.
    if opts.loglevel == 'all':
        opts.loglevel = log.DEBUG
    if opts.loglevel == 'debug':
        opts.loglevel = log.DEBUG
    if opts.loglevel == 'info':
        opts.loglevel = log.INFO
    elif opts.loglevel == 'warn':
        opts.loglevel = log.WARNING
    elif opts.loglevel == 'error':
        opts.loglevel = log.ERROR

    return opts, args

def run():
    """Run the program."""

    try:
        import pkg_resources

    except ImportError:
        # gettext isn't initialized yet, since pkg_resources is required to find translation files.
        # Thus, localizing these messages is pointless.
        log._print("The package 'pkg_resources' could not be found.")
        log._print("You need to install the 'setuptools' package, which also includes pkg_resources.")
        log._print("Note: On most distributions, 'distribute' supersedes 'setuptools'.")
        wait_and_exit()

    # Load configuration and setup localisation.
    preferences.read_preferences_file()
    from mcomix import i18n
    i18n.install_gettext()

    # Retrieve and parse command line arguments.
    argv = portability.get_commandline_args()
    opts, args = parse_arguments(argv)

    # First things first: set the log level.
    log.setLevel(opts.loglevel)

    # On Windows, update the fontconfig cache manually, before MComix starts
    # using Gtk, since the process may take several minutes, during which the
    # main window will just be frozen if the work is left to Gtk itself...
    if opts.update_fontconfig_cache:
        # First, update fontconfig cache.
        log.debug('starting fontconfig cache update')
        try:
            from mcomix.win32 import fc_cache
            from mcomix import process
            fc_cache.update()
            log.debug('fontconfig cache updated')
        except Exception as e:
            log.error('during fontconfig cache update', exc_info=e)
        # And then replace current MComix process with a fresh one
        # (that will not try to update the cache again).
        exe = sys.argv[0]
        if sys.platform == 'win32' and exe.endswith('.py'):
            # Find the interpreter.
            exe = process.find_executable(('pythonw.exe', 'python.exe'))
            args = [exe, sys.argv[0]]
        else:
            args = [exe]
        if sys.platform == 'win32':
            args.append('--no-update-fontconfig-cache')
        args.extend(argv)
        if '--update-fontconfig-cache' in args:
            args.remove('--update-fontconfig-cache')
        log.debug('restarting MComix from fresh: os.execv(%s, %s)', repr(exe), args)
        try:
            if sys.platform == 'win32':
                # Of course we can't use os.execv on Windows because it will
                # mangle arguments containing spaces or non-ascii characters...
                process.Win32Popen(args)
                sys.exit(0)
            else:
                os.execv(exe, args)
        except Exception as e:
            log.error('os.execv(%s, %s) failed', exe, str(args), exc_info=e)
        wait_and_exit()

    # Check for PyGTK and PIL dependencies.
    try:
        from gi import require_version

        require_version('PangoCairo', '1.0')
        require_version('Gtk', '3.0')
        require_version('Gdk', '3.0')

        from gi.repository import Gdk, Gtk, GLib
        from gi import version_info as gi_version_info

        if gi_version_info < (3,11,0):
            from gi.repository import GObject
            GObject.threads_init()

    except AssertionError:
        log.error( _("You do not have the required versions of GTK+ 3.0 and PyGObject installed.") )
        wait_and_exit()

    except ImportError:
        log.error( _('No version of GObject was found on your system.') )
        log.error( _('This error might be caused by missing GTK+ libraries.') )
        wait_and_exit()

    try:
        import PIL.Image
        assert PIL.Image.VERSION >= '1.1.5'

    except AssertionError:
        log.error( _("You don't have the required version of the Python Imaging"), end=' ')
        log.error( _('Library (PIL) installed.') )
        log.error( _('Installed PIL version is: %s') % Image.VERSION )
        log.error( _('Required PIL version is: 1.1.5 or higher') )
        wait_and_exit()

    except ImportError:
        log.error( _('Python Imaging Library (PIL) 1.1.5 or higher is required.') )
        log.error( _('No version of the Python Imaging Library was found on your system.') )
        wait_and_exit()

    if not os.path.exists(constants.DATA_DIR):
        os.makedirs(constants.DATA_DIR, 0700)

    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0700)

    from mcomix import icons
    icons.load_icons()

    open_path = None
    open_page = 1
    if len(args) == 1:
        open_path = args[0]
    elif len(args) > 1:
        open_path = args

    elif preferences.prefs['auto load last file'] \
        and preferences.prefs['path to last file'] \
        and os.path.isfile(preferences.prefs['path to last file']):
        open_path = preferences.prefs['path to last file']
        open_page = preferences.prefs['page of last file']

    # Some languages require a RTL layout
    if preferences.prefs['language'] in ('he', 'fa'):
        Gtk.widget_set_default_direction(Gtk.TextDirection.RTL)

    Gdk.set_program_class(constants.APPNAME)

    settings = Gtk.Settings.get_default()
    # Enable icons for menu items.
    settings.props.gtk_menu_images = True

    from mcomix import main
    window = main.MainWindow(fullscreen = opts.fullscreen, is_slideshow = opts.slideshow,
            show_library = opts.library, manga_mode = opts.manga,
            double_page = opts.doublepage, zoom_mode = opts.zoommode,
            open_path = open_path, open_page = open_page)
    main.set_main_window(window)

    if 'win32' != sys.platform:
        # Add a SIGCHLD handler to reap zombie processes.
        def on_sigchld(signum, frame):
            try:
                os.waitpid(-1, os.WNOHANG)
            except OSError:
                pass
        signal.signal(signal.SIGCHLD, on_sigchld)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda signum, stack: GLib.idle_add(window.terminate_program))
    try:
        Gtk.main()
    except KeyboardInterrupt: # Will not always work because of threading.
        window.terminate_program()

# vim: expandtab:sw=4:ts=4

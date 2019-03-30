
import os
import sys
import argparse
import signal

if __name__ == '__main__':
    print('PROGRAM TERMINATED',file=sys.stderr)
    print('Please do not run this script directly! Use mcomixstarter.py instead.',file=sys.stderr)
    sys.exit(1)

# These modules must not depend on GTK, PIL,
# or any other optional libraries.
from mcomix import (
    constants,
    log,
    portability,
    preferences,
)

def wait_and_exit():
    ''' Wait for the user pressing ENTER before closing. This should help
    the user find possibly missing dependencies when starting, since the
    Python window will not close down immediately after the error. '''
    if sys.platform == 'win32' and not sys.stdin.closed and not sys.stdout.closed:
        print()
        input('Press ENTER to continue...')
    sys.exit(1)

def print_version():
    '''Print the version number and exit.'''
    print(constants.APPNAME + ' ' + constants.VERSION)
    sys.exit(0)

def parse_arguments():
    ''' Parse the command line passed in <argv>. Returns a tuple containing
    (options, arguments). Errors parsing the command line are handled in
    this function. '''

    parser = argparse.ArgumentParser(
        usage='%%(prog)s %s' % _('[OPTION...] [PATH...]'),
        description=_('View images and comic book archives.'),
        add_help=False)
    parser.add_argument('--help', action='help',
                        help=_('Show this help and exit.'))
    parser.add_argument('path', type=str, action='store', nargs='*', default='',
                        help=argparse.SUPPRESS)

    parser.add_argument('-s', '--slideshow', dest='slideshow', action='store_true',
                        help=_('Start the application in slideshow mode.'))
    parser.add_argument('-l', '--library', dest='library', action='store_true',
                        help=_('Show the library on startup.'))
    parser.add_argument('-v', '--version', dest='version', action='store_true',
                        help=_('Show the version number and exit.'))

    viewmodes = parser.add_argument_group('View modes')
    viewmodes.add_argument('-f', '--fullscreen', dest='fullscreen', action='store_true',
                           help=_('Start the application in fullscreen mode.'))
    viewmodes.add_argument('-m', '--manga', dest='manga', action='store_true',
                           help=_('Start the application in manga mode.'))
    viewmodes.add_argument('-d', '--double-page', dest='doublepage', action='store_true',
                           help=_('Start the application in double page mode.'))

    fitmodes = parser.add_argument_group('Zoom modes')
    fitmodes.add_argument('-b', '--zoom-best', dest='zoommode', action='store_const',
                          const=constants.ZOOM_MODE_BEST,
                          help=_('Start the application with zoom set to best fit mode.'))
    fitmodes.add_argument('-w', '--zoom-width', dest='zoommode', action='store_const',
                          const=constants.ZOOM_MODE_WIDTH,
                          help=_('Start the application with zoom set to fit width.'))
    fitmodes.add_argument('-h', '--zoom-height', dest='zoommode', action='store_const',
                          const=constants.ZOOM_MODE_HEIGHT,
                          help=_('Start the application with zoom set to fit height.'))

    debugopts = parser.add_argument_group('Debug options')
    debugopts.add_argument('-W', dest='loglevel', action='store',
                           choices=log.levels.keys(), default='warn',
                           metavar='[ {} ]'.format(' | '.join(log.levels.keys())),
                           help=_('Sets the desired output log level.'))
    # This supresses an error when MComix is used with cProfile
    debugopts.add_argument('-o', dest='output', action='store',
                           default='', help=argparse.SUPPRESS)

    args = parser.parse_args()

    return args

def run():
    '''Run the program.'''

    # Load configuration and setup localisation.
    preferences.read_preferences_file()
    from mcomix import i18n
    i18n.install_gettext()

    # Retrieve and parse command line arguments.
    args = parse_arguments()

    if args.version:
        print_version()

    # First things first: set the log level.
    log.setLevel(log.levels[args.loglevel])

    # Check for PyGTK and PIL dependencies.
    try:
        from gi import version_info as gi_version_info
        if gi_version_info < (3,21,0):
            log.error(_('You do not have the required versions of PyGObject installed.'))
            wait_and_exit()

        from gi import require_version

        require_version('PangoCairo', '1.0')
        require_version('Gtk', '3.0')
        require_version('Gdk', '3.0')

        from gi.repository import Gdk, Gtk, GLib

    except ValueError:
        log.error(_('You do not have the required versions of GTK+ 3.0 installed.'))
        wait_and_exit()

    except ImportError:
        log.error(_('No version of GObject was found on your system.'))
        log.error(_('This error might be caused by missing GTK+ libraries.'))
        wait_and_exit()

    try:
        #FIXME
        # check Pillow version carefully here.
        # from 5.1.0 to 5.4.1, PILLOW_VERSION is used,
        # but since 6.0.0, only __version__ should be used.
        # clean up these code once python 3.6 goes EOL (maybe 2021)
        # (https://pillow.readthedocs.io/en/stable/releasenotes/5.2.0.html)
        import PIL.Image
        pilver=getattr(PIL.Image,'__version__',None)
        if not pilver:
            pilver=getattr(PIL.Image,'PILLOW_VERSION')

    except AttributeError:
        log.error(_('You don\'t have the required version of the Pillow installed.'))
        log.error(_('Required Pillow version is: %s or higher') % constants.REQUIRED_PIL_VERSION)
        wait_and_exit()

    except ImportError:
        log.error(_('Pillow %s or higher is required.') % constants.REQUIRED_PIL_VERSION)
        log.error(_('No version of the Pillow was found on your system.'))
        wait_and_exit()

    else:
        if pilver < constants.REQUIRED_PIL_VERSION:
            log.error(_('You don\'t have the required version of the Pillow installed.'))
            log.error(_('Installed PIL version is: %s') % pilver)
            log.error(_('Required Pillow version is: %s or higher') % constants.REQUIRED_PIL_VERSION)
            wait_and_exit()

    if not os.path.exists(constants.DATA_DIR):
        os.makedirs(constants.DATA_DIR, 0o700)

    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0o700)

    from mcomix import icons
    icons.load_icons()

    open_path = args.path or None
    open_page = 1

    if isinstance(open_path, list):
        n = 0
        while n<len(open_path):
            p = os.path.join(constants.STARTDIR, open_path[n])
            p = os.path.normpath(p)
            if not os.path.exists(p):
                log.error(_('{} not exists.'.format(p)))
                open_path.pop(n)
                continue
            open_path[n] = p
            n += 1
        if not open_path:
            open_path = None

    if not open_path and preferences.prefs['auto load last file'] \
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
    window = main.MainWindow(fullscreen = args.fullscreen, is_slideshow = args.slideshow,
                             show_library = args.library, manga_mode = args.manga,
                             double_page = args.doublepage, zoom_mode = args.zoommode,
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

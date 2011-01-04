#!/usr/bin/env python

"""
This script installs or uninstalls MComix on your system.
-------------------------------------------------------------------------------
Usage: install.py [OPTIONS] COMMAND

Commands:
    install                  Install to /usr/local

    uninstall                Uninstall from /usr/local

Options:
    --dir <directory>        Install or uninstall in <directory>
                             instead of /usr/local

    --no-mime                Do not install the file manager thumbnailer
                             or register new mime types for x-cbz,
                             x-cbt and x-cbr archive files.
"""

import os
import sys
import getopt
import shutil

source_dir = os.path.dirname(os.path.realpath(__file__))
install_dir = '/usr/local/'
install_mime = True

TRANSLATIONS = ('ca', 'cs', 'de', 'es', 'fr', 'gl', 'hr', 'hu', 'id', 'ja',
    'ko', 'pl', 'pt_BR', 'ru', 'sv', 'uk', 'zh_CN', 'zh_TW')

# Files to be installed, as (source file, destination directory)
FILES = (('src/about_dialog.py', 'share/mcomix/src'),
        ('src/archive_extractor.py', 'share/mcomix/src'),
        ('src/archive_packer.py', 'share/mcomix/src'),
        ('src/archive_tools.py', 'share/mcomix/src'),
        ('src/bookmark_backend.py', 'share/mcomix/src'),
        ('src/bookmark_dialog.py', 'share/mcomix/src'),
        ('src/bookmark_menu_item.py', 'share/mcomix/src'),
        ('src/bookmark_menu.py', 'share/mcomix/src'),
        ('src/clipboard.py', 'share/mcomix/src'),
        ('src/comment_dialog.py', 'share/mcomix/src'),
        ('src/constants.py', 'share/mcomix/src'),
        ('src/cursor_handler.py', 'share/mcomix/src'),
        ('src/deprecated.py', 'share/mcomix/src'),
        ('src/dialog_handler.py', 'share/mcomix/src'),
        ('src/edit_comment_area.py', 'share/mcomix/src'),
        ('src/edit_dialog.py', 'share/mcomix/src'),
        ('src/edit_image_area.py', 'share/mcomix/src'),
        ('src/encoding.py', 'share/mcomix/src'),
        ('src/enhance_backend.py', 'share/mcomix/src'),
        ('src/enhance_dialog.py', 'share/mcomix/src'),
        ('src/event.py', 'share/mcomix/src'),
        ('src/file_chooser_base_dialog.py', 'share/mcomix/src'),
        ('src/file_chooser_library_dialog.py', 'share/mcomix/src'),
        ('src/file_chooser_main_dialog.py', 'share/mcomix/src'),
        ('src/file_chooser_simple_dialog.py', 'share/mcomix/src'),
        ('src/file_handler.py', 'share/mcomix/src'),
        ('src/histogram.py', 'share/mcomix/src'),
        ('src/icons.py', 'share/mcomix/src'),
        ('src/image_handler.py', 'share/mcomix/src'),
        ('src/image_tools.py', 'share/mcomix/src'),
        ('src/labels.py', 'share/mcomix/src'),
        ('src/lens.py', 'share/mcomix/src'),
        ('src/library_add_progress_dialog.py', 'share/mcomix/src'),
        ('src/library_backend.py', 'share/mcomix/src'),
        ('src/library_book_area.py', 'share/mcomix/src'),
        ('src/library_collection_area.py', 'share/mcomix/src'),
        ('src/library_control_area.py', 'share/mcomix/src'),
        ('src/library_main_dialog.py', 'share/mcomix/src'),
        ('src/main.py', 'share/mcomix/src'),
        ('src/mcomix.py', 'share/mcomix/src'),
        ('src/pageselect.py', 'share/mcomix/src'),
        ('src/portability.py', 'share/mcomix/src'),
        ('src/preferences_dialog.py', 'share/mcomix/src'),
        ('src/preferences_page.py', 'share/mcomix/src'),
        ('src/preferences.py', 'share/mcomix/src'),
        ('src/preferences_section.py', 'share/mcomix/src'),
        ('src/process.py', 'share/mcomix/src'),
        ('src/properties_dialog.py', 'share/mcomix/src'),
        ('src/properties_page.py', 'share/mcomix/src'),
        ('src/recent.py', 'share/mcomix/src'),
        ('src/slideshow.py', 'share/mcomix/src'),
        ('src/status.py', 'share/mcomix/src'),
        ('src/thumbbar.py', 'share/mcomix/src'),
        ('src/thumbnail_tools.py', 'share/mcomix/src'),
        ('src/tools.py', 'share/mcomix/src'),
        ('src/ui.py', 'share/mcomix/src'),
        ('src/archive/__init__.py', 'share/mcomix/src/archive'),
        ('src/archive/archive_base.py', 'share/mcomix/src/archive'),
        ('src/archive/rarfile.py', 'share/mcomix/src/archive'),
        ('src/archive/rar.py', 'share/mcomix/src/archive'),
        ('src/archive/zip.py', 'share/mcomix/src/archive'),
        ('src/archive/tar.py', 'share/mcomix/src/archive'),
        ('images/mcomix.png', 'share/mcomix/images'),
        ('images/gtk-refresh.png', 'share/mcomix/images'),
        ('images/goto-first-page.png', 'share/mcomix/images'),
        ('images/goto-last-page.png', 'share/mcomix/images'),
        ('images/next-page.png', 'share/mcomix/images'),
        ('images/previous-page.png', 'share/mcomix/images'),
        ('images/next-archive.png', 'share/mcomix/images'),
        ('images/previous-archive.png', 'share/mcomix/images'),                
        ('images/16x16/mcomix.png', 'share/mcomix/images/16x16'),
        ('images/double-page.png', 'share/mcomix/images'),
        ('images/fitheight.png', 'share/mcomix/images'),
        ('images/fitmanual.png', 'share/mcomix/images'),
        ('images/fitbest.png', 'share/mcomix/images'),
        ('images/fitwidth.png', 'share/mcomix/images'),
        ('images/comments.png', 'share/mcomix/images'),
        ('images/gimp-flip-horizontal.png', 'share/mcomix/images'),
        ('images/gimp-flip-vertical.png', 'share/mcomix/images'),
        ('images/gimp-rotate-90.png', 'share/mcomix/images'),
        ('images/gimp-rotate-180.png', 'share/mcomix/images'),
        ('images/gimp-rotate-270.png', 'share/mcomix/images'),
        ('images/gimp-thumbnails.png', 'share/mcomix/images'),
        ('images/gimp-transform.png', 'share/mcomix/images'),
        ('images/zoom.png', 'share/mcomix/images'),
        ('images/lens.png', 'share/mcomix/images'),
        ('images/library.png', 'share/mcomix/images'),
        ('images/manga.png', 'share/mcomix/images'),
        ('images/tango-add-bookmark.png', 'share/mcomix/images'),
        ('images/tango-archive.png', 'share/mcomix/images'),
        ('images/tango-enhance-image.png', 'share/mcomix/images'),
        ('images/tango-image.png', 'share/mcomix/images'),
        ('mcomix.1.gz', 'share/man/man1'),
        ('mcomix.desktop', 'share/applications'),
        ('images/16x16/mcomix.png', 'share/icons/hicolor/16x16/apps'),
        ('images/22x22/mcomix.png', 'share/icons/hicolor/22x22/apps'),
        ('images/24x24/mcomix.png', 'share/icons/hicolor/24x24/apps'),
        ('images/32x32/mcomix.png', 'share/icons/hicolor/32x32/apps'),
        ('images/48x48/mcomix.png', 'share/icons/hicolor/48x48/apps'))
        
# Symlinks to be created, as (target, symlink)
LINKS = (('../share/mcomix/src/mcomix.py', 'bin/mcomix'),)

# Mime files to be installed, as (source file, destination directory)
MIME_FILES = (('mime/comicthumb', 'bin'),
              ('mime/comicthumb.1.gz', 'share/man/man1'),
              ('mime/mcomix.xml', 'share/mime/packages'),
              ('mime/icons/16x16/application-x-cbz.png',
                'share/icons/hicolor/16x16/mimetypes'),
              ('mime/icons/22x22/application-x-cbz.png',
                'share/icons/hicolor/22x22/mimetypes'),
              ('mime/icons/24x24/application-x-cbz.png',
                'share/icons/hicolor/24x24/mimetypes'),
              ('mime/icons/32x32/application-x-cbz.png',
                'share/icons/hicolor/32x32/mimetypes'),
              ('mime/icons/48x48/application-x-cbz.png',
                'share/icons/hicolor/48x48/mimetypes'))

# Mime symlinks to be created, as (target, symlink)
MIME_LINKS = (('application-x-cbz.png',
               'share/icons/hicolor/16x16/mimetypes/application-x-cbr.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/16x16/mimetypes/application-x-cbt.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/22x22/mimetypes/application-x-cbr.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/22x22/mimetypes/application-x-cbt.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/24x24/mimetypes/application-x-cbr.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/24x24/mimetypes/application-x-cbt.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/32x32/mimetypes/application-x-cbr.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/32x32/mimetypes/application-x-cbt.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/48x48/mimetypes/application-x-cbr.png'),
              ('application-x-cbz.png',
               'share/icons/hicolor/48x48/mimetypes/application-x-cbt.png'))

def info():
    """Print usage info and exit."""
    print __doc__
    sys.exit(1)

def install(src, dst):
    """Copy <src> to <dst>. The <src> path is relative to the source_dir and
    the <dst> path is a directory relative to the install_dir.
    """
    try:
        dst = os.path.join(install_dir, dst, os.path.basename(src))
        src = os.path.join(source_dir, src)

        assert os.path.isfile(src)
        assert not os.path.isdir(dst)
        if not os.path.isdir(os.path.dirname(dst)):
            os.makedirs(os.path.dirname(dst))
        shutil.copy(src, dst)
        print 'Installed', dst

    except Exception:
        print 'Could not install', dst

def uninstall(path):
    """Remove the file or directory at <path>, which is relative to the 
    install_dir.
    """
    try:
        path = os.path.join(install_dir, path)

        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
        elif os.path.isdir(path):

            shutil.rmtree(path)
        else:
            return
        print 'Removed', path

    except Exception:
        print 'Could not remove', path

def make_link(src, link):
    """Create a symlink <link> pointing to <src>. The <link> path is relative
    to the install_dir, and the <src> path is relative to the full path of
    the created link.
    """
    try:
        link = os.path.join(install_dir, link)
        if os.path.isfile(link) or os.path.islink(link):
            os.remove(link)
        if not os.path.exists(os.path.dirname(link)):
            os.makedirs(os.path.dirname(link))
        os.symlink(src, link)
        print 'Symlinked', link
    except:
        print 'Could not create symlink', link

def check_dependencies():
    """Check for required and recommended dependencies."""
    required_found = True
    recommended_found = True
    print 'Checking dependencies ...\n'
    print 'Required dependencies:'
    # Should also check the PyGTK version. To do that we have to load the
    # gtk module though, which normally can't be done while using `sudo`.
    try:
        import pygtk
        print '    PyGTK ........................ OK'
    except ImportError:
        print '    !!! PyGTK .................... Not found'
        required_found = False
    try:
        import Image
        assert Image.VERSION >= '1.1.5'
        print '    Python Imaging Library ....... OK'
    except ImportError:
        print '    !!! Python Imaging Library ... Not found'
        required_found = False
    except AssertionError:
        print '    !!! Python Imaging Library ... version', Image.VERSION,
        print 'found'
        print '    !!! Python Imaging Library 1.1.5 or higher is required'
        required_found = False
    print '\nRecommended dependencies:'
    # rar/unrar is only a requirement to read RAR (.cbr) files.
    rar = False
    for path in os.getenv('PATH').split(':'):
        if (os.path.isfile(os.path.join(path, 'unrar')) or
            os.path.isfile(os.path.join(path, 'rar'))):
            print '    rar/unrar .................... OK'
            rar = True
            break
    if not rar:
        print '    !!! rar/unrar ................ Not found'
        recommended_found = False
    if not required_found:
        print '\nCould not find all required dependencies!'
        print 'Please install them and try again.'
        sys.exit(1)
    if not recommended_found:
        print '\nNote that not all recommeded dependencies were found.'
        print 'MComix has still been installed, but will not be able to'
        print 'use all its functions until they are installed.'
    print


# ---------------------------------------------------------------------------
# Parse the command line.
# ---------------------------------------------------------------------------
try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], '', ['dir=', 'no-mime'])
except getopt.GetoptError:
    info()
for opt, value in opts:
    if opt == '--dir':
        install_dir = value
        if not os.path.isdir(install_dir):
            print '\n!!! Error:', install_dir, 'does not exist.' 
            info()
    elif opt == '--no-mime':
        install_mime = False

# ---------------------------------------------------------------------------
# Install MComix.
# ---------------------------------------------------------------------------
if args == ['install']:
    check_dependencies()
    print 'Installing MComix to', install_dir, '...\n'
    if not os.access(install_dir, os.W_OK):
        print 'You do not have write permissions to', install_dir
        sys.exit(1)
    for src, dst in FILES:
        install(src, dst)
    for lang in TRANSLATIONS:
        install(os.path.join('messages', lang, 'LC_MESSAGES/mcomix.mo'),
            os.path.join('share/locale/', lang, 'LC_MESSAGES'))
    for src, link in LINKS:
        make_link(src, link)
    if install_mime:
        for src, dst in MIME_FILES:
            install(src, dst)
        for src, link in MIME_LINKS:
            make_link(src, link)
        os.popen('update-mime-database "%s"' % 
            os.path.join(install_dir, 'share/mime'))
        print '\nUpdated mime database (added .cbz, .cbr and .cbt file types.)'
        schema = os.path.join(source_dir, 'mime/comicbook.schemas')
        os.popen('GCONF_CONFIG_SOURCE=$(gconftool-2 --get-default-source) '
                 'gconftool-2 --makefile-install-rule "%s" 2>/dev/null' %
                    schema)
        print '\nRegistered comic archive thumbnailer in gconf (if available).'
        print 'The thumbnailer is only supported by some file managers,',
        print 'such as Nautilus'
        print 'and Thunar.'
        print 'You might have to restart the file manager for the thumbnailer',
        print 'to be activated.'
    os.utime(os.path.join(install_dir, 'share/icons/hicolor'), None)
# ---------------------------------------------------------------------------
# Uninstall MComix.
# ---------------------------------------------------------------------------
elif args == ['uninstall']:
    print 'Uninstalling MComix from', install_dir, '...\n'
    uninstall('share/mcomix')
    uninstall('share/man/man1/mcomix.1.gz')
    uninstall('share/applications/mcomix.desktop')
    uninstall('share/icons/hicolor/16x16/apps/mcomix.png')
    uninstall('share/icons/hicolor/22x22/apps/mcomix.png')
    uninstall('share/icons/hicolor/24x24/apps/mcomix.png')
    uninstall('share/icons/hicolor/32x32/apps/mcomix.png')
    uninstall('share/icons/hicolor/48x48/apps/mcomix.png')

    for _, link in LINKS:
        uninstall(link)
    for lang in TRANSLATIONS:
        uninstall(os.path.join('share/locale', lang, 'LC_MESSAGES/mcomix.mo'))
    for src, path in MIME_FILES:
        uninstall(os.path.join(path, os.path.basename(src)))
    for _, link in MIME_LINKS:
        uninstall(link)
    
    # These are from old versions of Comix, we try to remove them anyway.
    uninstall('share/pixmaps/comix.png')
    uninstall('share/pixmaps/comix')
    uninstall('/tmp/comix')
    
    print '\nThere might still be files in ~/.mcomix/ left on your system.'
    print 'Please remove that directory manually if you do not plan to'
    print 'install Comix again later.'

else:
    info()


# vim: expandtab:sw=4:ts=4

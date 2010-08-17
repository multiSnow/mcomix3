#!/usr/bin/env python

"""
This script installs or uninstalls Comix on your system.
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

# These translations have not yet been updated for Comix 4:
# 'de', 'it', 'nl', 'el', 'fa'

# Files to be installed, as (source file, destination directory)
FILES = (('src/about.py', 'share/comix/src'),
         ('src/about.pyc', 'share/comix/src'),
         ('src/archive.py', 'share/comix/src'),
         ('src/archive.pyc', 'share/comix/src'),
         ('src/bookmark.py', 'share/comix/src'),
         ('src/bookmark.pyc', 'share/comix/src'),
         ('src/comix.py', 'share/comix/src'),
         ('src/comment.py', 'share/comix/src'),
         ('src/comment.pyc', 'share/comix/src'),
         ('src/constants.py', 'share/comix/src'),
         ('src/constants.pyc', 'share/comix/src'),
         ('src/cursor.py', 'share/comix/src'),
         ('src/cursor.pyc', 'share/comix/src'),
         ('src/deprecated.py', 'share/comix/src'),
         ('src/deprecated.pyc', 'share/comix/src'),
         ('src/edit.py', 'share/comix/src'),
         ('src/edit.pyc', 'share/comix/src'),
         ('src/encoding.py', 'share/comix/src'),
         ('src/encoding.pyc', 'share/comix/src'),
         ('src/enhance.py', 'share/comix/src'),
         ('src/enhance.pyc', 'share/comix/src'),
         ('src/event.py', 'share/comix/src'),
         ('src/event.pyc', 'share/comix/src'),
         ('src/filechooser.py', 'share/comix/src'),
         ('src/filechooser.pyc', 'share/comix/src'),
         ('src/filehandler.py', 'share/comix/src'),
         ('src/filehandler.pyc', 'share/comix/src'),
         ('src/histogram.py', 'share/comix/src'),
         ('src/histogram.pyc', 'share/comix/src'),
         ('src/icons.py', 'share/comix/src'),
         ('src/icons.pyc', 'share/comix/src'),
         ('src/image.py', 'share/comix/src'),
         ('src/image.pyc', 'share/comix/src'),
         ('src/labels.py', 'share/comix/src'),
         ('src/labels.pyc', 'share/comix/src'),
         ('src/lens.py', 'share/comix/src'),
         ('src/lens.pyc', 'share/comix/src'),
         ('src/library.py', 'share/comix/src'),
         ('src/library.pyc', 'share/comix/src'),
         ('src/librarybackend.py', 'share/comix/src'),
         ('src/librarybackend.pyc', 'share/comix/src'),
         ('src/main.py', 'share/comix/src'),
         ('src/main.pyc', 'share/comix/src'),
         ('src/portability.py', 'share/comix/src'),
         ('src/portability.pyc', 'share/comix/src'),
         ('src/preferences.py', 'share/comix/src'),
         ('src/preferences.pyc', 'share/comix/src'),
         ('src/process.py', 'share/comix/src'),
         ('src/process.pyc', 'share/comix/src'),
         ('src/properties.py', 'share/comix/src'),
         ('src/properties.pyc', 'share/comix/src'),
         ('src/recent.py', 'share/comix/src'),
         ('src/recent.pyc', 'share/comix/src'),
         ('src/slideshow.py', 'share/comix/src'),
         ('src/slideshow.pyc', 'share/comix/src'),
         ('src/status.py', 'share/comix/src'),
         ('src/status.pyc', 'share/comix/src'),
         ('src/thumbbar.py', 'share/comix/src'),
         ('src/thumbbar.pyc', 'share/comix/src'),
         ('src/thumbnail.py', 'share/comix/src'),
         ('src/thumbnail.pyc', 'share/comix/src'),
         ('src/thumbremover.py', 'share/comix/src'),
         ('src/thumbremover.pyc', 'share/comix/src'),
         ('src/ui.py', 'share/comix/src'),
         ('src/ui.pyc', 'share/comix/src'),
         ('images/16x16/comix.png', 'share/comix/images/16x16'),
         ('images/comix.svg', 'share/comix/images'),
         ('images/double-page.png', 'share/comix/images'),
         ('images/fitheight.png', 'share/comix/images'),
         ('images/fitmanual.png', 'share/comix/images'),
         ('images/fitbest.png', 'share/comix/images'),
         ('images/fitwidth.png', 'share/comix/images'),
         ('images/comments.png', 'share/comix/images'),
         ('images/gimp-flip-horizontal.png', 'share/comix/images'),
         ('images/gimp-flip-vertical.png', 'share/comix/images'),
         ('images/gimp-rotate-90.png', 'share/comix/images'),
         ('images/gimp-rotate-180.png', 'share/comix/images'),
         ('images/gimp-rotate-270.png', 'share/comix/images'),
         ('images/gimp-thumbnails.png', 'share/comix/images'),
         ('images/gimp-transform.png', 'share/comix/images'),
         ('images/zoom.png', 'share/comix/images'),
         ('images/lens.png', 'share/comix/images'),
         ('images/library.png', 'share/comix/images'),
         ('images/manga.png', 'share/comix/images'),
         ('images/tango-add-bookmark.png', 'share/comix/images'),
         ('images/tango-archive.png', 'share/comix/images'),
         ('images/tango-enhance-image.png', 'share/comix/images'),
         ('images/tango-image.png', 'share/comix/images'),
         ('comix.1.gz', 'share/man/man1'),
         ('comix.desktop', 'share/applications'),
         ('images/16x16/comix.png', 'share/icons/hicolor/16x16/apps'),
         ('images/22x22/comix.png', 'share/icons/hicolor/22x22/apps'),
         ('images/24x24/comix.png', 'share/icons/hicolor/24x24/apps'),
         ('images/32x32/comix.png', 'share/icons/hicolor/32x32/apps'),
         ('images/48x48/comix.png', 'share/icons/hicolor/48x48/apps'),
         ('images/comix.svg', 'share/icons/hicolor/scalable/apps'))

# Symlinks to be created, as (target, symlink)
LINKS = (('../share/comix/src/comix.py', 'bin/comix'),)

# Mime files to be installed, as (source file, destination directory)
MIME_FILES = (('mime/comicthumb', 'bin'),
              ('mime/comicthumb.1.gz', 'share/man/man1'),
              ('mime/comix.xml', 'share/mime/packages'),
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
        print 'Comix has still been installed, but will not be able to'
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
# Install Comix.
# ---------------------------------------------------------------------------
if args == ['install']:
    check_dependencies()
    print 'Installing Comix to', install_dir, '...\n'
    if not os.access(install_dir, os.W_OK):
        print 'You do not have write permissions to', install_dir
        sys.exit(1)
    for src, dst in FILES:
        install(src, dst)
    for lang in TRANSLATIONS:
        install(os.path.join('messages', lang, 'LC_MESSAGES/comix.mo'),
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
# Uninstall Comix.
# ---------------------------------------------------------------------------
elif args == ['uninstall']:
    print 'Uninstalling Comix from', install_dir, '...\n'
    uninstall('share/comix')
    uninstall('share/man/man1/comix.1.gz')
    uninstall('share/applications/comix.desktop')
    uninstall('share/icons/hicolor/16x16/apps/comix.png')
    uninstall('share/icons/hicolor/22x22/apps/comix.png')
    uninstall('share/icons/hicolor/24x24/apps/comix.png')
    uninstall('share/icons/hicolor/32x32/apps/comix.png')
    uninstall('share/icons/hicolor/48x48/apps/comix.png')
    uninstall('share/icons/hicolor/scalable/apps/comix.svg')
    for _, link in LINKS:
        uninstall(link)
    for lang in TRANSLATIONS:
        uninstall(os.path.join('share/locale', lang, 'LC_MESSAGES/comix.mo'))
    for src, path in MIME_FILES:
        uninstall(os.path.join(path, os.path.basename(src)))
    for _, link in MIME_LINKS:
        uninstall(link)
    
    # These are from old versions of Comix, we try to remove them anyway.
    uninstall('share/pixmaps/comix.png')
    uninstall('share/pixmaps/comix')
    uninstall('/tmp/comix')
    
    print '\nThere might still be files in ~/.comix/ left on your system.'
    print 'Please remove that directory manually if you do not plan to'
    print 'install Comix again later.'
else:
    info()


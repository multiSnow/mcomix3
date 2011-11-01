"""properties_dialog.py - Properties dialog that displays information about the archive/file."""

import gtk
import os
import time
import stat
try:
    import pwd
except ImportError:
    # Running on non-Unix machine.
    pass

from mcomix import i18n
from mcomix import strings
from mcomix import properties_page

class _PropertiesDialog(gtk.Dialog):

    def __init__(self, window):

        gtk.Dialog.__init__(self, _('Properties'), window, 0,
            (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.set_resizable(True)
        self.set_has_separator(False)
        self.set_default_response(gtk.RESPONSE_CLOSE)
        notebook = gtk.Notebook()
        self.set_border_width(4)
        notebook.set_border_width(6)
        self.vbox.pack_start(notebook, False, False, 0)

        if window.filehandler.archive_type is not None:
            # ------------------------------------------------------------
            # Archive tab
            # ------------------------------------------------------------
            page = properties_page._Page()
            thumb = window.imagehandler.get_thumbnail(1, width=200, height=128)
            page.set_thumbnail(thumb)
            filename = window.filehandler.get_pretty_current_filename()
            page.set_filename(filename)

            try:
                stats = os.stat(window.filehandler.get_path_to_base())

                main_info = (
                    _('%d pages') % window.imagehandler.get_number_of_pages(),
                    _('%d comments') %
                        window.filehandler.get_number_of_comments(),
                    strings.ARCHIVE_DESCRIPTIONS[window.filehandler.archive_type],
                    '%.1f MiB' % (stats.st_size / 1048576.0))

                page.set_main_info(main_info)

                try:
                    uid = pwd.getpwuid(stats.st_uid)[0]
                except Exception:
                    uid = str(stats.st_uid)

                secondary_info = (
                    (_('Location'), i18n.to_unicode(os.path.dirname(
                    window.filehandler.get_path_to_base()))),
                    (_('Accessed'), time.strftime('%Y-%m-%d, %H:%M:%S',
                    time.localtime(stats.st_atime))),
                    (_('Modified'), time.strftime('%Y-%m-%d, %H:%M:%S',
                    time.localtime(stats.st_mtime))),
                    (_('Permissions'), oct(stat.S_IMODE(stats.st_mode))),
                    (_('Owner'), uid))

                page.set_secondary_info(secondary_info)

            except Exception:
                pass

            notebook.append_page(page, gtk.Label(_('Archive')))

        # ----------------------------------------------------------------
        # Image tab
        # ----------------------------------------------------------------
        path = window.imagehandler.get_path_to_page()
        page = properties_page._Page()
        thumb = window.imagehandler.get_thumbnail(width=200, height=128)
        page.set_thumbnail(thumb)
        filename = os.path.basename(path)
        page.set_filename(filename)
        try:
            stats = os.stat(path)
            width, height = window.imagehandler.get_size()
            main_info = (
                '%dx%d px' % (width, height),
                window.imagehandler.get_mime_name(),
                '%.1f KiB' % (stats.st_size / 1024.0))
            page.set_main_info(main_info)
            try:
                uid = pwd.getpwuid(stats.st_uid)[0]
            except Exception:
                uid = str(stats.st_uid)
            secondary_info = (
                (_('Location'), i18n.to_unicode(os.path.dirname(path))),
                (_('Accessed'), time.strftime('%Y-%m-%d, %H:%M:%S',
                time.localtime(stats.st_atime))),
                (_('Modified'), time.strftime('%Y-%m-%d, %H:%M:%S',
                time.localtime(stats.st_mtime))),
                (_('Permissions'), oct(stat.S_IMODE(stats.st_mode))),
                (_('Owner'), uid))
            page.set_secondary_info(secondary_info)
        except Exception:
            pass
        notebook.append_page(page, gtk.Label(_('Image')))
        self.show_all()

# vim: expandtab:sw=4:ts=4

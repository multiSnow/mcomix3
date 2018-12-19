"""properties_dialog.py - Properties dialog that displays information about the archive/file."""

from gi.repository import Gtk
import os
import time
import stat
try:
    import pwd
    _has_pwd = True
except ImportError:
    # Running on non-Unix machine.
    _has_pwd = False

from mcomix import i18n
from mcomix import strings
from mcomix import properties_page
from mcomix import tools

class _PropertiesDialog(Gtk.Dialog):

    def __init__(self, window):

        super(_PropertiesDialog, self).__init__(_('Properties'), window, 0,
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))

        self._window = window
        self.resize(500, 430)
        self.set_resizable(True)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        notebook = Gtk.Notebook()
        self.set_border_width(4)
        notebook.set_border_width(6)
        self.vbox.pack_start(notebook, True, True, 0)

        self._archive_page = properties_page._Page()
        notebook.append_page(self._archive_page, Gtk.Label(label=_('Archive')))
        self._image_page = properties_page._Page()
        notebook.append_page(self._image_page, Gtk.Label(label=_('Image')))
        self._update_archive_page()
        self._window.page_changed += self._on_page_change
        self._window.filehandler.file_opened += self._on_book_change
        self._window.filehandler.file_closed += self._on_book_change
        self._window.imagehandler.page_available += self._on_page_available

        self.show_all()

    def _on_page_change(self):
        self._update_image_page()

    def _on_book_change(self):
        self._update_archive_page()

    def _on_page_available(self, page_number):
        if 1 == page_number:
            self._update_page_image(self._archive_page, 1)
        current_page_number = self._window.imagehandler.get_current_page()
        if current_page_number == page_number:
            self._update_image_page()

    def _update_archive_page(self):
        self._update_image_page()
        page = self._archive_page
        page.reset()
        window = self._window

        if window.filehandler.archive_type is None:
          self._update_page_image(page, 1)
          path=window.filehandler.get_path_to_base()
          name = os.path.basename(path)
          #filename = window.filehandler.get_pretty_current_filename()
          page.set_filename(name)

          main_info = (
            _('%d pages') % window.imagehandler.get_number_of_pages(),
            _('%d comments') %
                window.filehandler.get_number_of_comments(),
            'Directory'
          )
          page.set_main_info(main_info)
          self._update_page_secondary_info(page, path)
          page.show_all()
          return

        # In case it's not ready yet, bump the cover extraction
        # in front of the queue.
        path = window.imagehandler.get_path_to_page(1)
        if path is not None:
            window.filehandler._ask_for_files([path])
        self._update_page_image(page, 1)
        filename = window.filehandler.get_pretty_current_filename()
        page.set_filename(filename)
        path = window.filehandler.get_path_to_base()
        main_info = (
            _('%d pages') % window.imagehandler.get_number_of_pages(),
            _('%d comments') %
                window.filehandler.get_number_of_comments(),
            strings.ARCHIVE_DESCRIPTIONS[window.filehandler.archive_type]
        )
        page.set_main_info(main_info)
        self._update_page_secondary_info(page, path)
        page.show_all()

    def _update_image_page(self):
        page = self._image_page
        page.reset()
        window = self._window
        if not window.imagehandler.page_is_available():
            return
        self._update_page_image(page)
        path = window.imagehandler.get_path_to_page()
        filename = os.path.basename(path)
        page.set_filename(filename)
        width, height = window.imagehandler.get_size()
        main_info = (
            '%dx%d px' % (width, height),
            window.imagehandler.get_mime_name(),
        )
        page.set_main_info(main_info)
        self._update_page_secondary_info(page, path)
        page.show_all()

    def _update_page_image(self, page, page_number=None):
        if not self._window.imagehandler.page_is_available(page_number):
            return
        thumb = self._window.imagehandler.get_thumbnail(page_number, width=128, height=128)
        page.set_thumbnail(thumb)

    def _update_page_secondary_info(self, page, location):
        secondary_info = [
            (_('Location'), i18n.to_unicode(os.path.dirname(location))),
        ]
        try:
            stats = os.stat(location)
        except OSError as e:
            page.set_secondary_info(secondary_info)
            return
        if _has_pwd:
            uid = pwd.getpwuid(stats.st_uid)[0]
        else:
            uid = str(stats.st_uid)
        secondary_info.extend((
            (_('Size'), tools.format_byte_size(stats.st_size)),
            (_('Accessed'), time.strftime('%Y-%m-%d, %H:%M:%S',
            time.localtime(stats.st_atime))),
            (_('Modified'), time.strftime('%Y-%m-%d, %H:%M:%S',
            time.localtime(stats.st_mtime))),
            (_('Permissions'), oct(stat.S_IMODE(stats.st_mode))),
            (_('Owner'), uid)
        ))
        page.set_secondary_info(secondary_info)

# vim: expandtab:sw=4:ts=4

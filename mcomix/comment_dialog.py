"""comment.py - Comments dialog."""

import os
import gtk

from mcomix import i18n

class _CommentsDialog(gtk.Dialog):

    def __init__(self, window):
        gtk.Dialog.__init__(self, _('Comments'), window, 0,
            (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self.set_has_separator(False)
        self.set_resizable(True)
        self.set_default_response(gtk.RESPONSE_CLOSE)
        self.set_default_size(600, 550)
        self.set_border_width(4)

        tag = gtk.TextTag()
        tag.set_property('editable', False)
        tag.set_property('editable-set', True)
        tag.set_property('family', 'Monospace')
        tag.set_property('family-set', True)
        tag.set_property('scale', 0.9)
        tag.set_property('scale-set', True)
        tag_table = gtk.TextTagTable()
        tag_table.add(tag)

        self._tag = tag
        self._tag_table = tag_table
        self._notebook = None
        self._window = window
        self._comments = []

        self._window.filehandler.file_available += self._on_file_available
        self._window.filehandler.file_opened += self._update_comments
        self._window.filehandler.file_closed += self._update_comments
        self._update_comments()
        self.show_all()

    def _on_file_available(self, path_list):
        for path in path_list:
            if path in self._comments:
                self._add_comment(path, self._comments[path])
        self._notebook.show_all()

    def _update_comments(self):

        if self._notebook is not None:
            self._notebook.destroy()
            self._notebook = None

        notebook = gtk.Notebook()
        notebook.set_scrollable(True)
        notebook.set_border_width(6)
        self.vbox.pack_start(notebook)
        self._notebook = notebook
        self._comments = {}

        for num in xrange(1, self._window.filehandler.get_number_of_comments() + 1):
            path = self._window.filehandler.get_comment_name(num)
            if self._window.filehandler.file_is_available(path):
                self._add_comment(path, num)
            else:
                # In case it's not ready yet, bump it's
                # extraction in front of the queue.
                self._window.filehandler._ask_for_files([path])
            self._comments[path] = num

        self._notebook.show_all()

    def _add_comment(self, path, num):

        name = os.path.basename(path)

        page = gtk.VBox(False)
        page.set_border_width(8)

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        page.pack_start(scrolled)

        outbox = gtk.EventBox()
        scrolled.add_with_viewport(outbox)

        inbox = gtk.EventBox()
        inbox.set_border_width(6)
        outbox.add(inbox)

        text = self._window.filehandler.get_comment_text(num)
        if text is None:
            text = _('Could not read %s') % name

        text_buffer = gtk.TextBuffer(self._tag_table)
        text_buffer.set_text(i18n.to_unicode(text))
        text_buffer.apply_tag(self._tag, *text_buffer.get_bounds())
        text_view = gtk.TextView(text_buffer)
        inbox.add(text_view)

        bg_color = text_view.get_default_attributes().bg_color
        outbox.modify_bg(gtk.STATE_NORMAL, bg_color)
        tab_label = gtk.Label(i18n.to_unicode(name))
        self._notebook.insert_page(page, tab_label)


# vim: expandtab:sw=4:ts=4

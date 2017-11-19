"""bookmark_dialog.py - Bookmarks dialog handler."""

from gi.repository import Gdk, GdkPixbuf, Gtk, GObject

from mcomix import constants
from mcomix import bookmark_menu_item
from mcomix.tools import cmp

class _BookmarksDialog(Gtk.Dialog):

    """_BookmarksDialog lets the user remove or rearrange bookmarks."""

    _SORT_TYPE, _SORT_NAME, _SORT_PAGE, _SORT_ADDED = 100, 101, 102, 103

    def __init__(self, window, bookmarks_store):
        super(_BookmarksDialog, self).__init__(_('Edit Bookmarks'), window, Gtk.DialogFlags.DESTROY_WITH_PARENT,
            (Gtk.STOCK_REMOVE, constants.RESPONSE_REMOVE,
             Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))

        self._bookmarks_store = bookmarks_store

        self.set_resizable(True)
        self.set_default_response(Gtk.ResponseType.CLOSE)
        # scroll area fill to the edge (TODO window should not really be a dialog)
        self.set_border_width(0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_border_width(0)
        scrolled.set_shadow_type(Gtk.ShadowType.IN)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.vbox.pack_start(scrolled, True, True, 0)

        self._liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, GObject.TYPE_STRING,
            GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING, bookmark_menu_item._Bookmark)

        self._treeview = Gtk.TreeView(model=self._liststore)
        self._treeview.set_rules_hint(True)
        self._treeview.set_reorderable(True)
        # search by typing first few letters of name
        self._treeview.set_search_column(1)
        self._treeview.set_enable_search(True)
        self._treeview.set_headers_clickable(True)
        self._selection = self._treeview.get_selection()

        scrolled.add(self._treeview)

        cellrenderer_text = Gtk.CellRendererText()
        cellrenderer_pbuf = Gtk.CellRendererPixbuf()

        self._icon_col = Gtk.TreeViewColumn(_('Type'), cellrenderer_pbuf)
        self._name_col = Gtk.TreeViewColumn(_('Name'), cellrenderer_text)
        self._page_col = Gtk.TreeViewColumn(_('Page'), cellrenderer_text)
        self._path_col = Gtk.TreeViewColumn(_('Location'), cellrenderer_text)
        # TRANSLATORS: "Added" as in "Date Added"
        self._date_add_col = Gtk.TreeViewColumn(_('Added'), cellrenderer_text)

        self._treeview.append_column(self._icon_col)
        self._treeview.append_column(self._name_col)
        self._treeview.append_column(self._page_col)
        self._treeview.append_column(self._path_col)
        self._treeview.append_column(self._date_add_col)

        self._icon_col.set_attributes(cellrenderer_pbuf, pixbuf=0)
        self._name_col.set_attributes(cellrenderer_text, text=1)
        self._page_col.set_attributes(cellrenderer_text, text=2)
        self._path_col.set_attributes(cellrenderer_text, text=3)
        self._date_add_col.set_attributes(cellrenderer_text, text=4)
        self._name_col.set_expand(True)

        self._liststore.set_sort_func(_BookmarksDialog._SORT_TYPE,
            self._sort_model, ('_archive_type', '_name', '_page'))
        self._liststore.set_sort_func(_BookmarksDialog._SORT_NAME,
            self._sort_model, ('_name', '_page', '_path'))
        self._liststore.set_sort_func(_BookmarksDialog._SORT_PAGE,
            self._sort_model, ('_page', '_numpages', '_name'))
        self._liststore.set_sort_func(_BookmarksDialog._SORT_ADDED,
            self._sort_model, ('_date_added',))

        self._icon_col.set_sort_column_id(_BookmarksDialog._SORT_TYPE)
        self._name_col.set_sort_column_id(_BookmarksDialog._SORT_NAME)
        self._page_col.set_sort_column_id(_BookmarksDialog._SORT_PAGE)
        self._path_col.set_sort_column_id(3)
        self._date_add_col.set_sort_column_id(_BookmarksDialog._SORT_ADDED)

        self._icon_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._name_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._page_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._path_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._date_add_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        # FIXME Hide extra columns. Needs UI controls to enable these.
        self._path_col.set_visible(False)

        self.resize(600, 450)

        self.connect('response', self._response)
        self.connect('delete_event', self._close)

        self._treeview.connect('key_press_event', self._key_press_event)
        self._treeview.connect('row_activated', self._bookmark_activated)

        for bookmark in self._bookmarks_store.get_bookmarks():
            self._add_bookmark(bookmark)

        self.show_all()

    def _add_bookmark(self, bookmark):
        """Add the <bookmark> to the dialog."""
        self._liststore.prepend(bookmark.to_row())

    def _remove_selected(self):
        """Remove the currently selected bookmark from the dialog and from
        the store."""

        treeiter = self._selection.get_selected()[1]

        if treeiter is not None:

            bookmark = self._liststore.get_value(treeiter, 5)
            self._liststore.remove(treeiter)
            self._bookmarks_store.remove_bookmark(bookmark)

    def _bookmark_activated(self, treeview, path, view_column, *args):
        """ Open the activated bookmark. """

        iter = treeview.get_model().get_iter(path)
        bookmark = treeview.get_model().get_value(iter, 5)

        self._close()
        bookmark._load()

    def _sort_model(self, treemodel, iter1, iter2, user_data):
        """ Custom sort function to sort to model entries based on the
        BookmarkMenuItem's fields specified in @C{user_data}. This is a list
        of field names. """
        if iter1 == iter2:
            return 0
        if iter1 is None:
            return 1
        elif iter2 is None:
            return -1

        bookmark1 = treemodel.get_value(iter1, 5)
        bookmark2 = treemodel.get_value(iter2, 5)

        for field in user_data:
            result = cmp(getattr(bookmark1, field),
                getattr(bookmark2, field))
            if result != 0:
                return result

        # If the loop didn't return, both entries are equal.
        return 0

    def _response(self, dialog, response):

        if response == Gtk.ResponseType.CLOSE:
            self._close()

        elif response == constants.RESPONSE_REMOVE:
            self._remove_selected()

        else:
            self.destroy()

    def _key_press_event(self, dialog, event, *args):

        if event.keyval == Gdk.KEY_Delete:
            self._remove_selected()

    def _close(self, *args):
        """Close the dialog and update the _BookmarksStore with the new
        ordering."""

        ordering = []
        treeiter = self._liststore.get_iter_first()

        while treeiter is not None:
            bookmark = self._liststore.get_value(treeiter, 5)
            ordering.insert(0, bookmark)
            treeiter = self._liststore.iter_next(treeiter)

        for bookmark in ordering:
            self._bookmarks_store.remove_bookmark(bookmark)
            self._bookmarks_store.add_bookmark(bookmark)

        self.destroy()


# vim: expandtab:sw=4:ts=4

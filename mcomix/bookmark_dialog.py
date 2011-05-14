"""bookmark_dialog.py - Bookmarks dialog handler."""

import gtk
import gobject
import constants
import bookmark_menu_item

class _BookmarksDialog(gtk.Dialog):

    """_BookmarksDialog lets the user remove or rearrange bookmarks."""

    def __init__(self, window, bookmarks_store):
        gtk.Dialog.__init__(self, _('Edit Bookmarks'), window, gtk.DIALOG_DESTROY_WITH_PARENT,
            (gtk.STOCK_SORT_ASCENDING, constants.RESPONSE_SORT_ASCENDING,
             gtk.STOCK_SORT_DESCENDING, constants.RESPONSE_SORT_DESCENDING,
             gtk.STOCK_REMOVE, constants.RESPONSE_REMOVE,
             gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

        self._bookmarks_store = bookmarks_store

        self.set_has_separator(False)
        self.set_resizable(True)
        self.set_default_response(gtk.RESPONSE_CLOSE)
        # scroll area fill to the edge (TODO window should not really be a dialog)
        self.set_border_width(0)

        scrolled = gtk.ScrolledWindow()
        scrolled.set_border_width(0)
        scrolled.set_shadow_type(gtk.SHADOW_IN)
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.vbox.pack_start(scrolled)

        self._liststore = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING,
            gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, bookmark_menu_item._Bookmark)

        self._treeview = gtk.TreeView(self._liststore)
        self._treeview.set_rules_hint(True)
        self._treeview.set_reorderable(True)
        # search by typing first few letters of name
        self._treeview.set_search_column(1)
        self._treeview.set_enable_search(True)
        self._treeview.set_headers_clickable(True)
        self._selection = self._treeview.get_selection()

        scrolled.add(self._treeview)

        cellrenderer_text = gtk.CellRendererText()
        cellrenderer_pbuf = gtk.CellRendererPixbuf()

        self._icon_col = gtk.TreeViewColumn(_('Type'), cellrenderer_pbuf)
        self._name_col = gtk.TreeViewColumn(_('Name'), cellrenderer_text)
        self._page_col = gtk.TreeViewColumn(_('Page'), cellrenderer_text)
        self._path_col = gtk.TreeViewColumn(_('Location'), cellrenderer_text)
        # TRANSLATORS: "Added" as in "Date Added"
        self._date_add_col = gtk.TreeViewColumn(_('Added'), cellrenderer_text)

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

        self._icon_col.set_sort_column_id(1)
        self._name_col.set_sort_column_id(2)
        self._page_col.set_sort_column_id(3)
        self._path_col.set_sort_column_id(4)
        self._date_add_col.set_sort_column_id(5)

        self._icon_col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._name_col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._page_col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._path_col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self._date_add_col.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)

        # FIXME Hide extra columns. Needs UI controls to enable these.
        self._path_col.set_visible(False)
        # self._date_add_col.set_visible(False)

        self.resize(600, 450)

        self.connect('response', self._response)
        self.connect('delete_event', self._close)

        self._treeview.connect('key_press_event', self._key_press_event)

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

    def _sort(self, sort_ascending):

        model_row_array = []
        i = 0
        for model_row in self._liststore:
            model_row_array.append( (i, model_row) )
            i += 1

        if sort_ascending:
            sorted_model_rows = sorted( model_row_array, cmp=self._asc_sort_comparator )
        else:
            sorted_model_rows = sorted( model_row_array, cmp=self._desc_sort_comparator )

        new_order = []
        for sorted_model_row in sorted_model_rows:
            new_order.append(sorted_model_row[0])

        self._liststore.reorder(new_order)

    def _asc_sort_comparator(self, x, y):

        x_menuitem = x[1][5]
        y_menuitem = y[1][5]

        if x_menuitem._name < y_menuitem._name:
            return -1
        elif x_menuitem._name > y_menuitem._name:
            return 1
        else:
            if x_menuitem._page < y_menuitem._page:
                return -1
            elif x_menuitem._page > y_menuitem._page:
                return 1
            else:
                if x_menuitem._path < y_menuitem._path:
                    return -1
                elif x_menuitem._path > y_menuitem._path:
                    return 1
                else:
                    return 0

    def _desc_sort_comparator(self, x, y):

        x_menuitem = x[1][5]
        y_menuitem = y[1][5]

        if x_menuitem._name < y_menuitem._name:
            return 1
        elif x_menuitem._name > y_menuitem._name:
            return -1
        else:
            if x_menuitem._page < y_menuitem._page:
                return 1
            elif x_menuitem._page > y_menuitem._page:
                return -1
            else:
                if x_menuitem._path < y_menuitem._path:
                    return 1
                elif x_menuitem._path > y_menuitem._path:
                    return -1
                else:
                    return 0

    def _response(self, dialog, response):

        if response == gtk.RESPONSE_CLOSE:
            self._close()

        elif response == constants.RESPONSE_REMOVE:
            self._remove_selected()

        elif response == constants.RESPONSE_SORT_ASCENDING:
            self._sort(True)

        elif response == constants.RESPONSE_SORT_DESCENDING:
            self._sort(False)

    def _key_press_event(self, dialog, event, *args):

        if event.keyval == gtk.keysyms.Delete:
            self._remove_selected()

    def _close(self, *args):
        """Close the dialog and update the _BookmarksStore with the new
        ordering."""

        ordering = []
        treeiter = self._liststore.get_iter_root()

        while treeiter is not None:
            bookmark = self._liststore.get_value(treeiter, 5)
            ordering.insert(0, bookmark)
            treeiter = self._liststore.iter_next(treeiter)

        for bookmark in ordering:
            self._bookmarks_store.remove_bookmark(bookmark)
            self._bookmarks_store.add_bookmark(bookmark)

        self.destroy()


# vim: expandtab:sw=4:ts=4

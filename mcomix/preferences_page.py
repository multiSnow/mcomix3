"""preferences_page.py - MComix preference page."""

from gi.repository import Gtk

from mcomix import preferences_section

class _PreferencePage(Gtk.VBox):

    """The _PreferencePage is a conveniece class for making one "page"
    in a preferences-style dialog that contains one or more
    _PreferenceSections.
    """

    def __init__(self, right_column_width):
        """Create a new page where any possible right columns have the
        width request <right_column_width>.
        """
        super(_PreferencePage, self).__init__(False, 12)
        self.set_border_width(12)
        self._right_column_width = right_column_width
        self._section = None

    def new_section(self, header):
        """Start a new section in the page, with the header text from
        <header>.
        """
        self._section = preferences_section._PreferenceSection(header, self._right_column_width)
        self.pack_start(self._section, False, False, 0)

    def add_row(self, left_item, right_item=None):
        """Add a row to the page (in the latest section), containing one
        or two items. If the left item is a label it is automatically
        aligned properly.
        """
        if isinstance(left_item, Gtk.Label):
            left_item.set_alignment(0, 0.5)

        if right_item is None:
            self._section.contentbox.pack_start(left_item, True, True, 0)
        else:
            left_box, right_box = self._section.new_split_vboxes()
            left_box.pack_start(left_item, True, True, 0)
            right_box.pack_start(right_item, True, True, 0)

# vim: expandtab:sw=4:ts=4

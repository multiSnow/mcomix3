"""preferences_section.py - Preference dialog section."""

import gtk

from mcomix import labels

class _PreferenceSection(gtk.VBox):

    """The _PreferenceSection is a convenience class for making one
    "section" of a preference-style dialog, e.g. it has a bold header
    and a number of rows which are indented with respect to that header.
    """

    def __init__(self, header, right_column_width):
        """Contruct a new section with the header set to the text in
        <header>, and the width request of the (possible) right columns
        set to that of <right_column_width>.
        """
        super(_PreferenceSection, self).__init__(False, 0)
        self._right_column_width = right_column_width
        self.contentbox = gtk.VBox(False, 6)
        label = labels.BoldLabel(header)
        label.set_alignment(0, 0.5)
        hbox = gtk.HBox(False, 0)
        hbox.pack_start(gtk.HBox(), False, False, 6)
        hbox.pack_start(self.contentbox)
        self.pack_start(label, False, False)
        self.pack_start(hbox, False, False, 6)

    def new_split_vboxes(self):
        """Return two new VBoxes that are automatically put in the section
        after the previously added items. The right one has a width request
        equal to the right_column_width value passed to the class contructor,
        in order to make it easy for  all "right column items" in a page to
        line up nicely.
        """
        left_box = gtk.VBox(False, 6)
        right_box = gtk.VBox(False, 6)

        if self._right_column_width != None:
            right_box.set_size_request(self._right_column_width, -1)

        hbox = gtk.HBox(False, 12)
        hbox.pack_start(left_box)
        hbox.pack_start(right_box, False, False)
        self.contentbox.pack_start(hbox)
        return left_box, right_box

# vim: expandtab:sw=4:ts=4

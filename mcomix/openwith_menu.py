""" openwith_menu.py - Menu shell for the Open with... menu. """

import gtk

from mcomix import openwith


class OpenWithMenu(gtk.Menu):
    def __init__(self, ui, window):
        """ Constructor. """
        gtk.Menu.__init__(self)

        self._window = window
        
        actiongroup = gtk.ActionGroup('mcomix-openwith')
        actiongroup.add_actions([
            ('edit_commands', gtk.STOCK_EDIT, _('_Edit'),
             None, None, self._edit_commands)])

        action = actiongroup.get_action('edit_commands')
        action.set_accel_group(ui.get_accel_group())
        self.edit_button = action.create_menu_item()
        self.append(self.edit_button)

        self.show_all()

    def _edit_commands(self, *args):
        """ When clicked, opens the command editor to set up the menu. """
        openwith.OpenWithEditor(self._window)

# vim: expandtab:sw=4:ts=4

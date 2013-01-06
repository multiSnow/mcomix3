""" openwith_menu.py - Menu shell for the Open with... menu. """

import gtk

from mcomix import openwith


class OpenWithMenu(gtk.Menu):
    def __init__(self, ui, window):
        """ Constructor. """
        gtk.Menu.__init__(self)

        self._window = window
        self._openwith_manager = openwith.OpenWithManager()
        self._edit_diag = None
        
        actiongroup = gtk.ActionGroup('mcomix-openwith')
        actiongroup.add_actions([
            ('edit_commands', gtk.STOCK_EDIT, _('_Edit'),
             None, None, self._edit_commands)])

        action = actiongroup.get_action('edit_commands')
        action.set_accel_group(ui.get_accel_group())
        self.edit_button = action.create_menu_item()
        self.append(self.edit_button)

        self._construct_menu()

        self.show_all()

    def _construct_menu(self):
        """ Build the menu entries from scratch. """
        for item in self.get_children():
            if item != self.edit_button:
                self.remove(item)

        commandlist = self._openwith_manager.get_commands()

        if len(commandlist) > 0:
            separator = gtk.SeparatorMenuItem()
            separator.show()
            self.prepend(separator)

        for command in reversed(commandlist):
            menuitem = gtk.MenuItem(command.get_label())
            menuitem.connect('activate', self._commandmenu_clicked,
                    command.get_command())
            menuitem.show()
            self.prepend(menuitem)

    def _commandmenu_clicked(self, menuitem, cmd):
        """ Execute the command associated with the clicked menu. """
        command = openwith.OpenWithCommand(None, cmd)
        command.execute(self._window)

    def _edit_commands(self, *args):
        """ When clicked, opens the command editor to set up the menu. Make
        sure the dialog isn't opened more than once. """
        if not self._edit_diag:
            self._edit_diag = openwith.OpenWithEditor(self._window,
                    self._openwith_manager)
            self._edit_diag.connect_after('response', self._dialog_closed)

        self._edit_diag.show_all()
        self._edit_diag.present()

    def _dialog_closed(self, *args):
        """ Watch for the dialog getting closed and unset the local instance. """
        self._edit_diag.destroy()
        self._edit_diag = None
        self._construct_menu()

# vim: expandtab:sw=4:ts=4

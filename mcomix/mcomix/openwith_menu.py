''' openwith_menu.py - Menu shell for the Open with... menu. '''

from gi.repository import Gtk

from mcomix import openwith

# Reference to the OpenWith command manager
_openwith_manager = openwith.OpenWithManager()
# Reference to the edit dialog (to keep only one instance)
_openwith_edit_diag = None

class OpenWithMenu(Gtk.Menu):
    def __init__(self, ui, window):
        ''' Constructor. '''
        super(OpenWithMenu, self).__init__()

        self._window = window
        self._openwith_manager = _openwith_manager

        actiongroup = Gtk.ActionGroup(name='mcomix-openwith')
        actiongroup.add_actions([
            ('edit_commands', Gtk.STOCK_EDIT, _('_Edit commands'),
             None, None, self._edit_commands)])

        action = actiongroup.get_action('edit_commands')
        action.set_accel_group(ui.get_accel_group())
        self.edit_button = action.create_menu_item()
        self.append(self.edit_button)

        self._construct_menu()

        self._window.filehandler.file_opened += self._set_sensitivity
        self._window.filehandler.file_closed += self._set_sensitivity
        self._openwith_manager.set_commands += self._construct_menu

        self.show_all()

    def _construct_menu(self, *args):
        ''' Build the menu entries from scratch. '''
        for item in self.get_children():
            if item != self.edit_button:
                self.remove(item)

        commandlist = self._openwith_manager.get_commands()

        if len(commandlist) > 0:
            separator = Gtk.SeparatorMenuItem()
            separator.show()
            self.prepend(separator)

        for command in reversed(commandlist):
            if not command.is_separator():
                menuitem = Gtk.MenuItem(label=command.get_label())
                menuitem.connect('activate', self._commandmenu_clicked,
                        command.get_command(), command.get_label(),
                        command.get_cwd(), command.is_disabled_for_archives())
            else:
                menuitem = Gtk.SeparatorMenuItem()

            menuitem.show()
            self.prepend(menuitem)

        self._set_sensitivity()

    def _set_sensitivity(self):
        ''' Enables or disables menu items depending on files being loaded. '''
        sensitive = self._window.filehandler.file_loaded
        for item in self.get_children():
            if item != self.edit_button:
                item.set_sensitive(sensitive)

    def _commandmenu_clicked(self, menuitem, cmd, label, cwd, disabled_in_archives):
        ''' Execute the command associated with the clicked menu. '''
        command = openwith.OpenWithCommand(label, cmd, cwd, disabled_in_archives)
        command.execute(self._window)

    def _edit_commands(self, *args):
        ''' When clicked, opens the command editor to set up the menu. Make
        sure the dialog isn't opened more than once. '''
        global _openwith_edit_diag
        if not _openwith_edit_diag:
            _openwith_edit_diag = openwith.OpenWithEditor(self._window,
                    self._openwith_manager)
            _openwith_edit_diag.connect_after('response', self._dialog_closed)

        _openwith_edit_diag.show_all()
        _openwith_edit_diag.present()

    def _dialog_closed(self, *args):
        ''' Watch for the dialog getting closed and unset the local instance. '''
        global _openwith_edit_diag
        _openwith_edit_diag.destroy()
        _openwith_edit_diag = None

# vim: expandtab:sw=4:ts=4

""" Simple extension of Gtk.MessageDialog for consistent formating. Also
    supports remembering the dialog result.
"""

from gi.repository import Gtk

from mcomix.preferences import prefs


class MessageDialog(Gtk.MessageDialog):

    def __init__(self, parent=None, flags=0, type=0, buttons=0):
        """ Creates a dialog window.
        @param parent: Parent window
        @param flags: Dialog flags
        @param type: Dialog icon/type
        @param buttons: Dialog buttons. Can only be a predefined BUTTONS_XXX constant.
        """
        if parent is None:
            # Fix "mapped without a transient parent" Gtk warning.
            from mcomix import main
            parent = main.main_window()
        super(MessageDialog, self).__init__(parent=parent, flags=flags, type=type, buttons=buttons)

        #: Unique dialog identifier (for storing 'Do not ask again')
        self.dialog_id = None
        #: List of response IDs that should be remembered
        self.choices = []
        #: Automatically destroy dialog after run?
        self.auto_destroy = True

        self.remember_checkbox = Gtk.CheckButton(_('Do not ask again.'))
        self.remember_checkbox.set_no_show_all(True)
        self.remember_checkbox.set_can_focus(False)
        self.get_message_area().pack_end(self.remember_checkbox, True, True, 6)

    def set_text(self, primary, secondary=None):
        """ Formats the dialog's text fields.
        @param primary: Main text.
        @param secondary: Descriptive text.
        """
        if primary:
            self.set_markup('<span weight="bold" size="larger">' +
                primary + '</span>')
        if secondary:
            self.format_secondary_markup(secondary)

    def should_remember_choice(self):
        """ Returns True when the dialog choice should be remembered. """
        return self.remember_checkbox.get_active()

    def set_should_remember_choice(self, dialog_id, choices):
        """ This method enables the 'Do not ask again' checkbox.
        @param dialog_id: Unique identifier for the dialog (a string).
        @param choices: List of response IDs that should be remembered
        """
        self.remember_checkbox.show()
        self.dialog_id = dialog_id
        self.choices = [int(choice) for choice in choices]

    def set_auto_destroy(self, auto_destroy):
        """ Determines if the dialog should automatically destroy itself
        after run(). """
        self.auto_destroy = auto_destroy

    def run(self):
        """ Makes the dialog visible and waits for a result. Also destroys
        the dialog after the result has been returned. """

        if self.dialog_id in prefs['stored dialog choices']:
            self.destroy()
            return prefs['stored dialog choices'][self.dialog_id]
        else:
            self.show_all()
            # Prevent checkbox from grabbing focus by only enabling it after show
            self.remember_checkbox.set_can_focus(True)
            result = super(MessageDialog, self).run()

            if (self.should_remember_choice() and int(result) in self.choices):
                prefs['stored dialog choices'][self.dialog_id] = int(result)

            if self.auto_destroy:
                self.destroy()
            return result


# vim: expandtab:sw=4:ts=4

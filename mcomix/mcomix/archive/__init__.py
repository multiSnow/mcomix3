# -*- coding: utf-8 -*-

from gi.repository import Gtk

from mcomix import message_dialog

def ask_for_password(archive):
    """ Openes an input dialog to ask for a password. Returns either
    an Unicode string (the password), or None."""
    dialog = message_dialog.MessageDialog(None, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL)
    dialog.set_text(
        _("The archive is password-protected:"),
        archive + '\n\n' +
        ("Please enter the password to continue:"))
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.set_auto_destroy(False)

    password_box = Gtk.Entry()
    password_box.set_visibility(False)
    password_box.set_activates_default(True)
    dialog.get_content_area().pack_end(password_box, True, True, 0)
    dialog.set_focus(password_box)

    result = dialog.run()
    password = password_box.get_text()
    dialog.destroy()

    if result == Gtk.ResponseType.OK and password:
        return password.decode('utf-8')
    else:
        return None

# vim: expandtab:sw=4:ts=4

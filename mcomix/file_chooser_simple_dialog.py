"""file_chooser_simple_dialog.py - Custom FileChooserDialog implementations."""

import gtk

from mcomix import file_chooser_base_dialog

class SimpleFileChooserDialog(file_chooser_base_dialog._BaseFileChooserDialog):

    """A simple filechooser dialog that is designed to be used with the
    gtk.Dialog.run() method. The <action> dictates what type of filechooser
    dialog we want (i.e. save or open). If the type is an open-dialog, we
    use multiple selection by default.
    """

    def __init__(self, action=gtk.FILE_CHOOSER_ACTION_OPEN):
        super(SimpleFileChooserDialog, self).__init__(action)
        if action == gtk.FILE_CHOOSER_ACTION_OPEN:
            self.filechooser.set_select_multiple(True)
        self._paths = None

    def get_paths(self):
        """Return the selected paths. To be called after run() has returned
        a response.
        """
        return self._paths

    def files_chosen(self, paths):
        self._paths = paths

# vim: expandtab:sw=4:ts=4

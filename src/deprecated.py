"""deprecated.py - Clean up deprecated MComix files."""

import os
import shutil
import gtk
import constants

class _CleanerDialog(gtk.MessageDialog):

    def __init__(self, window, paths):
        gtk.MessageDialog.__init__(self, window, 0, gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_YES_NO,
            _('There are deprecated files left on your computer.'))

        self._paths = paths
        self.connect('response', self._response)

        self.format_secondary_text(
            _('Some old files (that were used for storing preferences, the library, bookmarks etc. for older versions of MComix) were found on your computer. If you do not plan on using the older versions of MComix again, you should remove these files in order to save some disk space. Do you want these files to be removed for you now?'))
    
    def _response(self, dialog, response):
        if response == gtk.RESPONSE_YES:

            for path in self._paths:

                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)

                except Exception:
                    print _('! Could not remove'), path

        self.destroy()


def move_files_to_xdg_dirs():
    """Move config and data files from the old MComix directory (~/.mcomix/)
    to the XDG config and data directories.
    """
    old_dir = os.path.join(constants.HOME_DIR, '.mcomix')
    
    to_be_moved = (
        ('preferences.pickle', constants.CONFIG_DIR),
        ('bookmarks.pickle', constants.DATA_DIR),
        ('library.db', constants.DATA_DIR),
        ('library_covers', constants.DATA_DIR))

    for name, new_dir in to_be_moved:
        if os.path.exists(os.path.join(old_dir, name)) and not os.path.exists(
                os.path.join(new_dir, name)):

            try:
                os.rename(os.path.join(old_dir, name),
                    os.path.join(new_dir, name))

            except Exception:
                pass

def check_for_deprecated_files(window):
    """Check for a number of deprecated files created by older versions of
    MComix. If any are found, we ask the user through a dilaog if they
    should be removed.
    """
    deprecated = (
        os.path.join(constants.HOME_DIR, '.mcomixrc'),
        os.path.join(constants.HOME_DIR, '.mcomix'))
    found = []

    for path in deprecated:
        if os.path.exists(path):
            found.append(path)

    if found:
        dialog = _CleanerDialog(window, found)
        dialog.show_all()

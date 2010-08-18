"""dialog_handler.py - Takes care of opening and closing and destroying of simple dialog windows.
   Dialog windows should only be taken care of here if they are windows that need to display
   information and then exit with no added functionality inbetween.
"""

import about_dialog
import comment_dialog
import properties_dialog

dialog_windows = {}
dialog_windows[ 'about-dialog' ] = [None, about_dialog._AboutDialog]
dialog_windows[ 'comments-dialog' ] = [None, comment_dialog._CommentsDialog]
dialog_windows[ 'properties-dialog' ] = [None, properties_dialog._PropertiesDialog]

def open_dialog(action, window, name_of_dialog):
    """Create and display the given dialog."""
    
    _dialog = dialog_windows[ name_of_dialog ]

    # if the dialog window is not created then create the window
    # and connect the _close_dialog action to the dialog window
    if _dialog[0] is None:
        dialog_windows[ name_of_dialog ][0] = _dialog[1](window)
        dialog_windows[ name_of_dialog ][0].connect('response', _close_dialog, name_of_dialog)
    else:
        # if the dialog window already exists bring it to the forefront of the screen
        _dialog[0].present()

def _close_dialog(action, exit_response, name_of_dialog):

    _dialog = dialog_windows[ name_of_dialog ]
    
    # if the dialog window exists then destroy it
    if _dialog[0] is not None:
        _dialog[0].destroy()
        _dialog[0] = None


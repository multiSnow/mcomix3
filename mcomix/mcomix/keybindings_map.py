# Bindings defined in this dictionary will appear in the configuration dialog.
# If 'group' is None, the binding cannot be modified from the preferences dialog.
BINDING_INFO = {
    # Navigation between pages, archives, directories
    'previous_page': {'title': _('Previous page'),
                      'group': _('Navigation')},
    'next_page': {'title': _('Next page'),
                  'group': _('Navigation')},
    'previous_page_ff': {'title': _('Back ten pages'),
                         'group': _('Navigation')},
    'next_page_ff': {'title': _('Forward ten pages'),
                     'group': _('Navigation')},
    'previous_page_dynamic': {'title': _('Previous page (dynamic)'),
                              'group': _('Navigation')},
    'next_page_dynamic': {'title': _('Next page (dynamic)'),
                          'group': _('Navigation')},
    'previous_page_singlestep': {'title': _('Previous page (always one page)'),
                                 'group': _('Navigation')},
    'next_page_singlestep': {'title': _('Next page (always one page)'),
                             'group': _('Navigation')},

    'first_page': {'title': _('First page'),
                   'group': _('Navigation')},
    'last_page': {'title': _('Last page'),
                  'group': _('Navigation')},
    'go_to': {'title': _('Go to page'),
              'group': _('Navigation')},

    'next_archive': {'title': _('Next archive'),
                     'group': _('Navigation')},
    'previous_archive': {'title': _('Previous archive'),
                         'group': _('Navigation')},
    'next_directory': {'title': _('Next directory'),
                       'group': _('Navigation')},
    'previous_directory': {'title': _('Previous directory'),
                           'group': _('Navigation')},

    # Scrolling
    'scroll_left_bottom': {'title': _('Scroll to bottom left'),
                           'group': _('Scroll')},
    'scroll_middle_bottom': {'title': _('Scroll to bottom center'),
                             'group': _('Scroll')},
    'scroll_right_bottom': {'title': _('Scroll to bottom right'),
                            'group': _('Scroll')},

    'scroll_left_middle': {'title': _('Scroll to middle left'),
                           'group': _('Scroll')},
    'scroll_middle': {'title': _('Scroll to center'),
                      'group': _('Scroll')},
    'scroll_right_middle': {'title': _('Scroll to middle right'),
                            'group': _('Scroll')},

    'scroll_left_top': {'title': _('Scroll to top left'),
                        'group': _('Scroll')},
    'scroll_middle_top': {'title': _('Scroll to top center'),
                          'group': _('Scroll')},
    'scroll_right_top': {'title': _('Scroll to top right'),
                         'group': _('Scroll')},

    'scroll_down': {'title': _('Scroll down'),
                    'group': _('Scroll')},
    'scroll_up': {'title': _('Scroll up'),
                  'group': _('Scroll')},
    'scroll_right': {'title': _('Scroll right'),
                     'group': _('Scroll')},
    'scroll_left': {'title': _('Scroll left'),
                    'group': _('Scroll')},

    'smart_scroll_up': {'title': _('Smart scroll up'),
                        'group': _('Scroll')},
    'smart_scroll_down': {'title': _('Smart scroll down'),
                          'group': _('Scroll')},

    # View
    'zoom_in': {'title': _('Zoom in'),
                'group': _('Zoom')},
    'zoom_out': {'title': _('Zoom out'),
                 'group': _('Zoom')},
    'zoom_original': {'title': _('Normal size'),
                      'group': _('Zoom')},

    'keep_transformation': {'title': _('Keep transformation'),
                            'group': _('Transformation')},
    'rotate_90': {'title': _('Rotate 90 degrees CW'),
                  'group': _('Transformation')},
    'rotate_180': {'title': _('Rotate 180 degrees'),
                   'group': _('Transformation')},
    'rotate_270': {'title': _('Rotate 90 degrees CCW'),
                   'group': _('Transformation')},
    'flip_horiz': {'title': _('Flip horizontally'),
                   'group': _('Transformation')},
    'flip_vert': {'title': _('Flip vertically'),
                  'group': _('Transformation')},
    'no_autorotation': {'title': _('Never autorotate'),
                        'group': _('Transformation')},

    'rotate_90_width': {'title': _('Rotate 90 degrees CW'),
                        'group': _('Autorotate by width')},
    'rotate_270_width': {'title': _('Rotate 90 degrees CCW'),
                         'group': _('Autorotate by width')},
    'rotate_90_height': {'title': _('Rotate 90 degrees CW'),
                         'group': _('Autorotate by height')},
    'rotate_270_height': {'title': _('Rotate 90 degrees CCW'),
                          'group': _('Autorotate by height')},

    'double_page': {'title': _('Double page mode'),
                    'group': _('View mode')},
    'manga_mode': {'title': _('Manga mode'),
                   'group': _('View mode')},
    'invert_scroll': {'title': _('Invert smart scroll'),
                      'group': _('View mode')},

    'lens': {'title': _('Magnifying lens'),
             'group': _('View mode')},
    'stretch': {'title': _('Stretch small images'),
                'group': _('View mode')},

    'best_fit_mode': {'title': _('Best fit mode'),
                      'group': _('View mode')},
    'fit_width_mode': {'title': _('Fit width mode'),
                       'group': _('View mode')},
    'fit_height_mode': {'title': _('Fit height mode'),
                        'group': _('View mode')},
    'fit_size_mode': {'title': _('Fit size mode'),
                      'group': _('View mode')},
    'fit_manual_mode': {'title': _('Manual zoom mode'),
                        'group': _('View mode')},

    # General UI
    'exit_fullscreen': {'title': _('Exit from fullscreen'),
                        'group': _('User interface')},

    'osd_panel': {'title': _('Show OSD panel'),
                  'group': _('User interface')},
    'minimize': {'title': _('Minimize'),
                 'group': _('User interface')},
    'fullscreen': {'title': _('Fullscreen'),
                   'group': _('User interface')},
    'toolbar': {'title': _('Show/hide toolbar'),
                'group': _('User interface')},
    'menubar': {'title': _('Show/hide menubar'),
                'group': _('User interface')},
    'statusbar': {'title': _('Show/hide statusbar'),
                  'group': _('User interface')},
    'scrollbar': {'title': _('Show/hide scrollbars'),
                  'group': _('User interface')},
    'thumbnails': {'title': _('Thumbnails'),
                   'group': _('User interface')},
    'hide_all': {'title': _('Show/hide all'),
                 'group': _('User interface')},
    'slideshow': {'title': _('Start slideshow'),
                  'group': _('User interface')},

    # File operations
    'delete': {'title': _('Delete'),
               'group': _('File')},
    'trash': {'title': _('trash'),
               'group': _('File')},
    'refresh_archive': {'title': _('Refresh'),
                        'group': _('File')},
    'close': {'title': _('Close'),
              'group': _('File')},
    'quit': {'title': _('Quit'),
             'group': _('File')},
    'save_and_quit': {'title': _('Save and quit'),
                      'group': _('File')},
    'extract_page': {'title': _('Save As'),
                     'group': _('File')},

    'comments': {'title': _('Archive comments'),
                 'group': _('File')},
    'properties': {'title': _('Properties'),
                   'group': _('File')},
    'preferences': {'title': _('Preferences'),
                    'group': _('File')},

    'edit_archive': {'title': _('Edit archive'),
                     'group': _('File')},
    'open': {'title': _('Open'),
             'group': _('File')},
    'enhance_image': {'title': _('Enhance image'),
                      'group': _('File')},
    'library': {'title': _('Library'),
                'group': _('File')},
}

# Generate 9 entries for executing command 1 to 9
for i in range(1, 10):
    BINDING_INFO['execute_command_%d' %i] = {
            'title' : _('Execute external command') + ' (%d)' % i,
            'group' : _('External commands')
    }

DEFAULT_BINDINGS = {
    # Navigation between pages, archives, directories
    'previous_page':['Page_Up','KP_Page_Up','BackSpace'],
    'next_page':['Page_Down','KP_Page_Down'],
    'previous_page_singlestep':['<Ctrl>Page_Up','<Ctrl>KP_Page_Up','<Ctrl>BackSpace'],
    'next_page_singlestep':['<Ctrl>Page_Down','<Ctrl>KP_Page_Down'],
    'previous_page_dynamic':['<Mod1>Left'],
    'next_page_dynamic':['<Mod1>Right'],
    'previous_page_ff':['<Shift>Page_Up','<Shift>KP_Page_Up','<Shift>BackSpace','<Shift><Mod1>Left'],
    'next_page_ff':['<Shift>Page_Down','<Shift>KP_Page_Down','<Shift><Mod1>Right'],

    'first_page':['Home','KP_Home'],
    'last_page':['End','KP_End'],
    'go_to':['G'],

    'next_archive':['<control><shift>N'],
    'previous_archive':['<control><shift>P'],
    'next_directory':['<control>N'],
    'previous_directory':['<control>P'],

    # Scrolling
    # Numpad (without numlock) aligns the image depending on the key.
    'scroll_left_bottom':['KP_1'],
    'scroll_middle_bottom':['KP_2'],
    'scroll_right_bottom':['KP_3'],

    'scroll_left_middle':['KP_4'],
    'scroll_middle':['KP_5'],
    'scroll_right_middle':['KP_6'],

    'scroll_left_top':['KP_7'],
    'scroll_middle_top':['KP_8'],
    'scroll_right_top':['KP_9'],

    # Arrow keys scroll the image
    'scroll_down':['Down','KP_Down'],
    'scroll_up':['Up','KP_Up'],
    'scroll_right':['Right','KP_Right'],
    'scroll_left':['Left','KP_Left'],

    # Space key scrolls down a percentage of the window height or the
    # image height at a time. When at the bottom it flips to the next
    # page.
    #
    # It also has a "smart scrolling mode" in which we try to follow
    # the flow of the comic.
    #
    # If Shift is pressed we should backtrack instead.
    'smart_scroll_up':['<Shift>space'],
    'smart_scroll_down':['space'],

    # View
    'zoom_in':['plus','KP_Add','equal'],
    'zoom_out':['minus','KP_Subtract'],
    # Zoom out is already defined as GTK menu hotkey
    'zoom_original':['<Control>0','KP_0'],

    'keep_transformation':['k'],
    'rotate_90':['r'],
    'rotate_270':['<Shift>r'],
    'rotate_180':[],
    'flip_horiz':[],
    'flip_vert':[],
    'no_autorotation':[],

    'rotate_90_width':[],
    'rotate_270_width':[],
    'rotate_90_height':[],
    'rotate_270_height':[],

    'double_page':['d'],
    'manga_mode':['m'],
    'invert_scroll':['x'],

    'lens':['l'],
    'stretch':['y'],

    'best_fit_mode':['b'],
    'fit_width_mode':['w'],
    'fit_height_mode':['h'],
    'fit_size_mode':['s'],
    'fit_manual_mode':['a'],

    # General UI
    'exit_fullscreen':['Escape'],

    'osd_panel':['Tab'],
    'minimize':['n'],
    'fullscreen':['f','F11'],
    'toolbar':[],
    'menubar':['<Control>M'],
    'statusbar':[],
    'scrollbar':[],
    'thumbnails':['F9'],
    'hide_all':['i'],
    'slideshow':['<Control>S'],

    # File operations
    'trash':['Delete'],
    'delete':['<Shift>Delete'],
    'refresh_archive':['<control><shift>R'],
    'close':['<Control>W'],
    'quit':['<Control>Q'],
    'save_and_quit':['<Control><shift>q'],
    'extract_page':['<Control><Shift>s'],

    'comments':['c'],
    'properties':['<Alt>Return'],
    'preferences':['F12'],

    'edit_archive':[],
    'open':['<Control>O'],
    'enhance_image':['e'],
    'library':['<Control>L'],
}

# Execute external command. Bind keys from 1 to 9 to commands 1 to 9.
for i in range(1, 10):
    DEFAULT_BINDINGS['execute_command_%d' % i] = [str(i)]

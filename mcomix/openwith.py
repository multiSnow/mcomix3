""" openwith.py - Logic and storage for Open with... commands. """
import gtk

from mcomix.preferences import prefs


class OpenWithManager(object):
    def __init__(self):
        """ Constructor. """
        pass


    def get_commands(self):
        return [OpenWithCommand(label, command)
                for label, command in prefs['openwith commands']]

class OpenWithCommand(object):
    def __init__(self, label, command):
        self.label = label
        self.command = command
    
    def get_label(self):
        return self.label

    def get_command(self):
        return self.command

    def execute(self, window):
        pass

class OpenWithEditor(gtk.Dialog):
    def __init__(self, window):
        gtk.Dialog.__init__(self, _('Edit external commands'), parent=window)
        self._window = window

        self._command_tree = gtk.TreeView()
        self._command_tree.set_headers_visible(True)
        self._command_tree.append_column(gtk.TreeViewColumn('Label'))
        self._command_tree.append_column(gtk.TreeViewColumn('Command'))
        self._add_button = gtk.Button(stock=gtk.STOCK_ADD)
        self._remove_button = gtk.Button(stock=gtk.STOCK_REMOVE)
        self._up_button = gtk.Button(stock=gtk.STOCK_GO_UP)
        self._down_button = gtk.Button(stock=gtk.STOCK_GO_DOWN)
        self._info_label = gtk.Label()
        self._info_label.set_markup(
            '<b>' + _('Variables:') + '</b>\n' +
            _('<b>%f</b> - Filename') + '\n' +
            _('<b>%d</b> - Directory') + '\n')
        self._info_label.set_alignment(0, 0)
        self._test_button = gtk.Button(_('_Test command'))
        self._test_field = gtk.Entry()

        self._layout()
        self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.set_default_response(gtk.RESPONSE_CLOSE)

        self.connect('response', self._response)

        self.resize(600, 300)
        self.show_all()

    def _layout(self):
        """ Create and lay out UI components. """

        upperbox = gtk.HBox()
        self.get_content_area().pack_start(upperbox, padding=4)

        buttonbox = gtk.VBox()
        buttonbox.pack_start(self._add_button, False)
        buttonbox.pack_start(self._remove_button, False)
        buttonbox.pack_start(self._up_button, False)
        buttonbox.pack_start(self._down_button, False)
        buttonbox.pack_end(self._info_label, padding=6)
        upperbox.pack_start(self._command_tree, padding=4)
        upperbox.pack_end(buttonbox, False, padding=4)
        
        self.get_action_area().expand = True
        self.get_action_area().pack_start(self._test_field, True, True)
        self.get_action_area().pack_start(self._test_button, False)

    def _response(self, dialog, response):
        if response == gtk.RESPONSE_CLOSE:
            self.destroy()

# vim: expandtab:sw=4:ts=4

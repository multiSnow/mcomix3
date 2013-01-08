""" openwith.py - Logic and storage for Open with... commands. """
import os
import subprocess
import gtk
import gobject

from mcomix.preferences import prefs


class OpenWithManager(object):
    def __init__(self):
        """ Constructor. """
        pass

    def set_commands(self, cmds):
        prefs['openwith commands'] = [(cmd.get_label(), cmd.get_command())
            for cmd in cmds]

    def get_commands(self):
        return [OpenWithCommand(label, command)
                for label, command in prefs['openwith commands']]


class OpenWithException(Exception): pass


class OpenWithRunException(OpenWithException): pass


class OpenWithSyntaxException(OpenWithException): pass


class OpenWithCommand(object):
    def __init__(self, label, command):
        self.label = label
        if isinstance(command, str):
            self.command = command.decode('utf-8').strip()
        else:
            self.command = command.strip()

    def get_label(self):
        return self.label

    def get_command(self):
        return self.command

    def execute(self, window):
        """ Spawns a new process with the given executable
        and arguments. """
        try:
            # Redirect process output to null here?
            subprocess.Popen(self.parse(window))
        except Exception, e:
            text = _("Could not run command %(cmdlabel)s: %(exception)s") % \
                {'cmdlabel': self.get_label(), 'exception': unicode(e)}
            window.osd.show(text)

    def validate(self, window):
        """ Returns True only if the command passes syntactic
        checking without exception and when the first argument
        is an executable, valid file. """
        try:
            args = self.parse(window, False)
            syntax_passes = True
        except OpenWithException:
            args = []
            syntax_passes = False

        if len(args) > 0:
            executable = self._is_executable(args[0])
        else:
            executable = False

        return (syntax_passes and executable)

    def parse(self, window, check_restrictions=True):
        """ Parses the command string and replaces special characters
        with their respective variable contents. Returns a list of
        arguments.
        If check_restrictions is False, no checking will be done
        if one of the variables isn't valid in the current file context. """
        if (check_restrictions and window.filehandler.archive_type is None and
            (u'%a' in self.get_command() or u'%A' in self.get_command())):
            raise OpenWithException(_("%a and %A can only be used for archives."))
        if (check_restrictions and window.filehandler.archive_type is not None and
            (u'%o' in self.get_command() or u'%O' in self.get_command())):
            raise OpenWithException(_("%o and %O can only be used outside of archives."))

        args = self._commandline_to_arguments(self.get_command(), window)
        # Environment variables must be expanded after MComix variables,
        # as win32 will eat %% and replace it with %.
        args = [os.path.expandvars(arg) for arg in args]
        return args

    def _commandline_to_arguments(self, line, window):
        """ Parse a command line string into a list containing
        the parts to pass to Popen. The following two functions have
        been contributed by Ark <aaku@users.sf.net>. """
        result = []
        buf = u""
        quote = False
        escape = False
        for c in line:
            if escape:
                if c == u'%' or c == u'"':
                    buf += c
                else:
                    buf += self._expand_variable(c, window)
                escape = False
            elif c == u' ':
                if quote:
                    buf += c
                elif len(buf) != 0:
                    result.append(buf)
                    buf = u""
            elif c == u'"':
                if quote:
                    result.append(buf)
                    buf = u""
                    quote = False
                else:
                    quote = True
            elif c == u'%':
                escape = True
            else:
                buf += c
        if escape:
            raise OpenWithException(
                _("Incomplete escape sequence. "
                  "For a literal '%', use '%%'."))
        if len(buf) != 0:
            result.append(buf)
        return result

    def _expand_variable(self, identifier, window):
        """ Replaces variables with their respective file
        or archive path. """
        # Check for valid identifiers beforehand,
        # as this can be done even when no file is opened in filehandler.
        if identifier not in ('/', 'a', 'f', 'w', 'o', 'A', 'D', 'F', 'W', 'O'):
            raise OpenWithException(
                _("Invalid escape sequence: %s") % identifier);
        if identifier == '/':
            return os.path.sep

        # If no file is loaded, all following calls make no sense.
        if not window.filehandler.file_loaded:
            return identifier

        elif identifier == 'a':
            return window.filehandler.get_base_filename()
        elif identifier == 'f':
            return window.imagehandler.get_page_filename()
        elif identifier == 'w' or identifier == 'o':
            if window.filehandler.archive_type is None:
                return os.path.basename(
                    window.filehandler.get_path_to_base())
            else:
                return os.path.basename(
                    os.path.dirname(window.filehandler.get_path_to_base()))
        elif identifier == 'A':
            return window.filehandler.get_path_to_base()
        elif identifier == 'D':
            return os.path.normpath(os.path.dirname(window.imagehandler.get_path_to_page()))
        elif identifier == 'F':
            return os.path.normpath(window.imagehandler.get_path_to_page())
        elif identifier == 'W' or identifier == 'O':
            if window.filehandler.archive_type is None:
                return window.filehandler.get_path_to_base()
            else:
                return os.path.dirname(window.filehandler.get_path_to_base())

    def _is_executable(self, arg):
        """ Check if a name is executable. This name can be either
        a relative path, when the executable is in PATH, or an
        absolute path. """
        if os.path.isfile(arg) and os.access(arg, os.R_OK|os.X_OK):
            return True

        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe = os.path.join(path, arg)
            if os.path.isfile(exe) and os.access(exe, os.R_OK|os.X_OK):
                return True

        return False


class OpenWithEditor(gtk.Dialog):
    """ The editor for changing and creating external commands. This window
    keeps its own internal model once initialized, and will overwrite
    the external model (i.e. preferences) only when properly closed. """

    def __init__(self, window, openwithmanager):
        gtk.Dialog.__init__(self, _('Edit external commands'), parent=window)
        self.set_destroy_with_parent(True)
        self._window = window
        self._openwith = openwithmanager

        self._command_tree = gtk.TreeView()
        self._command_tree.get_selection().connect('changed', self._item_selected)
        self._add_button = gtk.Button(stock=gtk.STOCK_ADD)
        self._add_button.connect('clicked', self._add_command)
        self._remove_button = gtk.Button(stock=gtk.STOCK_REMOVE)
        self._remove_button.connect('clicked', self._remove_command)
        self._remove_button.set_sensitive(False)
        self._info_label = gtk.Label()
        self._info_label.set_markup(
            '<b>' + _('Variables') + '</b>\n' +
            '<b>%f</b> - ' + _('File name') + '\n' +
            '<b>%w</b> - ' + _('Directory name') + '\n' +
            '<b>%a</b> - ' + _('Archive name') + '\n' +
            '<b>' + _('Absolute path variables') + '</b>\n' +
            '<b>%F</b> - ' + _('File path') + '\n' +
            '<b>%W</b> - ' + _('Directory containing archive or image') + '\n' +
            '<b>%A</b> - ' + _('Archive path') + '\n' +
            '<b>%D</b> - ' + _('Directory containing (extracted) files') + '\n' +
            '<b>' + _('Miscellaneous variables') + '</b>\n' +
            '<b>%/</b> - ' + _('Backslash or slash, depending on OS') + '\n' +
            '<b>%"</b> - ' + _('Literal quote') + '\n' +
            '<b>%%</b> - ' + _('Literal % character') + '\n')
        self._info_label.set_alignment(0, 0)
        self._test_field = gtk.Entry()
        self._test_field.set_property('editable', gtk.FALSE)
        self._test_field.set_text(_('Preview area'))
        self._save_button = self.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT)
        self.set_default_response(gtk.RESPONSE_ACCEPT)

        self._layout()
        self._setup_table()

        self.connect('response', self._response)

        self.resize(600, 300)

    def save(self):
        """ Serializes the tree model into a list of OpenWithCommands
        and passes these back to the Manager object for persistance. """
        commands = self.get_commands()
        self._openwith.set_commands(commands)

    def get_commands(self):
        """ Retrieves a list of OpenWithCommand instances from
        the list model. """
        model = self._command_tree.get_model()
        iter = model.get_iter_first()
        commands = []
        while iter:
            label, command = model.get(iter, 0, 1)
            commands.append(OpenWithCommand(label, command))
            iter = model.iter_next(iter)
        return commands

    def _add_command(self, button):
        """ Add a new empty label-command line to the list. """
        self._command_tree.get_model().append((_('Command label'), _('Command')))

    def _remove_command(self, button):
        """ Removes the currently selected command from the list. """
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            model.remove(iter)

    def test_command(self):
        """ Parses the currently selected command and displays the output in the
        text box next to the button. """
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            command = OpenWithCommand(*model.get(iter, 0, 1))
            def quote_if_necessary(arg):
                if u" " in arg:
                    return u'"' + arg.replace(u'"', u'\\"') + u'"'
                else:
                    return arg
            try:
                args = map(quote_if_necessary, command.parse(self._window))
                self._test_field.set_text(" ".join(args))
            except OpenWithException, e:
                self._test_field.set_text(unicode(e))

    def _item_selected(self, selection):
        """ Enable or disable buttons that depend on an item being selected. """
        for button in (self._remove_button, ):
            button.set_sensitive(selection.count_selected_rows() > 0)

        if selection.count_selected_rows() > 0:
            self.test_command()
        else:
            self._test_field.set_text(_('Preview area'))

    def _layout(self):
        """ Create and lay out UI components. """
        upperbox = gtk.HBox()
        self.get_content_area().pack_start(upperbox, padding=4)

        buttonbox = gtk.VBox()
        buttonbox.pack_start(self._add_button, False)
        buttonbox.pack_start(self._remove_button, False)
        buttonbox.pack_end(self._info_label, padding=6)

        treebox = gtk.VBox()
        scroll_window = gtk.ScrolledWindow()
        scroll_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll_window.add(self._command_tree)
        treebox.pack_start(scroll_window, padding=4)
        treebox.pack_end(self._test_field, False)

        upperbox.pack_start(treebox, padding=4)
        upperbox.pack_end(buttonbox, False, padding=4)

    def _setup_table(self):
        """ Initializes the TreeView with settings and data. """
        for i, label in enumerate(('Label', 'Command')):
            renderer = gtk.CellRendererText()
            renderer.set_property('editable', gtk.TRUE)
            renderer.connect('edited', self._value_changed, i)
            column = gtk.TreeViewColumn(label, renderer)
            column.set_property('resizable', gtk.TRUE)
            column.set_attributes(renderer, text=i)
            self._command_tree.append_column(column)

        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        for command in self._openwith.get_commands():
            model.append((command.get_label(), command.get_command()))
        self._command_tree.set_model(model)

        self._command_tree.set_headers_visible(True)
        self._command_tree.set_reorderable(True)

    def _value_changed(self, renderer, path, new_text, column):
        """ Called when the user edits a field in the table. """
        model = self._command_tree.get_model()
        iter = model.get_iter(path)
        # Editing the model in the cellrenderercallback stops the editing
        # operation, causing GTK warnings. Delay until callback is finished.
        def delayed_set_value():
            model.set_value(iter, column, new_text)
            # Only re-validate if command column is changed
            if column == 1:
                self.test_command()
        gobject.idle_add(delayed_set_value)


    def _response(self, dialog, response):
        if response == gtk.RESPONSE_ACCEPT:
            # The Save button is only enabled if all commands are valid
            self.save()
            self.hide_all()

# vim: expandtab:sw=4:ts=4

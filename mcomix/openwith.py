""" openwith.py - Logic and storage for Open with... commands. """
import sys
import os
import re
import subprocess
import gtk
import gobject

from mcomix.preferences import prefs
from mcomix import message_dialog
from mcomix import process


class OpenWithException(Exception): pass


class OpenWithManager(object):
    def __init__(self):
        """ Constructor. """
        pass

    def set_commands(self, cmds):
        prefs['openwith commands'] = [(cmd.get_label(), cmd.get_command(), cmd.get_cwd(), cmd.is_disabled_for_archives())
            for cmd in cmds]

    def get_commands(self):
        try:
            return [OpenWithCommand(label, command, cwd, disabled_for_archives)
                    for label, command, cwd, disabled_for_archives in prefs['openwith commands']]
        except ValueError:
            # Backwards compatibility for early versions with only two parameters
            return [OpenWithCommand(label, command, u'', False)
                    for label, command in prefs['openwith commands']]


class OpenWithCommand(object):
    def __init__(self, label, command, cwd, disabled_for_archives):
        self.label = label
        if isinstance(command, str):
            self.command = command.decode('utf-8').strip()
        else:
            self.command = command.strip()
        if isinstance(cwd, str):
            self.cwd = cwd.decode('utf-8').strip()
        else:
            self.cwd = cwd.strip()

        self.disabled_for_archives = bool(disabled_for_archives)

    def get_label(self):
        return self.label

    def get_command(self):
        return self.command

    def get_cwd(self):
        return self.cwd

    def is_disabled_for_archives(self):
        return self.disabled_for_archives

    def is_separator(self):
        return bool(re.match(r'^-+$', self.get_label().strip()))

    def execute(self, window):
        """ Spawns a new process with the given executable
        and arguments. """
        if (self.is_disabled_for_archives() and
            window.filehandler.archive_type is not None):
            window.osd.show(_("'%s' is disabled for archives.") % self.get_label())
            return

        try:
            current_dir = os.getcwd()
            if self.get_cwd() and len(self.get_cwd().strip()) > 0:
                directories = self.parse(window, text=self.get_cwd())
                if self.is_valid_workdir(window):
                    os.chdir(directories[0])
                else:
                    raise OpenWithException(_('Invalid working directory.'))

            # Redirect process output to null here?
            # FIXME: Close process when finished to avoid zombie process
            args = self.parse(window)
            if sys.platform == 'win32':
                proc = process.Win32Popen(args)
            else:
                proc = subprocess.Popen(args)
            del proc
            os.chdir(current_dir)
        except Exception, e:
            text = _("Could not run command %(cmdlabel)s: %(exception)s") % \
                {'cmdlabel': self.get_label(), 'exception': unicode(e)}
            window.osd.show(text)

    def is_executable(self, window):
        """ Check if a name is executable. This name can be either
        a relative path, when the executable is in PATH, or an
        absolute path. """
        args = self.parse(window)
        if len(args) == 0:
            return False

        if self.is_valid_workdir(window):
            workdir = self.parse(window, text=self.get_cwd())[0]
        else:
            workdir = os.getcwd()

        arg = args[0]
        fullcmd = os.path.join(workdir, arg)
        if os.path.isfile(fullcmd) and os.access(fullcmd, os.R_OK|os.X_OK):
            return True

        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe = os.path.join(path, arg)
            if os.path.isfile(exe) and os.access(exe, os.R_OK|os.X_OK):
                return True

        return False

    def is_valid_workdir(self, window):
        """ Check if the working directory is valid. """
        if len(self.get_cwd().strip()) == 0:
            return True

        args = self.parse(window, text=self.get_cwd())
        if len(args) > 1:
            return False

        dir = args[0]
        if os.path.isdir(dir) and os.access(dir, os.X_OK):
            return True

        return False

    def parse(self, window, text='', check_restrictions=True):
        """ Parses the command string and replaces special characters
        with their respective variable contents. Returns a list of
        arguments.
        If check_restrictions is False, no checking will be done
        if one of the variables isn't valid in the current file context. """
        if not text:
            text = self.get_command()

        args = self._commandline_to_arguments(text, window,
            not(check_restrictions and window and window.filehandler.archive_type is None))
        # Environment variables must be expanded after MComix variables,
        # as win32 will eat %% and replace it with %.
        args = [os.path.expandvars(arg) for arg in args]
        return args

    def _commandline_to_arguments(self, line, window, archive_context):
        """ Parse a command line string into a list containing
        the parts to pass to Popen. The following two functions have
        been contributed by Ark <aaku@users.sf.net>. """
        result = []
        buf = u""
        quote = False
        escape = False
        inarg = False
        for c in line:
            if escape:
                if c == u'%' or c == u'"':
                    buf += c
                else:
                    buf += self._expand_variable(c, window, archive_context)
                escape = False
            elif c == u' ' or c == u'\t':
                if quote:
                    buf += c
                elif inarg:
                    result.append(buf)
                    buf = u""
                    inarg = False
            else:
                if c == u'"':
                    quote = not quote
                elif c == u'%':
                    escape = True
                else:
                    buf += c
                inarg = True

        if escape:
            raise OpenWithException(
                _("Incomplete escape sequence. "
                  "For a literal '%', use '%%'."))
        if quote:
            raise OpenWithException(
                _("Incomplete quote sequence. "
                  "For a literal '\"', use '%\"'."))

        if inarg:
            result.append(buf)
        return result

    def _expand_variable(self, identifier, window, archive_context):
        """ Replaces variables with their respective file
        or archive path. """

        # Skip if no file is loaded
        if not window or not window.filehandler.file_loaded:
            return '%' + identifier

        if not archive_context and identifier in (u'a', u'c', u'A', u'C'):
            raise OpenWithException(
                _("Archive-related variables can only be used for archives."))

        if identifier == u'/':
            return os.path.sep
        elif identifier == u'a':
            return window.filehandler.get_base_filename()
        elif identifier == u'd':
            return os.path.basename(os.path.dirname(window.imagehandler.get_path_to_page()))
        elif identifier == u'f':
            return window.imagehandler.get_page_filename()
        elif identifier == u'c':
            return os.path.basename(os.path.dirname(window.filehandler.get_path_to_base()))
        elif identifier == u'A':
            return window.filehandler.get_path_to_base()
        elif identifier == u'D':
            return os.path.normpath(os.path.dirname(window.imagehandler.get_path_to_page()))
        elif identifier == u'F':
            return os.path.normpath(window.imagehandler.get_path_to_page())
        elif identifier == u'C':
            return os.path.dirname(window.filehandler.get_path_to_base())
        else:
            raise OpenWithException(
                _("Invalid escape sequence: %%%s") % identifier);



class OpenWithEditor(gtk.Dialog):
    """ The editor for changing and creating external commands. This window
    keeps its own internal model once initialized, and will overwrite
    the external model (i.e. preferences) only when properly closed. """

    def __init__(self, window, openwithmanager):
        gtk.Dialog.__init__(self, _('Edit external commands'), parent=window)
        self.set_destroy_with_parent(True)
        self._window = window
        self._openwith = openwithmanager
        self._changed = False

        self._command_tree = gtk.TreeView()
        self._command_tree.get_selection().connect('changed', self._item_selected)
        self._add_button = gtk.Button(stock=gtk.STOCK_ADD)
        self._add_button.connect('clicked', self._add_command)
        self._add_sep_button = gtk.Button(_('Add _separator'))
        self._add_sep_button.connect('clicked', self._add_sep_command)
        self._remove_button = gtk.Button(stock=gtk.STOCK_REMOVE)
        self._remove_button.connect('clicked', self._remove_command)
        self._remove_button.set_sensitive(False)
        self._up_button = gtk.Button(stock=gtk.STOCK_GO_UP)
        self._up_button.connect('clicked', self._up_command)
        self._up_button.set_sensitive(False)
        self._down_button = gtk.Button(stock=gtk.STOCK_GO_DOWN)
        self._down_button.connect('clicked', self._down_command)
        self._down_button.set_sensitive(False)
        self._run_button = gtk.Button(_('Run _command'))
        self._run_button.connect('clicked', self._run_command)
        self._run_button.set_sensitive(False)
        self._info_label = gtk.Label()
        self._info_label.set_markup(
            '<b>' + _('Image-related variables') + '</b>\n' +
            '<b>%F</b> - ' + _('File path') + '\n' +
            '<b>%D</b> - ' + _('Image directory path') + '\n' +
            '<b>%f</b> - ' + _('File name') + '\n' +
            '<b>%d</b> - ' + _('Image directory name') + '\n' +
            '<b>' + _('Archive-related variables') + '</b>\n' +
            '<b>%A</b> - ' + _('Archive path') + '\n' +
            '<b>%C</b> - ' + _("Archive's directory path") + '\n' +
            '<b>%a</b> - ' + _('Archive name') + '\n' +
            '<b>%c</b> - ' + _("Archive's directory name") + '\n' +
            '<b>' + _('Miscellaneous variables') + '</b>\n' +
            '<b>%/</b> - ' + _('Backslash or slash, depending on OS') + '\n' +
            '<b>%"</b> - ' + _('Literal quote') + '\n' +
            '<b>%%</b> - ' + _('Literal % character') + '\n')
        self._info_label.set_alignment(0, 0)
        self._test_field = gtk.Entry()
        self._test_field.set_property('editable', gtk.FALSE)
        self._exec_label = gtk.Label()
        self._exec_label.set_alignment(0, 0)
        self._save_button = self.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_ACCEPT)
        self.set_default_response(gtk.RESPONSE_ACCEPT)

        self._layout()
        self._setup_table()

        self.connect('response', self._response)
        self._window.draw_image += lambda *args, **kwargs: self.test_command()
        self._window.filehandler.file_opened += self.test_command
        self._window.filehandler.close_file += lambda *args: self.test_command()

        self.resize(800, 300)

    def save(self):
        """ Serializes the tree model into a list of OpenWithCommands
        and passes these back to the Manager object for persistance. """
        commands = self.get_commands()
        self._openwith.set_commands(commands)
        self._changed = False

    def get_commands(self):
        """ Retrieves a list of OpenWithCommand instances from
        the list model. """
        model = self._command_tree.get_model()
        iter = model.get_iter_first()
        commands = []
        while iter:
            label, command, cwd, disabled_for_archives = model.get(iter, 0, 1, 2, 3)
            commands.append(OpenWithCommand(label, command, cwd, disabled_for_archives))
            iter = model.iter_next(iter)
        return commands

    def get_command(self):
        """ Retrieves the selected command object. """
        selection = self._command_tree.get_selection()
        if not selection:
            return None

        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            command = OpenWithCommand(*model.get(iter, 0, 1, 2, 3))
            return command
        else:
            return None

    def test_command(self):
        """ Parses the currently selected command and displays the output in the
        text box next to the button. """
        command = self.get_command()
        if not command:
            return

        # Test only if the selected field is a valid command
        if command.is_separator():
            self._test_field.set_text(_('This is a separator pseudo-command.'))
            self._exec_label.set_text('')
            return

        try:
            args = map(self._quote_if_necessary, command.parse(self._window))
            self._test_field.set_text(" ".join(args))

            if not command.is_valid_workdir(self._window):
                self._exec_label.set_text(
                    _('"%s" does not have a valid working directory.') % command.get_label())
            elif not command.is_executable(self._window):
                self._exec_label.set_text(
                    _('"%s" does not appear to have a valid executable.') % command.get_label())
            else:
                self._exec_label.set_text('')
        except OpenWithException, e:
            self._test_field.set_text(unicode(e))

    def _add_command(self, button):
        """ Add a new empty label-command line to the list. """
        self._command_tree.get_model().append((_('Command label'), '', '', gtk.FALSE, gtk.TRUE))
        self._changed = True

    def _add_sep_command(self, button):
        """ Adds a new separator line. """
        self._command_tree.get_model().append(('-', '', '', gtk.FALSE, gtk.FALSE))
        self._changed = True

    def _remove_command(self, button):
        """ Removes the currently selected command from the list. """
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            model.remove(iter)
            self._changed = True

    def _up_command(self, button):
        """ Moves the selected command up by one. """
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            path = model.get_path(iter)[0]

            if path >= 1:
                up = model.get_iter(path - 1)
                model.swap(iter, up)
            self._changed = True

    def _down_command(self, button):
        """ Moves the selected command down by one. """
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            path = model.get_path(iter)[0]

            if path < len(self.get_commands()) - 1:
                down = model.get_iter(path + 1)
                model.swap(iter, down)
            self._changed = True

    def _run_command(self, button):
        """ Executes the selected command in the current context. """
        command = self.get_command()
        if command and not command.is_separator():
            command.execute(self._window)

    def _item_selected(self, selection):
        """ Enable or disable buttons that depend on an item being selected. """
        for button in (self._remove_button, self._up_button,
                self._down_button, self._run_button):
            button.set_sensitive(selection.count_selected_rows() > 0)

        if selection.count_selected_rows() > 0:
            self.test_command()

            if self.get_command().is_separator():
                self._run_button.set_sensitive(False)
        else:
            self._test_field.set_text('')

    def _layout(self):
        """ Create and lay out UI components. """
        upperbox = gtk.HBox()
        self.get_content_area().pack_start(upperbox, padding=4)

        buttonbox = gtk.VBox()
        buttonbox.pack_start(self._add_button, False)
        buttonbox.pack_start(self._add_sep_button, False)
        buttonbox.pack_start(self._remove_button, False)
        buttonbox.pack_start(self._up_button, False)
        buttonbox.pack_start(self._down_button, False)
        buttonbox.pack_start(self._run_button, False, padding=10)
        buttonbox.pack_end(self._info_label)

        treebox = gtk.VBox()
        scroll_window = gtk.ScrolledWindow()
        scroll_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scroll_window.add(self._command_tree)
        treebox.pack_start(scroll_window, padding=4)
        preview_box = gtk.HBox()
        preview_box.pack_start(gtk.Label(_('Preview:')), False)
        preview_box.pack_start(self._test_field, padding=4)
        treebox.pack_start(preview_box, False)
        treebox.pack_start(self._exec_label, False, padding=4)

        upperbox.pack_start(treebox, padding=4)
        upperbox.pack_end(buttonbox, False, padding=4)

    def _setup_table(self):
        """ Initializes the TreeView with settings and data. """
        for i, label in enumerate((_('Label'), _('Command'), _('Working directory'))):
            renderer = gtk.CellRendererText()
            renderer.connect('edited', self._text_changed, i)
            column = gtk.TreeViewColumn(label, renderer)
            column.set_property('resizable', gtk.TRUE)
            column.set_attributes(renderer, text=i, editable=4)
            if (i == 1):
                column.set_expand(True)  # Command column should scale automatically
            self._command_tree.append_column(column)

        # The 'Disabled in archives' field is shown as toggle button
        renderer = gtk.CellRendererToggle()
        renderer.connect('toggled', self._value_changed, len(self._command_tree.get_columns()))
        column = gtk.TreeViewColumn(_('Disabled in archives'), renderer)
        column.set_attributes(renderer, active=len(self._command_tree.get_columns()), activatable=4)
        self._command_tree.append_column(column)

        # Label, command, working dir, disabled for archives, line is editable
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, 
                gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN)
        for command in self._openwith.get_commands():
            model.append((command.get_label(), command.get_command(), command.get_cwd(),
                command.is_disabled_for_archives(), not command.is_separator()))
        self._command_tree.set_model(model)

        self._command_tree.set_headers_visible(True)
        self._command_tree.set_reorderable(True)

    def _text_changed(self, renderer, path, new_text, column):
        """ Called when the user edits a field in the table. """
        # Prevent changing command to separator
        if column == 0 and re.match(r'^-+$', new_text):
            return

        model = self._command_tree.get_model()
        iter = model.get_iter(path)
        # Editing the model in the cellrenderercallback stops the editing
        # operation, causing GTK warnings. Delay until callback is finished.
        def delayed_set_value():
            old_value = model.get_value(iter, column)
            model.set_value(iter, column, new_text)
            self._changed = old_value != new_text
            self.test_command()
        gobject.idle_add(delayed_set_value)

    def _value_changed(self, renderer, path, column):
        """ Called when a toggle field is changed """
        model = self._command_tree.get_model()
        iter = model.get_iter(path)
        # Editing the model in the cellrenderercallback stops the editing
        # operation, causing GTK warnings. Delay until callback is finished.
        def delayed_set_value():
            value = not renderer.get_active()
            model.set_value(iter, column, value)
            self._changed = True

        gobject.idle_add(delayed_set_value)

    def _response(self, dialog, response):
        if response == gtk.RESPONSE_ACCEPT:
            # The Save button is only enabled if all commands are valid
            self.save()
            self.hide_all()
        else:
            if self._changed:
                confirm_diag = message_dialog.MessageDialog(self, gtk.DIALOG_MODAL,
                    gtk.MESSAGE_INFO, gtk.BUTTONS_YES_NO)
                confirm_diag.set_text(_('Save changes to commands?'),
                    _('You have made changes to the list of external commands that '
                      'have not been saved yet. Press "Yes" to save all changes, '
                      'or "No" to discard them.'))
                response = confirm_diag.run()

                if response == gtk.RESPONSE_YES:
                    self.save()

    def _quote_if_necessary(self, arg):
        """ Quotes a command line argument if necessary. """
        if arg == u"":
            return u'""'
        if sys.platform == 'win32':
            # based on http://msdn.microsoft.com/en-us/library/17w5ykft%28v=vs.85%29.aspx
            backslash_counter = 0
            needs_quoting = False
            result = u""
            for c in arg:
                if c == u'\\':
                    backslash_counter += 1
                else:
                    if c == u'\"':
                        result += u'\\' * (2 * backslash_counter + 1)
                    else:
                        result += u'\\' * backslash_counter
                    backslash_counter = 0
                    result += c
                if c == u' ':
                    needs_quoting = True

            if needs_quoting:
                result += u'\\' * (2 * backslash_counter)
                result = u'"' + result + u'"'
            else:
                result += u'\\' * backslash_counter
            return result
        else:
            # simplified version of
            # http://www.gnu.org/software/bash/manual/bashref.html#Double-Quotes
            arg = arg.replace(u'\\', u'\\\\')
            arg = arg.replace(u'"', u'\\"')
            if u" " in arg:
                return u'"' + arg + u'"'
            return arg
# vim: expandtab:sw=4:ts=4

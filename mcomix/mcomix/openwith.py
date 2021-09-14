''' openwith.py - Logic and storage for Open with... commands. '''
import os
import re
import shlex
import sys

from gi.repository import Gtk
from gi.repository import GLib, GObject

from mcomix.preferences import prefs
from mcomix import message_dialog
from mcomix import process
from mcomix import callback


DEBUGGING_CONTEXT, NO_FILE_CONTEXT, IMAGE_FILE_CONTEXT, ARCHIVE_CONTEXT = -1, 0, 1, 2

class OpenWithException(Exception): pass


class OpenWithManager(object):
    def __init__(self):
        ''' Constructor. '''
        pass

    @callback.Callback
    def set_commands(self, cmds):
        prefs['external commands'] = [
            (cmd.get_label(), cmd.get_command(),
             cmd.get_cwd(), cmd.is_disabled_for_archives())
            for cmd in cmds]

    def get_commands(self):
        try:
            return [OpenWithCommand(label, command, cwd, disabled_for_archives)
                    for label, command, cwd, disabled_for_archives
                    in prefs['external commands']]
        except ValueError as e:
            OpenWithException(_('external commands error: {}.').format(e))


class OpenWithCommand(object):
    def __init__(self, label, command, cwd, disabled_for_archives):
        self.label = label
        self.command = command.strip()
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
        ''' Spawns a new process with the given executable
        and arguments. '''
        if (self.is_disabled_for_archives() and
            window.filehandler.archive_type is not None):
            window.osd.show(_('"%s" is disabled for archives.') % \
                            self.get_label())
            return

        current_dir = os.getcwd()
        try:
            if self.is_valid_workdir(window):
                workdir = self.parse(window, text=self.get_cwd())[0]
                os.chdir(workdir)

            args = self.parse(window)
            process.call_thread(args)

        except Exception as e:
            text = _('Could not run command %(cmdlabel)s: %(exception)s') % \
                {'cmdlabel': self.get_label(), 'exception': str(e)}
            window.osd.show(text)
        finally:
            os.chdir(current_dir)

    def is_executable(self, window):
        ''' Check if a name is executable. This name can be either
        a relative path, when the executable is in PATH, or an
        absolute path. '''
        args = self.parse(window)
        if len(args) == 0:
            return False

        if self.is_valid_workdir(window):
            workdir = self.parse(window, text=self.get_cwd())[0]
        else:
            workdir = os.getcwd()

        exe = process.find_executable((args[0],), workdir=workdir)

        return exe is not None

    def is_valid_workdir(self, window, allow_empty=False):
        ''' Check if the working directory is valid. '''
        cwd = self.get_cwd().strip()
        if not cwd:
            return allow_empty

        args = self.parse(window, text=cwd)
        if len(args) > 1:
            return False

        dir = args[0]
        if os.path.isdir(dir) and os.access(dir, os.X_OK):
            return True

        return False

    def parse(self, window, text='', check_restrictions=True):
        ''' Parses the command string and replaces special characters
        with their respective variable contents. Returns a list of
        arguments.
        If check_restrictions is False, no checking will be done
        if one of the variables isn't valid in the current file context. '''
        if not text:
            text = self.get_command()
        if not text.strip():
            raise OpenWithException(_('Command line is empty.'))

        args = self._commandline_to_arguments(
            text, window,
            self._get_context_type(window, check_restrictions)
        )
        return args

    def _commandline_to_arguments(self, line, window, context_type):
        ''' New parser for commandline using shlex and new style formatter.
        '''
        result = shlex.split(line)
        variables = self._create_format_dict(window, context_type)
        for i, arg in enumerate(result):
            result[i]=self._format_argument(arg, variables)
        return result

    def _create_format_dict(self, window, context_type):
        variables = {}
        if context_type == NO_FILE_CONTEXT:
            # dummy variables for preview if no file opened
            variables.update((head+tail,'{{{}{}}}'.format(head, tail))
                             for head in ('image', 'archive', 'container')
                             for tail in ('', 'dir', 'base', 'dirbase'))
            return variables
        variables.update((
            ('image', os.path.normpath(window.imagehandler.get_path_to_page())), # %F
            ('imagebase', window.imagehandler.get_page_filename()), # %f
        ))
        variables['imagedir'] = os.path.dirname(variables['image']) # %D
        variables['imagedirbase'] = os.path.basename(variables['imagedir']) # %d
        if context_type & ARCHIVE_CONTEXT:
            variables.update((
                ('archive', window.filehandler.get_path_to_base()), # %A
                ('archivebase', window.filehandler.get_base_filename()), # %a
            ))
            variables['archivedir'] = os.path.dirname(variables['archive']) # %C
            variables['archivedirbase'] = os.path.basename(variables['archivedir']) # %c
            container = 'archive' # currently opened archive
        else:
            container = 'imagedir' # directory containing the currently opened image file
        variables.update((
            ('container', variables[container]), # %B
            ('containerbase', variables[container+'base']), # %b
        ))
        variables['containerdir'] = os.path.dirname(variables['container']) # %S
        variables['containerdirbase'] = os.path.basename(variables['containerdir']) # %s
        return variables

    def _format_argument(self, string, variables):
        try:
            # Also add system environment here.
            return string.format(**variables, **os.environ)
        except KeyError as e:
            raise OpenWithException(_('Unknown variable: {}.').format(e))

    def _get_context_type(self, window, check_restrictions=True):
        if not check_restrictions:
            return DEBUGGING_CONTEXT # ignore context, reflect variable name
        context = 0
        if not window.filehandler.file_loaded:
            context = NO_FILE_CONTEXT # no file loaded
        elif window.filehandler.archive_type is not None:
            context = IMAGE_FILE_CONTEXT|ARCHIVE_CONTEXT # archive loaded
        else:
            context = IMAGE_FILE_CONTEXT # image loaded (no archive)
        if not window.imagehandler.get_current_page():
            context &= ~IMAGE_FILE_CONTEXT # empty archive
        return context


class OpenWithEditor(Gtk.Dialog):
    ''' The editor for changing and creating external commands. This window
    keeps its own internal model once initialized, and will overwrite
    the external model (i.e. preferences) only when properly closed. '''

    def __init__(self, window, openwithmanager):
        super(OpenWithEditor, self).__init__(title=_('Edit external commands'))
        self.set_transient_for(window)
        self.set_destroy_with_parent(True)
        self._window = window
        self._openwith = openwithmanager
        self._changed = False

        self._command_tree = Gtk.TreeView()
        self._command_tree.get_selection().connect('changed', self._item_selected)
        self._add_button = Gtk.Button.new_from_stock(Gtk.STOCK_ADD)
        self._add_button.connect('clicked', self._add_command)
        self._add_sep_button = Gtk.Button.new_with_mnemonic(_('Add _separator'))
        self._add_sep_button.connect('clicked', self._add_sep_command)
        self._remove_button = Gtk.Button.new_from_stock(Gtk.STOCK_REMOVE)
        self._remove_button.connect('clicked', self._remove_command)
        self._remove_button.set_sensitive(False)
        self._up_button = Gtk.Button.new_from_stock(Gtk.STOCK_GO_UP)
        self._up_button.connect('clicked', self._up_command)
        self._up_button.set_sensitive(False)
        self._down_button = Gtk.Button.new_from_stock(Gtk.STOCK_GO_DOWN)
        self._down_button.connect('clicked', self._down_command)
        self._down_button.set_sensitive(False)
        self._run_button = Gtk.Button.new_with_mnemonic(_('Run _command'))
        self._run_button.connect('clicked', self._run_command)
        self._run_button.set_sensitive(False)
        self._test_field = Gtk.Entry()
        self._test_field.set_property('editable', False)
        self._exec_label = Gtk.Label()
        self._exec_label.set_alignment(0, 0)
        self._set_exec_text('')
        self._save_button = self.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.ACCEPT)

        self._layout()
        self._setup_table()

        self.connect('response', self._response)
        self._window.page_changed += self.test_command
        self._window.filehandler.file_opened += self.test_command
        self._window.filehandler.file_closed += self.test_command

        self.resize(600, 400)

    def save(self):
        ''' Serializes the tree model into a list of OpenWithCommands
        and passes these back to the Manager object for persistance. '''
        commands = self.get_commands()
        self._openwith.set_commands(commands)
        self._changed = False

    def get_commands(self):
        ''' Retrieves a list of OpenWithCommand instances from
        the list model. '''
        model = self._command_tree.get_model()
        iter = model.get_iter_first()
        commands = []
        while iter:
            label, command, cwd, disabled_for_archives = model.get(iter, 0, 1, 2, 3)
            commands.append(OpenWithCommand(label, command, cwd, disabled_for_archives))
            iter = model.iter_next(iter)
        return commands

    def get_command(self):
        ''' Retrieves the selected command object. '''
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
        ''' Parses the currently selected command and displays the output in the
        text box next to the button. '''
        command = self.get_command()
        self._run_button.set_sensitive(False)
        if not command:
            return

        # Test only if the selected field is a valid command
        if command.is_separator():
            self._test_field.set_text(_('This is a separator pseudo-command.'))
            self._set_exec_text('')
            return

        try:
            self._test_field.set_text(shlex.join(command.parse(self._window)))
            self._run_button.set_sensitive(True)

            if not command.is_valid_workdir(self._window, allow_empty=True):
                self._set_exec_text(
                    _('"%s" does not have a valid working directory.') % command.get_label())
            elif not command.is_executable(self._window):
                self._set_exec_text(
                    _('"%s" does not appear to have a valid executable.') % command.get_label())
            else:
                self._set_exec_text('')
        except OpenWithException as e:
            self._test_field.set_text(str(e))
            self._set_exec_text('')

    def _add_command(self, button):
        ''' Add a new empty label-command line to the list. '''
        row = (_('Command label'), '', '', False, True)
        selection = self._command_tree.get_selection()
        if selection and selection.get_selected()[1]:
            model, iter = selection.get_selected()
            model.insert_before(iter, row)
        else:
            self._command_tree.get_model().append(row)
        self._changed = True

    def _add_sep_command(self, button):
        ''' Adds a new separator line. '''
        row = ('-', '', '', False, False)
        selection = self._command_tree.get_selection()
        if selection and selection.get_selected()[1]:
            model, iter = selection.get_selected()
            model.insert_before(iter, row)
        else:
            self._command_tree.get_model().append(row)
        self._changed = True

    def _remove_command(self, button):
        ''' Removes the currently selected command from the list. '''
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            model.remove(iter)
            self._changed = True

    def _up_command(self, button):
        ''' Moves the selected command up by one. '''
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            path = model.get_path(iter)[0]

            if path >= 1:
                up = model.get_iter(path - 1)
                model.swap(iter, up)
            self._changed = True

    def _down_command(self, button):
        ''' Moves the selected command down by one. '''
        model, iter = self._command_tree.get_selection().get_selected()
        if (iter and model.iter_is_valid(iter)):
            path = model.get_path(iter)[0]

            if path < len(self.get_commands()) - 1:
                down = model.get_iter(path + 1)
                model.swap(iter, down)
            self._changed = True

    def _run_command(self, button):
        ''' Executes the selected command in the current context. '''
        command = self.get_command()
        if command and not command.is_separator():
            command.execute(self._window)

    def _item_selected(self, selection):
        ''' Enable or disable buttons that depend on an item being selected. '''
        for button in (self._remove_button, self._up_button,
                self._down_button):
            button.set_sensitive(selection.count_selected_rows() > 0)

        if selection.count_selected_rows() > 0:
            self.test_command()
        else:
            self._test_field.set_text('')

    def _set_exec_text(self, text):
        self._exec_label.set_text(text)

    def _layout(self):
        ''' Create and lay out UI components. '''
        # All these boxes basically are just for adding a 4px border
        vbox = self.get_content_area()
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, True, True, 4)
        content = Gtk.VBox()
        content.set_spacing(6)
        hbox.pack_start(content, True, True, 4)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_window.add(self._command_tree)
        content.pack_start(scroll_window, True, True, 0)

        buttonbox = Gtk.HBox()
        buttonbox.pack_start(self._add_button, False, False, 0)
        buttonbox.pack_start(self._add_sep_button, False, False, 0)
        buttonbox.pack_start(self._remove_button, False, False, 0)
        buttonbox.pack_start(self._up_button, False, False, 0)
        buttonbox.pack_start(self._down_button, False, False, 0)
        content.pack_start(buttonbox, False, False, 0)

        preview_box = Gtk.HBox()
        preview_box.pack_start(Gtk.Label(label=_('Preview:')), False, False, 0)
        preview_box.pack_start(self._test_field, True, True, 4)
        preview_box.pack_start(self._run_button, False, False, 0)
        content.pack_start(preview_box, False, False, 0)

        content.pack_start(self._exec_label, False, False, 0)

        hints_expander = Gtk.Expander.new(_('Hints of variables in command'))
        content.pack_start(hints_expander, False, False, 0)

        hints_grid = Gtk.Grid()
        hints_expander.add(hints_grid)

        hints_all = [(
            ('{image}', _('Full path of the currently opened image file')),
            ('{imagebase}', _('Base name of {}').format('"{image}"')),
            ('{imagedir}', _('Full directory name of {}').format('"{image}"')),
            ('{imagedirbase}', _('Base name of {}').format('"{imagedir}"')),
            ('{container}', _('Full path of the currently opened directory or archive')),
            ('{containerbase}', _('Base name of {}').format('"{container}"')),
            ('{containerdir}', _('Full directory name of {}').format('"{container}"')),
            ('{containerdirbase}', _('Base name of {}').format('"{containerdir}"')),
        ), (
            ('{archive}', _('Full path of the currently opened archive')),
            ('{archivebase}', _('Base name of {}').format('"{archive}"')),
            ('{archivedir}', _('Full directory name of {}').format('"{archive}"')),
            ('{archivedirbase}', _('Base name of {}').format('"{archivedir}"')),
            ('{{', '{'),
            ('}}', '}'),
            ('{{{}}}'.format(_('<environ name>')), _('System Environment')),
        )]

        for x, hints in enumerate(hints_all):
            for y, (key, desc) in enumerate(hints):
                hints_grid.attach(Gtk.Label(label=key, halign=Gtk.Align.CENTER, margin=4),
                                  x*2, y, 1, 1)
                hints_grid.attach(Gtk.Label(label=desc, halign=Gtk.Align.START, margin=4),
                                  x*2+1, y, 1, 1)

        return # keep infomations below for reference
        linklabel = Gtk.Label()
        linklabel.set_markup(_('Please refer to the <a href="%s">external command documentation</a> '
            'for a list of usable variables and other hints.') % \
                'https://sourceforge.net/p/mcomix/wiki/External_Commands')
        linklabel.set_alignment(0, 0)
        content.pack_start(linklabel, False, False, 4)

    def _setup_table(self):
        ''' Initializes the TreeView with settings and data. '''
        for i, label in enumerate((_('Label'), _('Command'), _('Working directory'))):
            renderer = Gtk.CellRendererText()
            renderer.connect('edited', self._text_changed, i)
            column = Gtk.TreeViewColumn(label, renderer)
            column.set_property('resizable', True)
            column.set_attributes(renderer, text=i, editable=4)
            if (i == 1):
                column.set_expand(True)  # Command column should scale automatically
            self._command_tree.append_column(column)

        # The 'Disabled in archives' field is shown as toggle button
        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self._value_changed,
                len(self._command_tree.get_columns()))
        column = Gtk.TreeViewColumn(_('Disabled in archives'), renderer)
        column.set_attributes(renderer, active=len(self._command_tree.get_columns()),
                activatable=4)
        self._command_tree.append_column(column)

        # Label, command, working dir, disabled for archives, line is editable
        model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING,
                GObject.TYPE_BOOLEAN, GObject.TYPE_BOOLEAN)
        for command in self._openwith.get_commands():
            model.append((command.get_label(), command.get_command(), command.get_cwd(),
                command.is_disabled_for_archives(), not command.is_separator()))
        self._command_tree.set_model(model)

        self._command_tree.set_headers_visible(True)
        self._command_tree.set_reorderable(True)

    def _text_changed(self, renderer, path, new_text, column):
        ''' Called when the user edits a field in the table. '''
        # Prevent changing command to separator, and completely removing label
        if column == 0 and (not new_text.strip() or re.match(r'^-+$', new_text)):
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
        GLib.idle_add(delayed_set_value)

    def _value_changed(self, renderer, path, column):
        ''' Called when a toggle field is changed '''
        model = self._command_tree.get_model()
        iter = model.get_iter(path)
        # Editing the model in the cellrenderercallback stops the editing
        # operation, causing GTK warnings. Delay until callback is finished.
        def delayed_set_value():
            value = not renderer.get_active()
            model.set_value(iter, column, value)
            self._changed = True

        GLib.idle_add(delayed_set_value)

    def _response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            # The Save button is only enabled if all commands are valid
            self.save()
            self.hide()
        else:
            if self._changed:
                confirm_diag = message_dialog.MessageDialog(
                    self,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.YES_NO)
                confirm_diag.set_text(
                    _('Save changes to commands?'),
                    _('You have made changes to the list of external commands that '
                      'have not been saved yet. Press "Yes" to save all changes, '
                      'or "No" to discard them.'))
                response = confirm_diag.run()

                if response == Gtk.ResponseType.YES:
                    self.save()

    def _quote_if_necessary(self, arg):
        ''' Quotes a command line argument if necessary. '''
        if arg == '':
            return '""'
        # simplified version of
        # http://www.gnu.org/software/bash/manual/bashref.html#Double-Quotes
        arg = arg.replace('\\', '\\\\')
        arg = arg.replace('"', '\\"')
        if ' ' in arg:
            return '"' + arg + '"'
        return arg


# vim: expandtab:sw=4:ts=4

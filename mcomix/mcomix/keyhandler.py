'''keyhandler.py - Key handler.
'''

from os.path import normpath
from shlex import join,quote
from subprocess import run
from threading import Lock,Thread,Timer
from time import time_ns

from gi.repository import Gdk,GLib,Gtk

CONTROL_MASK=Gdk.ModifierType.CONTROL_MASK
SHIFT_MASK=Gdk.ModifierType.SHIFT_MASK
MOD1_MASK=Gdk.ModifierType.MOD1_MASK
SUPER_MASK=Gdk.ModifierType.SUPER_MASK
IGNORED_KEYNAMES=(
    'Control_L','Alt_L','Super_L','Shift_L','Meta_L',
    'Control_R','Alt_R','Super_R','Shift_R','Meta_R',
    'Caps_Lock',
)

def _get_keystr(event):
    masks=CONTROL_MASK|SHIFT_MASK|MOD1_MASK|SUPER_MASK
    keymap=Gdk.Keymap.get_default()
    valid,keyval,group,level,modifiers=keymap.translate_keyboard_state(
        event.hardware_keycode,event.get_state(),event.group)
    if (keyname:=Gdk.keyval_name(keyval)) in IGNORED_KEYNAMES:
        return
    masks&=event.get_state()&~modifiers
    prefix=[]
    if masks&CONTROL_MASK: # Ctrl
        prefix.append('C')
    if masks&MOD1_MASK: # Mod1, usually Alt
        prefix.append('M')
    if masks&SUPER_MASK: # Super, 'winlogo'
        prefix.append('S')
    if masks&SHIFT_MASK: # Shift, only recognized without ASCII chars
        prefix.append('F')
    prefix.append(keyname)
    return '-'.join(prefix)

def show_result_dialog(window,args,returncode,stdout,stderr):
    dialog=KeyHandlerResultDialog(window,args,returncode,stdout,stderr)
    dialog.show_all()

def execute(cmd,window,show_result):
    returncode=(process:=run(cmd,capture_output=True)).returncode
    stdout=process.stdout
    stderr=process.stderr
    args=process.args
    if show_result:
        GLib.idle_add(show_result_dialog,window,args,returncode,stdout,stderr)

class KeyHandlerDialog(Gtk.Window):
    def __init__(self,parent,cmd=[],timeout=3000,delay=1000,show_result=True):
        assert cmd
        super().__init__(modal=True,destroy_with_parent=True)
        self._window=parent
        self.set_transient_for(parent)

        self._cmd=cmd.copy()
        self._timeout=max(timeout/1000,0)
        self._delay=max(delay/1000,0)
        self._show_result=show_result

        self._timer=None
        self._start_timestamp=0
        self._waiting=False
        self._keystr=None

        self._archivepath=''
        self._imagepath=''
        if parent.filehandler.archive_type is not None:
            self._archivepath=normpath(parent.filehandler.get_path_to_base())
        if parent.imagehandler.get_current_page():
            self._imagepath=normpath(parent.imagehandler.get_path_to_page())

        stdin=f'archivepath: {self._archivepath}\nimagepath: {self._imagepath}'

        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self._progressbar=Gtk.ProgressBar()
        self._progressbar.set_show_text(True)
        self._progressbar.set_text(_('Wait for key...'))
        self._progressbar.set_fraction(1)
        box.add(self._progressbar)

        self.add(box)

        self.connect('show',self._keyhandler_started)
        self.connect('destroy',self._keyhandler_closed)
        self.connect('key-press-event',self._key_press_event)
        self.connect('key-release-event', self._key_release_event)

    def _cancal_timer(self):
        if self._timer is not None:
            timer=self._timer
            self._timer=None
            timer.cancel()
            self._progressbar.set_fraction(0)

    def _update_progressbar(self):
        with (lock:=Lock()):
            while self._timer is not None:
                duration=self._timeout-(time_ns()-self._start_timestamp)/(10**9)
                GLib.idle_add(self._progressbar.set_fraction,duration/self._timeout)
                lock.acquire(timeout=10**-3)

    def _keyhandler_started(self,dialog):
        self._waiting=True
        if self._timeout:
            self._timer=Timer(self._timeout,GLib.idle_add,args=(self._keyhandler_timeout,))
            self._timer.start()
            self._start_timestamp=time_ns()
            Thread(target=self._update_progressbar).start()

    def _keyhandler_timeout(self):
        self._waiting=False
        self._timer=None
        self._keystr=None
        if self._delay:
            self._progressbar.set_text(_('Timeout'))
            Timer(self._delay,GLib.idle_add,args=(self.destroy,)).start()
        else:
            self.destroy()

    def _keyhandler_closed(self,dialog):
        self._cancal_timer()
        if self._keystr is None:
            return
        self._cmd.extend((self._keystr,self._imagepath,self._archivepath))
        Thread(target=execute,args=(self._cmd,self._window,self._show_result),
               daemon=True).start()

    def _key_press_event(self,dialog,event):
        if not self._waiting or (keystr:=_get_keystr(event)) is None:
            return
        self._waiting=False
        self._keystr=keystr
        if self._delay:
            msg=_('Call key-handler')
            self._progressbar.set_text(f'{msg}:\n{keystr}')
            self._cancal_timer()
            Timer(self._delay,GLib.idle_add,args=(self.destroy,)).start()
        else:
            self.destroy()

    def _key_release_event(self,dialog,event):
        # XXX: ignore key-release-event for now.
        pass

class KeyHandlerResultDialog(Gtk.Dialog):
    def __init__(self,parent,cmd,returncode,stdout,stderr):
        super().__init__(modal=True,destroy_with_parent=True)
        self._window=parent
        self.set_transient_for(parent)

        self._box=self.get_content_area()

        self._add_result(f'returncode: {returncode}',join(cmd))
        if stdout:
            try:
                self._add_result(f'stdout:',stdout.decode('utf8'))
            except UnicodeDecodeError:
                self._add_result('stdout:','<binary data>')
        if stderr:
            try:
                self._add_result(f'stderr:',stderr.decode('utf8'))
            except UnicodeDecodeError:
                self._add_result('stderr:','<binary data>')

    def _add_result(self,labeltext,text):
        label=Gtk.Label()
        label.set_text(labeltext)
        textarea=Gtk.TextView(editable=False,monospace=True)
        textarea.get_buffer().set_text(text)
        scrolled=Gtk.ScrolledWindow(
            min_content_width=800,
            max_content_height=600,
        )
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.NEVER)
        scrolled.add(textarea)
        self._box.add(label)
        self._box.add(scrolled)

# Local Variables:
# coding: utf-8
# mode: python
# python-indent-offset: 4
# indent-tabs-mode: nil
# End:

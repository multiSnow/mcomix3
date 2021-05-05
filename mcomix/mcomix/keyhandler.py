'''keyhandler.py - Key handler.
'''

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

        self._progressbar=Gtk.ProgressBar()
        self._progressbar.set_show_text(True)
        self._progressbar.set_text(_('Wait for key...'))
        self._progressbar.set_fraction(1)
        self.add(self._progressbar)

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
        if self._delay:
            self._progressbar.set_text(_('Timeout'))
            Timer(self._delay,GLib.idle_add,args=(self.destroy,)).start()
        else:
            self.destroy()

    def _keyhandler_closed(self,dialog):
        self._cancal_timer()

    def _key_press_event(self,dialog,event):
        if not self._waiting or (keystr:=_get_keystr(event)) is None:
            return
        self._waiting=False
        if self._delay:
            msg=_('Call key-handler')
            self._progressbar.set_text(f'{msg}:\n{keystr}')
            self._cancal_timer()
            Timer(self._delay,GLib.idle_add,args=(self.destroy,)).start()
        else:
            self.destroy()
        self._cmd.append(keystr)
        # TODO: call keyhandler

    def _key_release_event(self,dialog,event):
        # XXX: ignore key-release-event for now.
        pass

# Local Variables:
# coding: utf-8
# mode: python
# python-indent-offset: 4
# indent-tabs-mode: nil
# End:

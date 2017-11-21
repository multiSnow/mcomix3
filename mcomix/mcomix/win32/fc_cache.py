
from mcomix import i18n, process

import tempfile
import shutil
import time
import sys
import os


# Find fc-cache.exe
fc_cache_exe = process.find_executable((
    'fc-cache',
    'c:/Python27/Lib/site-packages/gnome/fc-cache.exe',
))


# Update cache, while displaying a status dialog so the user know something is happening.
def update(args=[], notification_delay=3, notification_duration=3):
    '''Update fontconfig cache by calling fc-cache.exe manually.

    The function will block until fc-cache.exe has finished. If the update
    takes more than <notification_delay> seconds, a notification window will be
    shown for at least <notification_duration> seconds.
    '''

    cmd = [fc_cache_exe]
    cmd.extend(args)
    proc = process.popen(cmd, stdout=process.NULL)

    notif_time = time.time() + notification_delay
    end_time = notif_time + notification_duration

    i18n.install_gettext()

    import pygtk
    pygtk.require('2.0')
    import gtk, gobject
    gobject.threads_init()

    class Window(gtk.Window):

        def __init__(self):
            super(Window, self).__init__()
            self.set_title('MComix')
            self.set_border_width(10)
            self.set_wmclass('MComix', 'MComix')
            self.set_resizable(False)
            self.set_deletable(False)
            self._displayed = False
            vbox = gtk.VBox(spacing=5)
            label = gtk.Label(_('Updating font cache. This may take a few minutes.'))
            vbox.pack_start(label)
            self._spinner = gtk.Spinner()
            vbox.pack_start(self._spinner, expand=False, fill=False)
            vbox.show_all()
            self.add(vbox)
            self.set_geometry_hints(vbox)
            gobject.timeout_add(200, self._on_ping)

        def _on_ping(self):
            now = time.time()
            returncode = proc.poll()
            if returncode is None:
                # Process is still running.
                if now <= notif_time:
                    # Not enough time elapsed, do not show dialog yet.
                    return True
            else:
                # Process has terminated.
                if not notif_time < now < end_time:
                    # Dialog is not being shown or it has already
                    # been displayed for the required amount of time.
                    gtk.main_quit()
                    return False
            if not self._displayed:
                # Show dialog.
                self.show()
                self._spinner.start()
                self._displayed = True
            return True

    # Create a very simple fontconfig configuration,
    # with a temporary cache directory, and only a few fonts.
    tmpdir = tempfile.mkdtemp(suffix='-mcomix-fc_cache')
    try:
        cachedir = os.path.join(tmpdir, 'cache')
        os.mkdir(cachedir)
        config = os.path.join(tmpdir, 'fonts.conf')
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        with open(config, 'w') as f:
            f.write('''<?xml version="1.0"?>
                    <!DOCTYPE fontconfig SYSTEM "fonts.dtd">
                    <fontconfig>
                      <dir>c:/Python27/Lib/site-packages/gnome/share/fonts</dir>
                      <dir>%(executable_dir)s/share/fonts</dir>
                      <cachedir>%(cache_dir)s</cachedir>
                      <alias>
                        <family>Times</family>
                        <default><family>Vera</family></default>
                      </alias>
                      <alias>
                        <family>Helvetica</family>
                        <default><family>Vera</family></default>
                      </alias>
                      <alias>
                        <family>Courier</family>
                        <default><family>Vera</family></default>
                    </alias>
                    </fontconfig>''' % {
                        'executable_dir': exe_dir,
                        'cache_dir': cachedir,
                    })
        previous_config = os.environ.get('FONTCONFIG_FILE', None)
        os.environ['FONTCONFIG_FILE'] = config
        try:
            win = Window()
            gtk.main()
        finally:
            if previous_config is None:
                del os.environ['FONTCONFIG_FILE']
            else:
                os.environ['FONTCONFIG_FILE'] = previous_config
    finally:
        shutil.rmtree(tmpdir)


if __name__=='__main__':
    update()


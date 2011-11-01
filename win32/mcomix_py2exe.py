"""

	This is a wrapper script simply for starting MComix.
	Only used for generating an executable with Py2exe.

	Build instructions:

	1. 'win32/build_py2exe' will create dist_py2exe and copy relevant
	   libraries.
	2. Copy files from mcomix/images and mcomix/messages into
	   dist_py2exe/library.zip/mcomix (this is done by the wrapper script)
	3. Copy share/locale (only gtk20.mo files to conserve space),
	        share/themes/MS-Windows,
			lib/gtk-2.0/2.10.0/engines/libwimp.dll,
			etc/gtk-2.0/gtkrc
			from the GTK+ distribution into dist_py2exe/
	4. Rename dist_py2exe/mcomix_py2exe.exe into MComix.exe (also done
	   (by the wrapper script)

"""

from mcomix.run import run
run()

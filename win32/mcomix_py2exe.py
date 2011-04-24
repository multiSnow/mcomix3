"""

	This is a wrapper script simply for starting MComix. 
	Only used for generating an executable with Py2exe.

	Build instructions:
	
	1. 'setup.py py2exe' will create dist_py2exe and copy relevant libraries.
	2. Copy files from mcomix/images and mcomix/messages into dist_py2exe/library.zip/mcomix
	3. Copy share/locale and share/themes from the GTK+ distribution into dist_py2exe/share
	   (Keep only gtk20.mo files to to save space?)
	4. Rename dist_py2exe/mcomix_py2exe.exe into MComix.exe

"""

from mcomix import mcomixstarter
mcomixstarter.run()

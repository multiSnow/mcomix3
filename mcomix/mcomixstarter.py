#!/usr/bin/python3

'''MComix - GTK Comic Book Viewer
'''

# -------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# -------------------------------------------------------------------------

import sys

py2msg='''PROGRAM TERMINATED
Python 2.x is no longer supported.
'''

if sys.version_info.major<3:
    sys.stderr.write(py2msg)
    sys.exit(1)

if __name__=='__main__':
    import mcomix.run
    mcomix.run.run()

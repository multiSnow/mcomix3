User under win32 should use `original mcomix`__.

=======
MComix3
=======

Fork from MComix gtk3 branch, switch to python3.

Only tested under Linux.

Required:
---------
- **Python3** 3.3 or later.
- **PyGObject** 3.24 or later, with **GTK+ 3 gir bindings** 3.22 or later.
- **PIL** (Python Imaging Library) 1.1.5 or later. Alternatively, **Pillow** (a fork of PIL) can be used.

Recommended:
------------
- **unrar**, **rar** or **libunrar** to extract RAR archives.
- **p7zip** to extract 7Z archives. Note that p7zip might be able to extract RAR archives as well, but this might require additional software (for example, **p7zip-rar** on Debian-like systems), and it might fail to open certain RAR archives, especially newer ones.
- **lha** to extract LHA archives.
- **mupdf** for PDF support.

Run:
----
``python3 mcomix/mcomixstarter.py <diretory, archive or image>``

Install:
--------
**setup.py is not working**

``python3 installer.py --srcdir=mcomix --target=<somewhere>``

then:

``python3 <somewere>/mcomix/mcomixstarter.py <diretory, archive or image>``


.. _mcomix: https://sourceforge.net/projects/mcomix/
__ mcomix_

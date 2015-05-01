
import pkg_resources
import os

def get_pkg_info(pkgname):
    pkg = pkg_resources.require(pkgname)[0]
    info = '\n'.join(pkg.get_metadata_lines('PKG-INFO'))
    return info

datas = []

for pkgname in (
    'czipfile',
    'pillow',
):
    pkg_info = get_pkg_info(pkgname)
    doc_dir = 'build/doc/%s' % pkgname
    info_file = '%s/PKG-INFO.txt' % doc_dir
    os.makedirs(doc_dir)
    with open(info_file, 'w+') as fp:
        fp.write(pkg_info)
        fp.write('\n')
    datas.append((info_file, 'doc/%s' % pkgname))

datas.extend((
    # Add MComix documentation.
    ('README', 'doc/mcomix'),
    ('COPYING', 'doc/mcomix'),
    ('ChangeLog', 'doc/mcomix'),
    # Add Python documentation.
    ('C:/Python27/LICENSE.tx', 'doc/python'),
    ('C:/Python27/NEWS.txt', 'doc/python'),
    ('C:/Python27/README.txt', 'doc/python'),
    # Add Cairo/GLib/GTK+/Pango documentation.
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/share/doc/cairo_[0-9]*/', 'doc/cairo'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/share/doc/glib-[0-9]*/', 'doc/glib'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/share/doc/gtk+-[0-9]*/', 'doc/gtk+'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/share/doc/pango-[0-9]*/', 'doc/pango'),
    # Add Cairo/GLib/GTK+/Pango runtime files.
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/etc/gtk-2.0/gtkrc', 'etc/gtk-2.0'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/etc/pango/pango.aliases', 'etc/pango'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/lib/gtk-2.0/2.10.0/engines', 'lib/gtk-2.0/2.10.0'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/share/icons/hicolor', 'share/icons'),
    ('C:/Python27/Lib/site-packages/gtk-2.0/runtime/share/themes/MS-Windows', 'share/themes'),
    # Add Unrar DLL and documentation.
    ('C:/Program Files/UnrarDLL/unrar.dll', '.'),
    ('C:/Program Files/UnrarDLL/*.txt', 'doc/unrar'),
    # Add MuPDF tools and documentation.
    ('C:/Program Files/MuPDF/mudraw.exe', '.'),
    ('C:/Program Files/MuPDF/mutool.exe', '.'),
    ('C:/Program Files/MuPDF/*.txt', 'doc/mupdf'),
    # Add 7z executable and documentation.
    ('C:/Program Files/7-Zip/7z.exe', '.'),
    ('C:/Program Files/7-Zip/7z.dll', '.'),
    ('C:/Program Files/7-Zip/License.txt', 'doc/7z'),
))

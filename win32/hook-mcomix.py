
import pkg_resources
import glob
import re
import os

from PyInstaller import is_win
import PyInstaller.bindepend
from hookutils import collect_submodules


datas = []
hiddenimports = []

# Add GTK DLLs.

gnome_dir = 'C:/Python27/Lib/site-packages/gnome'
gnome_dll = lambda name: '%s/%s' % (gnome_dir, name)

def gnome_dll_deps(dll, deps):
    deps.add(dll)
    imports = set(PyInstaller.bindepend.getImports(dll))
    assemblies = PyInstaller.bindepend.getAssemblies(dll)
    imports.update([a.getid() for a in assemblies])
    for dll in tuple(imports):
        dll = gnome_dll(dll)
        if dll in deps:
            continue
        if os.path.exists(dll):
            gnome_dll_deps(dll, deps)

dll_list = set()

for dll in (
    'libgdk_pixbuf-2.0-0.dll',
    'libgthread-2.0-0.dll',
    'libgtk-win32-2.0-0.dll',
):
    dll = gnome_dll(dll)
    gnome_dll_deps(dll, dll_list)

for dll in sorted(dll_list):
    datas.append((dll, '.'))

# Add GTK locales.

locale_dir = 'C:/Python27/Lib/site-packages/gnome/share/locale'
for mo in glob.glob('%s/*/LC_MESSAGES/gtk20.mo' % locale_dir):
    datas.append((mo, 'share/locale/%s' % os.path.dirname(mo[len(locale_dir)+1:])))

# Add czipfile/Pillow documentation.

for pkgname in (
    'czipfile',
    'pillow',
):
    pkg = pkg_resources.require(pkgname)[0]
    pkg_info = '\n'.join(pkg.get_metadata_lines('PKG-INFO'))
    doc_dir = 'build/doc/%s' % pkgname
    info_file = '%s/PKG-INFO.txt' % doc_dir
    os.makedirs(doc_dir)
    with open(info_file, 'w+') as fp:
        fp.write(pkg_info)
        fp.write('\n')
    datas.append((info_file, 'doc/%s' % pkgname))

# Add DLLs license and readme files.

license_dir = 'C:/Python27/Lib/site-packages/gnome/license'
doc_rx = re.compile('^(.*)\.(COPYING|LICENSE|README)(\..*)?$')
lib_list = [os.path.basename(dll) for dll in dll_list]
for entry in os.listdir(license_dir):
    m = doc_rx.match(entry)
    if m is None:
        continue
    lib_name = m.group(1).lower()
    for lib in lib_list:
        if -1 == lib.find(lib_name):
            continue
        datas.append(('%s/%s' % (license_dir, entry), 'doc'))
        break

datas.extend((
    # Add MComix documentation.
    ('README', 'doc/MComix'),
    ('COPYING', 'doc/MComix'),
    ('ChangeLog', 'doc/MComix'),
    # Add Python documentation.
    ('C:/Python27/LICENSE.tx', 'doc/Python'),
    ('C:/Python27/NEWS.txt', 'doc/Python'),
    ('C:/Python27/README.txt', 'doc/Python'),
    # Add Cairo/GLib/GTK+/Pango runtime files.
    ('C:/Python27/Lib/site-packages/gnome/etc/fonts', 'etc'),
    ('C:/Python27/Lib/site-packages/gnome/etc/gtk-2.0', 'etc'),
    ('C:/Python27/Lib/site-packages/gnome/etc/pango', 'etc'),
    ('C:/Python27/Lib/site-packages/gnome/lib/gtk-2.0/2.10.0/engines/libwimp.dll', 'lib/gtk-2.0/2.10.0/engines'),
    ('C:/Python27/Lib/site-packages/gnome/share/fonts', 'share'),
    ('C:/Python27/Lib/site-packages/gnome/share/icons/hicolor', 'share/icons'),
    ('C:/Python27/Lib/site-packages/gnome/share/themes/MS-Windows/gtk-2.0', 'share/themes/MS-Windows'),
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

# Add PIL hidden imports.

pil_modules = set(collect_submodules('PIL'))
for unwanted in (
    'PIL.DcxImagePlugin',
    'PIL.EpsImagePlugin',
    'PIL.FpxImagePlugin',
    'PIL.GdImageFile',
    'PIL.GimpGradientFile',
    'PIL.GimpPaletteFile',
    'PIL.GribStubImagePlugin',
    'PIL.Hdf5StubImagePlugin',
    'PIL.ImageQt',
    'PIL.ImageTk',
    'PIL.McIdasImagePlugin',
    'PIL.MicImagePlugin',
    'PIL.MpegImagePlugin',
    'PIL.OleFileIO',
    'PIL.PSDraw',
    'PIL.PixarImagePlugin',
    'PIL.SgiImagePlugin',
    'PIL.SpiderImagePlugin',
    'PIL.SunImagePlugin',
    'PIL._imagingtk',
):
    if unwanted in pil_modules:
        pil_modules.remove(unwanted)

hiddenimports.extend(pil_modules)


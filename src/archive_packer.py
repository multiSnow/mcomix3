"""archive_packer.py - Archive creation class."""

import os
import zipfile
import threading

class Packer:

    """Packer is a threaded class for packing files into ZIP archives.

    It would be straight-forward to add support for more archive types,
    but basically all other types are less well fitted for this particular
    task than ZIP archives are (yes, really).
    """

    def __init__(self, image_files, other_files, archive_path, base_name):
        """Setup a Packer object to create a ZIP archive at <archive_path>.
        All files pointed to by paths in the sequences <image_files> and
        <other_files> will be included in the archive when packed.

        The files in <image_files> will be renamed on the form
        "NN - <base_name>.ext", so that the lexical ordering of their
        filenames match that of their order in the list.

        The files in <other_files> will be included as they are,
        assuming their filenames does not clash with other filenames in
        the archive. All files are placed in the archive root.
        """
        self._image_files = image_files
        self._other_files = other_files
        self._archive_path = archive_path
        self._base_name = base_name
        self._pack_thread = None
        self._packing_successful = False

    def pack(self):
        """Pack all the files in the file lists into the archive."""
        self._pack_thread = threading.Thread(target=self._thread_pack)
        self._pack_thread.setDaemon(False)
        self._pack_thread.start()

    def wait(self):
        """Block until the packer thread has finished. Return True if the
        packer finished its work successfully.
        """
        if self._pack_thread != None:
            self._pack_thread.join()

        return self._packing_successful

    def _thread_pack(self):
        try:
            zfile = zipfile.ZipFile(self._archive_path, 'w')
        except Exception:
            print _('! Could not create archive at ') + self._archive_path
            return

        used_names = []
        pattern = '%%0%dd - %s%%s' % (len(str(len(self._image_files))),
            self._base_name)

        for i, path in enumerate(self._image_files):
            filename = pattern % (i + 1, os.path.splitext(path)[1])

            try:
                zfile.write(path, filename, zipfile.ZIP_STORED)
            except Exception:
                print _('! Could not add file ') + path + _(' to ') + self._archive_path + _(', aborting...')

                zfile.close()

                try:
                    os.remove(self._archive_path)
                except:
                    pass

                return

            used_names.append(filename)

        for path in self._other_files:
            filename = os.path.basename(path)

            while filename in used_names:
                filename = '_%s' % filename

            try:
                zfile.write(path, filename, zipfile.ZIP_DEFLATED)
            except Exception:
                print _('! Could not add file ') + path + _(' to ') + self._archive_path + _(', aborting...')

                zfile.close()

                try:
                    os.remove(self._archive_path)
                except:
                    pass

                return

            used_names.append(filename)

        zfile.close()
        self._packing_successful = True

# vim: expandtab:sw=4:ts=4

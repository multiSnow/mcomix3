'''archive_packer.py - Archive creation class.'''

import io
import os
import shutil
import threading
import zipfile

from mcomix import log

class Packer(object):

    '''Packer is a threaded class for packing files into ZIP archives.

    It would be straight-forward to add support for more archive types,
    but basically all other types are less well fitted for this particular
    task than ZIP archives are (yes, really).
    '''

    def __init__(self, image_files, other_files, archive_path, base_name):
        '''Setup a Packer object to create a ZIP archive at <archive_path>.
        All files pointed to by paths in the sequences <image_files> and
        <other_files> will be included in the archive when packed.

        The files in <image_files> will be renamed on the form
        "NN - <base_name>.ext", so that the lexical ordering of their
        filenames match that of their order in the list.

        The files in <other_files> will be included as they are,
        assuming their filenames does not clash with other filenames in
        the archive. All files are placed in the archive root.
        '''
        self._image_files = image_files
        self._other_files = other_files
        self._archive_path = archive_path
        self._base_name = base_name
        self._pack_thread = None
        self._packing_successful = False

    def pack(self):
        '''Pack all the files in the file lists into the archive.'''
        self._pack_thread = threading.Thread(target=self._thread_pack)
        self._pack_thread.name += '-pack'
        self._pack_thread.daemon=False
        self._pack_thread.start()

    def wait(self):
        '''Block until the packer thread has finished. Return True if the
        packer finished its work successfully.
        '''
        if self._pack_thread != None:
            self._pack_thread.join()

        return self._packing_successful

    def _thread_pack(self):

        used = set()
        fmt = '{{page:0{}d}} - {}{{ext}}'.format(
            len(str(len(self._image_files))), self._base_name)
        with io.BytesIO() as buf:
            with zipfile.ZipFile(buf, mode='w', allowZip64=True) as zfile:
                try:
                    for i, path in enumerate(self._image_files, start=1):
                        b, e = os.path.splitext(path)
                        fname = fmt.format(page=i, ext=e)
                        used.add(fname)
                        zfile.write(path, arcname=fname,
                                    compress_type=zipfile.ZIP_DEFLATED,
                                    compresslevel=9)

                    for path in self._other_files:
                        fname = os.path.basename(path)
                        while fname in used:
                            fname = '_{}'.format(fname)
                        used.add(fname)
                        zfile.write(path, arcname=fname,
                                    compress_type=zipfile.ZIP_DEFLATED,
                                    compresslevel=9)

                except Exception as e:
                    log.error(_('! Could not create archive, {}').format(e))

            # full data of zipfile is completed here
            archivedata = buf.getvalue()

        archive_dir = os.path.dirname(self._archive_path)
        archive_len = len(archivedata)
        if shutil.disk_usage(archive_dir).free < archive_len:
            log.error(_('! Directory {} is out of space, {} needed.').format(
                archive_dir, tools.format_byte_size(archive_len)
            ))
            return

        try:
            with open(self._archive_path, mode='wb') as fp:
                fp.write(archivedata)
        except Exception as e:
            log.error(_('! Could not create archive at path "%s", {}').format(e),
                      self._archive_path)
            try:
                os.remove(self._archive_path)
            except:
                pass
        else:
            self._packing_successful = True

# vim: expandtab:sw=4:ts=4


import os

from . import MComixTest, get_testfile_path

from mcomix import archive_tools
from mcomix import constants


_EXTENSION_TO_MIME_TYPES = {
    'cbz'    : constants.ZIP,
    'zip'    : constants.ZIP,
    'zip.bz2': constants.ZIP_EXTERNAL,
    'rar'    : constants.RAR,
    'tar'    : constants.TAR,
    'tar.gz' : constants.GZIP,
    'tar.bz2': constants.BZIP2,
    'tar.xz' : constants.XZ,
    'pdf'    : constants.PDF,
    '7z'     : constants.SEVENZIP,
    'lha'    : constants.LHA,
}

_ARCHIVE_TYPE_NAMES = {
    constants.ZIP         : 'zip',
    constants.RAR         : 'rar',
    constants.TAR         : 'tar',
    constants.GZIP        : 'gzip',
    constants.BZIP2       : 'bzip2',
    constants.XZ          : 'xz',
    constants.PDF         : 'pdf',
    constants.SEVENZIP    : '7z',
    constants.LHA         : 'lha',
    constants.ZIP_EXTERNAL: 'zip (external)',
}

class ArchiveToolsTest(MComixTest):

    def test_archive_mime_type(self):

       dir = get_testfile_path('archives')
       for filename in os.listdir(dir):
           ext = '.'.join(filename.split('.')[1:])
           path = os.path.join(dir, filename)
           archive_type = archive_tools.archive_mime_type(path)
           expected_type = _EXTENSION_TO_MIME_TYPES.get(ext, '???')
           msg = (
               'archive_mime_type("%s") failed; '
               'result differs: %s [%s] instead of %s [%s]'
               % (path,
                  archive_type, _ARCHIVE_TYPE_NAMES.get(archive_type, '???'),
                  expected_type, _ARCHIVE_TYPE_NAMES.get(expected_type, '???'),
                 )
           )
           self.assertEqual(archive_type, expected_type, msg=msg)


import hashlib
import locale
import os
import re
import shutil
import sys
import tempfile
import unittest

from mcomix import process
from mcomix.archive import rar
from mcomix.archive import rarfile
from mcomix.archive import sevenzip
from mcomix.archive import tar
from mcomix.archive import zip
from mcomix.archive import zip_external
import mcomix


class UnsupportedFormat(Exception):

    def __init__(self, format):
        super(UnsupportedFormat, self).__init__('unsuported %s format' % format)

class UnsupportedOption(Exception):

    def __init__(self, format, option):
        super(UnsupportedOption, self).__init__('unsuported option for %s format: %s' % (format, option))

def make_archive(outfile, contents, format='zip', solid=False, password=None):
    if os.path.exists(outfile):
        raise Exception('%s already exists' % outfile)
    cleanup = []
    try:
        outpath = os.path.abspath(outfile)
        tmp_dir = tempfile.mkdtemp(prefix=u'mcomix.test.', suffix=os.sep)
        cleanup.append(lambda: shutil.rmtree(tmp_dir))
        entry_list = []
        for name, filename in contents:
            entry_list.append(name)
            path = os.path.join(tmp_dir, name)
            if filename is None:
                os.makedirs(path)
                continue
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            shutil.copy(filename, path)
        if '7z' == format:
            cmd = ['7z', 'a']
            cmd.append('-ms=on' if solid else '-ms=off')
            if password is not None:
                cmd.append('-p' + password)
            cmd.extend(('--', outpath))
            # To avoid @ being treated as a special character...
            tmp_file = tempfile.NamedTemporaryFile(prefix='mcomix.test.', delete=False)
            cleanup.append(lambda: os.unlink(tmp_file.name))
            for entry in entry_list:
                tmp_file.write(entry.encode(locale.getpreferredencoding()) + '\n')
            tmp_file.close()
            entry_list = ['@' + tmp_file.name]
        elif 'lha' == format:
            if solid:
                raise UnsupportedOption(format, 'solid')
            cmd = ['lha', 'a', outpath, '--']
        elif 'rar' == format:
            cmd = ['rar', 'a', '-r']
            cmd.append('-s' if solid else '-s-')
            if password is not None:
                cmd.append('-p' + password)
            cmd.extend(('--', outpath))
        elif format.startswith('tar'):
            if not solid:
                raise UnsupportedOption(format, 'not solid')
            if 'tar' == format:
                compression = ''
            elif 'tar.bz2' == format:
                compression = 'j'
            elif 'tar.gz' == format:
                compression = 'z'
            else:
                raise UnsupportedFormat(format)
            cmd = ['tar', '-cv%sf' % compression, outpath, '--']
            # entry_list = [ name.replace('\\', '\\\\') for name in entry_list]
        elif 'zip' == format:
            if solid:
                raise UnsupportedOption(format, 'solid')
            cmd = ['zip', '-r']
            if password is not None:
                cmd.extend(['-P', password])
            cmd.extend([outpath, '--'])
        else:
            raise UnsupportedFormat(format)
        cmd.extend(entry_list)
        cwd = os.getcwd()
        cleanup.append(lambda: os.chdir(cwd))
        os.chdir(tmp_dir)
        proc = process.popen(cmd, stderr=process.PIPE)
        cleanup.append(proc.stdout.close)
        cleanup.append(proc.stderr.close)
        cleanup.append(proc.wait)
        stdout, stderr = proc.communicate()
    finally:
        for fn in reversed(cleanup):
            fn()
    if not os.path.exists(outfile):
        raise Exception('archive creation failed: %s\nstdout:\n%s\nstderr:\n%s\n' % (
            ' '.join(cmd), stdout, stderr
        ))

def exe_available(exe):
    try:
        process.call([exe])
    except:
        return False
    return True

def md5(path):
    hash = hashlib.md5()
    hash.update(open(path, 'rb').read())
    return hash.hexdigest()

class ArchiveFormatTest:

    name = ''
    skip = None
    handler = None
    format = ''
    solid = False
    password = None
    contents = ()
    archive = None

    @classmethod
    def _ask_password(cls, archive):
        if cls.password:
            return cls.password
        raise Exception('asked for password on unprotected archive!')

    @classmethod
    def setUpClass(cls):
        if cls.skip is not None:
            raise unittest.SkipTest(cls.skip)
        cls.tmp_dir = tempfile.mkdtemp(prefix=u'mcomix.test.', suffix=os.sep)
        cls.archive_path = u'test/files/archives/%s.%s' % (cls.archive, cls.format)
        cls.archive_contents = dict([
            (archive_name, filename)
            for name, archive_name, filename
            in cls.contents
        ])
        mcomix.archive.ask_for_password = cls._ask_password
        if os.path.exists(cls.archive_path):
            return
        if 'win32' == sys.platform:
            raise Exception('archive creation unsupported on Windows!')
        make_archive(cls.archive_path,
                     [(name, filename)
                      for name, archive_name, filename
                      in cls.contents],
                     format=cls.format,
                     solid=cls.solid,
                     password=cls.password)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir)

    def setUp(self):
        self.dest_dir = os.path.join(self.tmp_dir, 'contents')
        os.mkdir(self.dest_dir)

    def tearDown(self):
        shutil.rmtree(self.dest_dir)

    def test_init_not_unicode(self):
        self.assertRaises(AssertionError, self.handler, 'test')

    def test_archive(self):
        archive = self.handler(self.archive_path)
        self.assertEqual(archive.archive, self.archive_path)

    def test_list_contents(self):
        archive = self.handler(self.archive_path)
        contents = archive.list_contents()
        self.assertItemsEqual(contents, self.archive_contents.keys())

    def test_iter_contents(self):
        archive = self.handler(self.archive_path)
        contents = []
        for name in archive.iter_contents():
            contents.append(name)
        self.assertItemsEqual(contents, self.archive_contents.keys())

    def test_is_solid(self):
        archive = self.handler(self.archive_path)
        archive.list_contents()
        self.assertEqual(self.solid, archive.is_solid())
        archive = self.handler(self.archive_path)
        list(archive.iter_contents())
        self.assertEqual(self.solid, archive.is_solid())

    def test_extract(self):
        archive = self.handler(self.archive_path)
        contents = archive.list_contents()
        for name in contents:
            archive.extract(name, self.dest_dir)
            path = os.path.join(self.dest_dir, name)
            self.assertTrue(os.path.isfile(path))
            extracted_md5 = md5(path)
            original_md5 = md5(self.archive_contents[name])
            self.assertEqual((name, extracted_md5), (name, original_md5))

    def test_iter_extract(self):
        archive = self.handler(self.archive_path)
        contents = archive.list_contents()
        extracted = []
        for name in archive.iter_extract(reversed(contents), self.dest_dir):
            extracted.append(name)
            path = os.path.join(self.dest_dir, name)
            self.assertTrue(os.path.isfile(path))
            extracted_md5 = md5(path)
            original_md5 = md5(self.archive_contents[name])
            self.assertEqual((name, extracted_md5), (name, original_md5))
        # Entries must have been extracted in the order they are listed in the archive.
        # (necessary to prevent bad performances on solid archives)
        self.assertEqual(extracted, contents)


_FORMAT_EXECUTABLE = {
    '7z'     : '7z',
    'lha'    : 'lha',
    'rar'    : 'rar',
    'tar'    : 'tar',
    'tar.bz2': 'tar',
    'tar.gz' : 'tar',
    'zip'    : 'zip',
}


for name, handler, is_available, format, not_solid, solid, password in (
    ('7z (external)'    , sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , '7z'     , True , True , True ),
    ('7z (external) lha', sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , 'lha'    , True , False, False),
    ('7z (external) rar', sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , 'rar'    , True , True , True ),
    ('7z (external) zip', sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , 'zip'    , True , False, True ),
    ('tar'              , tar.TarArchive             , True                                      , 'tar'    , False, True , False),
    ('tar (gzip)'       , tar.TarArchive             , True                                      , 'tar.gz' , False, True , False),
    ('tar (bzip2)'      , tar.TarArchive             , True                                      , 'tar.bz2', False, True , False),
    ('rar (external)'   , rar.RarExecArchive         , rar.RarExecArchive.is_available()         , 'rar'    , True , True , True ),
    ('rar (dll)'        , rarfile.UnrarDll           , rarfile.UnrarDll.is_available()           , 'rar'    , True , True , True ),
    ('zip'              , zip.ZipArchive             , True                                      , 'zip'    , True , False, True ),
    ('zip (external)'   , zip_external.ZipExecArchive, zip_external.ZipExecArchive.is_available(), 'zip'    , True , False, True ),
):
    base_class_name = 'ArchiveFormat'
    base_class_name += ''.join([part.capitalize() for part in re.sub('[^\w]+', ' ', name).split()])
    base_class_name += '%sTest'
    base_class_dict = {
        'name': name,
        'handler': handler,
        'format': format,
    }

    skip = None
    if not is_available:
        skip = 'support for %s format with %s not available' % (format, name)
    base_class_dict['skip'] = skip

    base_class_list = []
    if not_solid:
        base_class_list.append(('', {}))
    if solid:
        base_class_list.append(('Solid', {'solid': True}))

    class_list = []

    if password:
        for variant, params in base_class_list:
            variant = variant + 'Password'
            params = dict(params)
            params['password'] = 'password'
            params['contents'] = (
                ('arg.jpeg', 'arg.jpeg', 'test/files/images/01-JPG-Indexed.jpg'),
                ('foo.JPG' , 'foo.JPG' , 'test/files/images/04-PNG-Indexed.png'),
                ('bar.jpg' , 'bar.jpg' , 'test/files/images/02-JPG-RGB.jpg'    ),
                ('meh.png' , 'meh.png' , 'test/files/images/03-PNG-RGB.png'    ),
            )
            class_list.append((variant, params))

    for sub_variant, is_supported, contents in (
        ('Flat', True, (
            ('arg.jpeg'            , 'arg.jpeg'            , 'test/files/images/01-JPG-Indexed.jpg'),
            ('foo.JPG'             , 'foo.JPG'             , 'test/files/images/04-PNG-Indexed.png'),
            ('bar.jpg'             , 'bar.jpg'             , 'test/files/images/02-JPG-RGB.jpg'    ),
            ('meh.png'             , 'meh.png'             , 'test/files/images/03-PNG-RGB.png'    ),
        )),
        ('Tree', True, (
            ('dir1/arg.jpeg'       , 'dir1/arg.jpeg'       , 'test/files/images/01-JPG-Indexed.jpg'),
            ('dir1/subdir1/foo.JPG', 'dir1/subdir1/foo.JPG', 'test/files/images/04-PNG-Indexed.png'),
            ('dir2/subdir1/bar.jpg', 'dir2/subdir1/bar.jpg', 'test/files/images/02-JPG-RGB.jpg'    ),
            ('meh.png'             , 'meh.png'             , 'test/files/images/03-PNG-RGB.png'    ),
        )),
        # Check we don't treat an entry name as an option or command line switch.
        ('OptEntry', True, (
            ('-rg.jpeg'            , '-rg.jpeg'            , 'test/files/images/01-JPG-Indexed.jpg'),
            ('--o.JPG'             , '--o.JPG'             , 'test/files/images/04-PNG-Indexed.png'),
            ('+ar.jpg'             , '+ar.jpg'             , 'test/files/images/02-JPG-RGB.jpg'    ),
            ('@eh.png'             , '@eh.png'             , 'test/files/images/03-PNG-RGB.png'    ),
        )),
        # Check an entry name is not used as glob pattern.
        ('GlobEntries', 'win32' != sys.platform, (
            ('[rg.jpeg'            , '[rg.jpeg'            , 'test/files/images/01-JPG-Indexed.jpg'),
            ('[]rg.jpeg'           , '[]rg.jpeg'           , 'test/files/images/02-JPG-RGB.jpg'    ),
            ('*oo.JPG'             , '*oo.JPG'             , 'test/files/images/04-PNG-Indexed.png'),
            ('?eh.png'             , '?eh.png'             , 'test/files/images/03-PNG-RGB.png'    ),
            # ('\\r.jpg'             , '\\r.jpg'             , 'test/files/images/blue.png'          ),
            # ('ba\\.jpg'            , 'ba\\.jpg'            , 'test/files/images/red.png'           ),
        )),
        # Same, Windows version.
        ('GlobEntries', 'win32' == sys.platform, (
            ('[rg.jpeg'            , '[rg.jpeg'            , 'test/files/images/01-JPG-Indexed.jpg'),
            ('[]rg.jpeg'           , '[]rg.jpeg'           , 'test/files/images/02-JPG-RGB.jpg'    ),
            ('*oo.JPG'             , '_oo.JPG'             , 'test/files/images/04-PNG-Indexed.png'),
            ('?eh.png'             , '_eh.png'             , 'test/files/images/03-PNG-RGB.png'    ),
            # ('\\r.jpg'             , '\\r.jpg'             , 'test/files/images/blue.png'          ),
            # ('ba\\.jpg'            , 'ba\\.jpg'            , 'test/files/images/red.png'           ),
        )),
        # Check how invalid filesystem characters are handled.
        # ('InvalidFileSystemChars', 'win32' == sys.platform, (
        #     ('a<g.jpeg'            , 'a_g.jpeg'            ,'test/files/images/01-JPG-Indexed.jpg'),
        #     ('f*o.JPG'             , 'f_o.JPG'             ,'test/files/images/04-PNG-Indexed.png'),
        #     ('b:r.jpg'             , 'b_r.jpg'             ,'test/files/images/02-JPG-RGB.jpg'    ),
        #     ('m?h.png'             , 'm_h.png'             ,'test/files/images/03-PNG-RGB.png'    ),
        # )),
    ):
        if not is_supported:
            continue
        contents = [
            map(lambda s: s.replace('/', os.sep), names)
            for names in contents
        ]
        for variant, params in base_class_list:
            variant = variant + sub_variant
            params = dict(params)
            params['contents'] = contents
            class_list.append((variant, params))

    for variant, params in class_list:
        class_name = base_class_name % variant
        class_dict = dict(base_class_dict)
        class_dict.update(params)
        class_dict['archive'] = variant
        globals()[class_name] = type(class_name, (ArchiveFormatTest, unittest.TestCase), class_dict)



xfail_list = [
    # No support for detecting solid RAR archives when using external tool.
    (ArchiveFormatRarExternalSolidFlatTest       , 'test_is_solid'),
    (ArchiveFormatRarExternalSolidOptEntryTest   , 'test_is_solid'),
    (ArchiveFormatRarExternalSolidGlobEntriesTest, 'test_is_solid'),
    (ArchiveFormatRarExternalSolidTreeTest       , 'test_is_solid'),
]

if 'win32' == sys.platform:
    xfail_list.extend([
        # Bug...
        (ArchiveFormatRarDllGlobEntriesTest     , 'test_iter_contents'),
        (ArchiveFormatRarDllGlobEntriesTest     , 'test_list_contents'),
        (ArchiveFormatRarDllGlobEntriesTest     , 'test_iter_extract' ),
        (ArchiveFormatRarDllGlobEntriesTest     , 'test_extract'      ),
        (ArchiveFormatRarDllSolidGlobEntriesTest, 'test_iter_contents'),
        (ArchiveFormatRarDllSolidGlobEntriesTest, 'test_list_contents'),
        (ArchiveFormatRarDllSolidGlobEntriesTest, 'test_iter_extract' ),
        (ArchiveFormatRarDllSolidGlobEntriesTest, 'test_extract'      ),
    ])

# Expected failures.
for klass, attr in xfail_list:
    setattr(klass, attr, unittest.expectedFailure(getattr(klass, attr)))


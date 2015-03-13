import hashlib
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


class UnsupportedFormat(Exception):

    def __init__(self, format):
        super(UnsupportedFormat, self).__init__('unsuported %s format' % format)

class UnsupportedOption(Exception):

    def __init__(self, format, option):
        super(UnsupportedOption, self).__init__('unsuported option for %s format: %s' % (format, option))

def make_archive(outfile, contents, format='zip', solid=False):
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
            cmd.extend(('--', outpath))
        elif 'lha' == format:
            if solid:
                raise UnsupportedOption(format, 'solid')
            cmd = ['lha', 'a', outpath, '--']
        elif 'rar' == format:
            cmd = ['rar', 'a', '-r']
            cmd.append('-s' if solid else '-s-')
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
        elif 'zip' == format:
            if solid:
                raise UnsupportedOption(format, 'solid')
            cmd = ['zip', '-r', outpath, '--']
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
    contents = ()
    archive = None

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
        if os.path.exists(cls.archive_path):
            return
        if 'win32' == sys.platform:
            raise Exception('archive creation unsupported on Windows!')
        make_archive(cls.archive_path,
                     [(name, filename)
                      for name, archive_name, filename
                      in cls.contents],
                     format=cls.format, solid=cls.solid)

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


for name, handler, is_available, format, not_solid, solid in (
    ('7z (external)'    , sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , '7z'     , True , True) ,
    ('7z (external) lha', sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , 'lha'    , True , False),
    ('7z (external) rar', sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , 'rar'    , True , True) ,
    ('7z (external) zip', sevenzip.SevenZipArchive   , sevenzip.SevenZipArchive.is_available()   , 'zip'    , True , False),
    ('tar'              , tar.TarArchive             , True                                      , 'tar'    , False, True) ,
    ('tar (gzip)'       , tar.TarArchive             , True                                      , 'tar.gz' , False, True) ,
    ('tar (bzip2)'      , tar.TarArchive             , True                                      , 'tar.bz2', False, True) ,
    ('rar (external)'   , rar.RarExecArchive         , rar.RarExecArchive.is_available()         , 'rar'    , True , True) ,
    ('rar (dll)'        , rarfile.UnrarDll           , rarfile.UnrarDll.is_available()           , 'rar'    , True , True) ,
    ('zip'              , zip.ZipArchive             , True                                      , 'zip'    , True , False),
    ('zip (external)'   , zip_external.ZipExecArchive, zip_external.ZipExecArchive.is_available(), 'zip'    , True , False),
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


# Expected failures.
for klass, attr in (
    # No support for detecting solid RAR archives when using external tool.
    (ArchiveFormatRarExternalSolidFlatTest, 'test_is_solid'),
    (ArchiveFormatRarExternalSolidTreeTest, 'test_is_solid'),
):
    setattr(klass, attr, unittest.expectedFailure(getattr(klass, attr)))


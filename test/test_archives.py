# coding: utf-8

import hashlib
import locale
import os
import re
import shutil
import sys
import tempfile
import unittest

from . import MComixTest, get_testfile_path

from mcomix import process
from mcomix.archive import (
    archive_recursive,
    lha_external,
    pdf_external,
    rar,
    rar_external,
    sevenzip_external,
    tar,
    zip,
    zip_external,
)
import mcomix


class UnsupportedFormat(Exception):

    def __init__(self, format):
        super(UnsupportedFormat, self).__init__('unsuported %s format' % format)

class UnsupportedOption(Exception):

    def __init__(self, format, option):
        super(UnsupportedOption, self).__init__('unsuported option for %s format: %s' % (format, option))

def make_archive(outfile, contents, format='zip', solid=False, password=None, header_encryption=False):
    if os.path.exists(outfile):
        raise Exception('%s already exists' % outfile)
    cleanup = []
    try:
        outpath = os.path.abspath(outfile)
        tmp_dir = tempfile.mkdtemp(dir=u'test/tmp', prefix=u'make_archive.')
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
                if header_encryption:
                    cmd.append('-mhe=on')
            else:
                assert not header_encryption
            cmd.extend(('--', outpath))
            # To avoid @ being treated as a special character...
            tmp_file = tempfile.NamedTemporaryFile(dir=u'test/tmp',
                                                   prefix=u'make_archive.',
                                                   delete=False)
            cleanup.append(lambda: os.unlink(tmp_file.name))
            for entry in entry_list:
                tmp_file.write(entry.encode(locale.getpreferredencoding()) + '\n')
            tmp_file.close()
            entry_list = ['@' + tmp_file.name]
        elif 'lha' == format:
            assert password is None
            assert not header_encryption
            if solid:
                raise UnsupportedOption(format, 'solid')
            cmd = ['lha', 'a', outpath, '--']
        elif 'rar' == format:
            cmd = ['rar', 'a', '-r']
            cmd.append('-s' if solid else '-s-')
            if password is not None:
                if header_encryption:
                    cmd.append('-hp' + password)
                else:
                    cmd.append('-p' + password)
            else:
                assert not header_encryption
            cmd.extend(('--', outpath))
        elif format.startswith('tar'):
            assert password is None
            assert not header_encryption
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
            assert not header_encryption
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

def md5(path):
    hash = hashlib.md5()
    hash.update(open(path, 'rb').read())
    return hash.hexdigest()

class ArchiveFormatTest(object):

    skip = None
    handler = None
    format = ''
    solid = False
    password = None
    header_encryption = False
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
        cls.archive_path = u'%s.%s' % (get_testfile_path('archives', cls.archive), cls.format)
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
                     [(name, get_testfile_path(filename))
                      for name, archive_name, filename
                      in cls.contents],
                     format=cls.format,
                     solid=cls.solid,
                     password=cls.password,
                     header_encryption=cls.header_encryption)

    def setUp(self):
        super(ArchiveFormatTest, self).setUp()
        self.dest_dir = tempfile.mkdtemp(prefix=u'extract.')
        self.archive = None

    def tearDown(self):
        if self.archive is not None:
            self.archive.close()
        super(ArchiveFormatTest, self).tearDown()

    def test_init_not_unicode(self):
        self.assertRaises(AssertionError, self.handler, 'test')

    def test_archive(self):
        self.archive = self.handler(self.archive_path)
        self.assertEqual(self.archive.archive, self.archive_path)

    def test_list_contents(self):
        self.archive = self.handler(self.archive_path)
        contents = self.archive.list_contents()
        self.assertItemsEqual(contents, self.archive_contents.keys())

    def test_iter_contents(self):
        self.archive = self.handler(self.archive_path)
        contents = []
        for name in self.archive.iter_contents():
            contents.append(name)
        self.assertItemsEqual(contents, self.archive_contents.keys())

    def test_is_solid(self):
        self.archive = self.handler(self.archive_path)
        self.archive.list_contents()
        self.assertEqual(self.solid, self.archive.is_solid())

    def test_iter_is_solid(self):
        self.archive = self.handler(self.archive_path)
        list(self.archive.iter_contents())
        self.assertEqual(self.solid, self.archive.is_solid())

    def test_extract(self):
        self.archive = self.handler(self.archive_path)
        contents = self.archive.list_contents()
        self.assertItemsEqual(contents, self.archive_contents.keys())
        # Use out-of-order extraction to try to trip implementation.
        for name in reversed(contents):
            self.archive.extract(name, self.dest_dir)
            path = os.path.join(self.dest_dir, name)
            self.assertTrue(os.path.isfile(path))
            extracted_md5 = md5(path)
            original_md5 = md5(get_testfile_path(self.archive_contents[name]))
            self.assertEqual((name, extracted_md5), (name, original_md5))

    def test_iter_extract(self):
        self.archive = self.handler(self.archive_path)
        contents = self.archive.list_contents()
        self.assertItemsEqual(contents, self.archive_contents.keys())
        extracted = []
        for name in self.archive.iter_extract(reversed(contents), self.dest_dir):
            extracted.append(name)
            path = os.path.join(self.dest_dir, name)
            self.assertTrue(os.path.isfile(path))
            extracted_md5 = md5(path)
            original_md5 = md5(get_testfile_path(self.archive_contents[name]))
            self.assertEqual((name, extracted_md5), (name, original_md5))
        # Entries must have been extracted in the order they are listed in the archive.
        # (necessary to prevent bad performances on solid archives)
        self.assertEqual(extracted, contents)


class RecursiveArchiveFormatTest(ArchiveFormatTest):

    base_handler = None

    def handler(self, archive):
        main_archive = self.base_handler(archive)
        return archive_recursive.RecursiveArchive(main_archive, self.dest_dir)


for name, handler, is_available, format, not_solid, solid, password, header_encryption in (
    ('7z (external)'    , sevenzip_external.SevenZipArchive, sevenzip_external.SevenZipArchive.is_available(), '7z'     , True , True , True , True  ),
    ('7z (external) lha', sevenzip_external.SevenZipArchive, sevenzip_external.SevenZipArchive.is_available(), 'lha'    , True , False, False, False ),
    ('7z (external) rar', sevenzip_external.SevenZipArchive, sevenzip_external.SevenZipArchive.is_available(), 'rar'    , True , True , True , True  ),
    ('7z (external) zip', sevenzip_external.SevenZipArchive, sevenzip_external.SevenZipArchive.is_available(), 'zip'    , True , False, True , False ),
    ('tar'              , tar.TarArchive                   , True                                            , 'tar'    , False, True , False, False ),
    ('tar (gzip)'       , tar.TarArchive                   , True                                            , 'tar.gz' , False, True , False, False ),
    ('tar (bzip2)'      , tar.TarArchive                   , True                                            , 'tar.bz2', False, True , False, False ),
    ('rar (external)'   , rar_external.RarArchive          , rar_external.RarArchive.is_available()          , 'rar'    , True , True , True , True  ),
    ('rar (dll)'        , rar.RarArchive                   , rar.RarArchive.is_available()                   , 'rar'    , True , True , True , True  ),
    ('zip'              , zip.ZipArchive                   , True                                            , 'zip'    , True , False, True , False ),
    ('zip (external)'   , zip_external.ZipArchive          , zip_external.ZipArchive.is_available()          , 'zip'    , True , False, True , False ),
):
    base_class_name = 'ArchiveFormat'
    base_class_name += ''.join([part.capitalize() for part in re.sub(r'[^\w]+', ' ', name).split()])
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
            variant = variant + 'Encrypted'
            params = dict(params)
            params['password'] = 'password'
            params['contents'] = (
                ('arg.jpeg', 'arg.jpeg', 'images/01-JPG-Indexed.jpg'),
                ('foo.JPG' , 'foo.JPG' , 'images/04-PNG-Indexed.png'),
                ('bar.jpg' , 'bar.jpg' , 'images/02-JPG-RGB.jpg'    ),
                ('meh.png' , 'meh.png' , 'images/03-PNG-RGB.png'    ),
            )
            class_list.append((variant, params))
            if header_encryption:
                variant = variant + 'Header'
                params = dict(params)
                params['header_encryption'] = True
                class_list.append((variant, params))
    else:
        assert not header_encryption

    for sub_variant, is_supported, contents in (
        ('Flat', True, (
            ('arg.jpeg'            , 'arg.jpeg'            , 'images/01-JPG-Indexed.jpg'),
            ('foo.JPG'             , 'foo.JPG'             , 'images/04-PNG-Indexed.png'),
            ('bar.jpg'             , 'bar.jpg'             , 'images/02-JPG-RGB.jpg'    ),
            ('meh.png'             , 'meh.png'             , 'images/03-PNG-RGB.png'    ),
        )),
        ('Tree', True, (
            ('dir1/arg.jpeg'       , 'dir1/arg.jpeg'       , 'images/01-JPG-Indexed.jpg'),
            ('dir1/subdir1/foo.JPG', 'dir1/subdir1/foo.JPG', 'images/04-PNG-Indexed.png'),
            ('dir2/subdir1/bar.jpg', 'dir2/subdir1/bar.jpg', 'images/02-JPG-RGB.jpg'    ),
            ('meh.png'             , 'meh.png'             , 'images/03-PNG-RGB.png'    ),
        )),
        ('Unicode', True, (
            (u'1-قفهسا.jpg'        , u'1-قفهسا.jpg'        , 'images/01-JPG-Indexed.jpg'),
            (u'2-רדןקמא.png'       , u'2-רדןקמא.png'       , 'images/04-PNG-Indexed.png'),
            (u'3-りえsち.jpg'      , u'3-りえsち.jpg'      , 'images/02-JPG-RGB.jpg'    ),
            (u'4-щжвщджл.png'      , u'4-щжвщджл.png'      , 'images/03-PNG-RGB.png'    ),
        )),
        # Check we don't treat an entry name as an option or command line switch.
        ('OptEntry', True, (
            ('-rg.jpeg'            , '-rg.jpeg'            , 'images/01-JPG-Indexed.jpg'),
            ('--o.JPG'             , '--o.JPG'             , 'images/04-PNG-Indexed.png'),
            ('+ar.jpg'             , '+ar.jpg'             , 'images/02-JPG-RGB.jpg'    ),
            ('@eh.png'             , '@eh.png'             , 'images/03-PNG-RGB.png'    ),
        )),
        # Check an entry name is not used as glob pattern.
        ('GlobEntries', 'win32' != sys.platform, (
            ('[rg.jpeg'            , '[rg.jpeg'            , 'images/01-JPG-Indexed.jpg'),
            ('[]rg.jpeg'           , '[]rg.jpeg'           , 'images/02-JPG-RGB.jpg'    ),
            ('*oo.JPG'             , '*oo.JPG'             , 'images/04-PNG-Indexed.png'),
            ('?eh.png'             , '?eh.png'             , 'images/03-PNG-RGB.png'    ),
            # ('\\r.jpg'             , '\\r.jpg'             , 'images/blue.png'          ),
            # ('ba\\.jpg'            , 'ba\\.jpg'            , 'images/red.png'           ),
        )),
        # Same, Windows version.
        ('GlobEntries', 'win32' == sys.platform, (
            ('[rg.jpeg'            , '[rg.jpeg'            , 'images/01-JPG-Indexed.jpg'),
            ('[]rg.jpeg'           , '[]rg.jpeg'           , 'images/02-JPG-RGB.jpg'    ),
            ('*oo.JPG'             , '_oo.JPG'             , 'images/04-PNG-Indexed.png'),
            ('?eh.png'             , '_eh.png'             , 'images/03-PNG-RGB.png'    ),
            # ('\\r.jpg'             , '\\r.jpg'             , 'images/blue.png'          ),
            # ('ba\\.jpg'            , 'ba\\.jpg'            , 'images/red.png'           ),
        )),
        # Check how invalid filesystem characters are handled.
        # ('InvalidFileSystemChars', 'win32' == sys.platform, (
        #     ('a<g.jpeg'            , 'a_g.jpeg'            ,'images/01-JPG-Indexed.jpg'),
        #     ('f*o.JPG'             , 'f_o.JPG'             ,'images/04-PNG-Indexed.png'),
        #     ('b:r.jpg'             , 'b_r.jpg'             ,'images/02-JPG-RGB.jpg'    ),
        #     ('m?h.png'             , 'm_h.png'             ,'images/03-PNG-RGB.png'    ),
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
        globals()[class_name] = type(class_name, (ArchiveFormatTest, MComixTest), class_dict)
        class_name = 'Recursive' + class_name
        class_dict = dict(class_dict)
        class_dict['base_handler'] = class_dict['handler']
        del class_dict['handler']
        globals()[class_name] = type(class_name, (RecursiveArchiveFormatTest, MComixTest), class_dict)



xfail_list = [
    # No support for detecting solid RAR archives when using external tool.
    ('RarExternalSolidFlat'       , 'test_is_solid'     ),
    ('RarExternalSolidFlat'       , 'test_iter_is_solid'),
    ('RarExternalSolidOptEntry'   , 'test_is_solid'     ),
    ('RarExternalSolidOptEntry'   , 'test_iter_is_solid'),
    ('RarExternalSolidGlobEntries', 'test_is_solid'     ),
    ('RarExternalSolidGlobEntries', 'test_iter_is_solid'),
    ('RarExternalSolidTree'       , 'test_is_solid'     ),
    ('RarExternalSolidTree'       , 'test_iter_is_solid'),
    ('RarExternalSolidUnicode'    , 'test_is_solid'     ),
    ('RarExternalSolidUnicode'    , 'test_iter_is_solid'),
    # No password support when using some external tools.
    ('RarExternalEncrypted'             , 'test_extract'      ),
    ('RarExternalEncrypted'             , 'test_iter_extract' ),
    ('RarExternalEncryptedHeader'       , 'test_extract'      ),
    ('RarExternalEncryptedHeader'       , 'test_iter_contents'),
    ('RarExternalEncryptedHeader'       , 'test_iter_extract' ),
    ('RarExternalEncryptedHeader'       , 'test_list_contents'),
    ('RarExternalSolidEncrypted'        , 'test_extract'      ),
    ('RarExternalSolidEncrypted'        , 'test_is_solid'     ),
    ('RarExternalSolidEncrypted'        , 'test_iter_is_solid'),
    ('RarExternalSolidEncrypted'        , 'test_iter_extract' ),
    ('RarExternalSolidEncryptedHeader'  , 'test_extract'      ),
    ('RarExternalSolidEncryptedHeader'  , 'test_is_solid'     ),
    ('RarExternalSolidEncryptedHeader'  , 'test_iter_is_solid'),
    ('RarExternalSolidEncryptedHeader'  , 'test_iter_contents'),
    ('RarExternalSolidEncryptedHeader'  , 'test_iter_extract' ),
    ('RarExternalSolidEncryptedHeader'  , 'test_list_contents'),
    ('ZipExternalEncrypted'             , 'test_extract'      ),
    ('ZipExternalEncrypted'             , 'test_iter_extract' ),
]

if 'win32' == sys.platform:
    xfail_list.extend([
        # Bug...
        ('RarDllGlobEntries'      , 'test_iter_contents'),
        ('RarDllGlobEntries'      , 'test_list_contents'),
        ('RarDllGlobEntries'      , 'test_iter_extract' ),
        ('RarDllGlobEntries'      , 'test_extract'      ),
        ('RarDllSolidGlobEntries' , 'test_iter_contents'),
        ('RarDllSolidGlobEntries' , 'test_list_contents'),
        ('RarDllSolidGlobEntries' , 'test_iter_extract' ),
        ('RarDllSolidGlobEntries' , 'test_extract'      ),
        # Not supported by 7z executable...
        ('7zExternalLhaUnicode'   , 'test_iter_contents'),
        ('7zExternalLhaUnicode'   , 'test_list_contents'),
        ('7zExternalLhaUnicode'   , 'test_iter_extract' ),
        ('7zExternalLhaUnicode'   , 'test_extract'      ),
        # Unicode not supported by the tar executable we used.
        ('TarBzip2SolidUnicode'   , 'test_iter_contents'),
        ('TarBzip2SolidUnicode'   , 'test_list_contents'),
        ('TarBzip2SolidUnicode'   , 'test_iter_extract' ),
        ('TarBzip2SolidUnicode'   , 'test_extract'      ),
        ('TarGzipSolidUnicode'    , 'test_iter_contents'),
        ('TarGzipSolidUnicode'    , 'test_list_contents'),
        ('TarGzipSolidUnicode'    , 'test_iter_extract' ),
        ('TarGzipSolidUnicode'    , 'test_extract'      ),
        ('TarSolidUnicode'        , 'test_iter_contents'),
        ('TarSolidUnicode'        , 'test_list_contents'),
        ('TarSolidUnicode'        , 'test_iter_extract' ),
        ('TarSolidUnicode'        , 'test_extract'      ),
        # Idem with unzip...
        ('ZipExternalUnicode'     , 'test_iter_contents'),
        ('ZipExternalUnicode'     , 'test_list_contents'),
        ('ZipExternalUnicode'     , 'test_iter_extract' ),
        ('ZipExternalUnicode'     , 'test_extract'      ),
        # ...and unrar!
        ('RarExternalUnicode'     , 'test_iter_contents'),
        ('RarExternalUnicode'     , 'test_list_contents'),
        ('RarExternalUnicode'     , 'test_iter_extract' ),
        ('RarExternalUnicode'     , 'test_extract'      ),
        ('RarExternalSolidUnicode', 'test_iter_contents'),
        ('RarExternalSolidUnicode', 'test_list_contents'),
        ('RarExternalSolidUnicode', 'test_iter_extract' ),
        ('RarExternalSolidUnicode', 'test_extract'      ),
    ])

# Expected failures.
for test, attr in xfail_list:
    for name in (
        'ArchiveFormat%sTest' % test,
        'RecursiveArchiveFormat%sTest' % test,
    ):
        if not name in globals():
            continue
        klass = globals()[name]
        setattr(klass, attr, unittest.expectedFailure(getattr(klass, attr)))


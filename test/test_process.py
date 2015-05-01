
import os
import shutil
import stat
import sys
import tempfile

from . import MComixTest

from mcomix import process


if 'win32' == sys.platform:

    def _is_valid_exe(name):
        return (name.endswith('.exe') and
                os.path.isabs(name) and
                os.path.isfile(exe))

else:
    def _is_valid_exe(name):
        return (os.path.isabs(name) and
                os.path.isfile(name) and
                os.access(exe, os.R_OK|os.X_OK))

def _create_file(path, rights='r'):
    mode = 0
    for r, m in (
        ('r', stat.S_IRUSR),
        ('w', stat.S_IWUSR),
        ('x', stat.S_IXUSR),
    ):
        if r in rights:
            mode |= m
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    open(path, 'w+b').close()
    os.chmod(path, mode)

def _create_tree(root, entries):
    for name, rights in entries:
        full_path = os.path.join(root, name)
        _create_file(full_path, rights)

class ProcessTest(MComixTest):

    def test_find_executable(self):
        cleanup = []
        try:
            root_dir = tempfile.mkdtemp(dir=u'test', prefix=u'tmp.path.')
            # cleanup.append(lambda: shutil.rmtree(root_dir))

            if 'win32' == sys.platform:
                orig_exe_dir = process._exe_dir
                cleanup.append(lambda: setattr(process, '_exe_dir', orig_exe_dir))
                process._exe_dir = 'dir4'
                tree = (
                    ('bin1.exe'         , 'rx'),
                    ('bin3.exe'         , 'rx'),
                    ('dir1/bin1.exe'    , 'rx'),
                    ('dir1/bin2'        , 'rx'),
                    ('dir2/bin1.exe'    , 'rx'),
                    ('dir3/bin2.exe'    , 'rx'),
                    ('dir3/bin4.exe'    , 'rx'),
                    ('dir3/dir/bin2.exe', 'rx'),
                    ('dir4/bin4.exe'    , 'rx'),
                    ('dir4/bin5.exe'    , 'rx'),
                )
                tests = (
                    # Absolute path, unchanged.
                    ([sys.executable]      , None  , sys.executable     ),
                    # Same without .exe extension.
                    ([sys.executable[:-4]] , None  , sys.executable     ),
                    # Must still be valid, though...
                    (['C:/invalid/invalid'], None  , None               ),
                    # bin1 in workdir should be picked up.
                    (['bin1.exe']          , None  , 'bin1.exe'         ),
                    (['bad', 'bin1.exe']   , None  , 'bin1.exe'         ),
                    # Same without .exe extension.
                    (['bin1']              , None  , 'bin1.exe'         ),
                    # bin2 in dir1 or bin2 @ind dir3 should not be picked up.
                    (['bin2']              , None  , 'dir3/bin2.exe'    ),
                    # Candidate with a directory component.
                    (['./bin3']            , None  , 'bin3.exe'         ),
                    # And a custom working directory.
                    (['dir/bin2']          , 'dir3', 'dir3/dir/bin2.exe'),
                    # Check main executable directory is searched too.
                    # (with higher priority than PATH)
                    (['bin4']              , None  , 'dir4/bin4.exe'    ),
                    # And work directory.
                    (['bin4']              , 'dir3', 'dir4/bin4.exe'    ),
                )
            else:
                tree = (
                    ('bin1'         , 'rx'),
                    ('bin3'         , 'rx'),
                    ('dir1/bin1'    , 'rx'),
                    ('dir1/bin2'    , 'r '),
                    ('dir2/bin1'    , 'rx'),
                    ('dir2/bin2'    , '  '),
                    ('dir3/bin1'    , 'rx'),
                    ('dir3/bin2'    , 'rx'),
                    ('dir3/bin3'    , 'r '),
                    ('dir3/bin4'    , 'rx'),
                    ('dir3/dir/bin2', 'rx'),
                    ('dir3/dir/bin3', 'rw '),
                )
                tests = (
                    # Absolute path, unchanged.
                    (['/bin/true']       , None  , '/bin/true'    ),
                    # Must still be valid, though...
                    (['/invalid/invalid'], None  , None           ),
                    # bin1 in workdir should not be picked up.
                    (['bin1']            , None  , 'dir1/bin1'    ),
                    # Check all candidates.
                    (['bad', 'bin1']     , None  , 'dir1/bin1'    ),
                    # bin2 in dir1 should not be picked up (not executable).
                    (['bin2']            , None  , 'dir3/bin2'    ),
                    # Same with bin3.
                    (['bin3']            , None  , None           ),
                    # Candidate with a directory component.
                    (['./bin3']          , None  , 'bin3'         ),
                    # And a custom working directory.
                    (['dir/bin2']        , 'dir3', 'dir3/dir/bin2'),
                    # But must still be valid...
                    (['dir/bin3']        , 'dir3', None           ),
                )

            _create_tree(root_dir, tree)

            root_dir = os.path.abspath(root_dir)

            orig_path = os.environ['PATH']
            cleanup.append(lambda: os.environ.__setitem__('PATH', orig_path))
            os.environ['PATH'] = os.pathsep.join('dir1 dir2 dir3'.split())

            orig_cwd = os.getcwd()
            cleanup.append(lambda: os.chdir(orig_cwd))
            os.chdir(root_dir)

            for candidates, workdir, expected in tests:
                if expected is not None:
                    if not os.path.isabs(expected):
                        expected = os.path.join(root_dir, expected)
                    expected = os.path.normpath(expected)
                result = process.find_executable(candidates, workdir=workdir)
                msg = (
                    'find_executable(%s, workdir=%s) failed; '
                    'returned %s instead of %s' % (
                        candidates, workdir,
                        result, expected,
                    )
                )
                self.assertEqual(result, expected, msg=msg)

        finally:
            for fn in reversed(cleanup):
                fn()


# -*- coding: utf-8 -*-

import os
import sys

# Useful to be able to run the current testsuite with another MComix version.
mcomix_path = os.environ.get('MCOMIXPATH', None)
if mcomix_path is not None:
    sys.path.insert(0, mcomix_path)

# Configure locale.

import locale

locale.setlocale(locale.LC_ALL, '')

# Since some of MComix' modules depend on gettext being installed for _(),
# add such a function here that simply returns the string passed into it.

import __builtin__

if '_' not in __builtin__.__dict__:
    __builtin__.__dict__['_'] = unicode

# Enable debug logging to make post-mortem analysis easier.

from mcomix import log

log.setLevel('DEBUG')

# Use a custom testcase class:
# - isolate tests: do not use or modify the user current
#   configuration for MComix (preferences, library, ...)
# - make sure MComix state is reset before each test

import shutil
import tempfile
import unittest

from mcomix.preferences import prefs

default_prefs = {}
default_prefs.update(prefs)

class MComixTest(unittest.TestCase):

    def setUp(self):
        base_tmpdir = os.path.join('test', 'tmp')
        if not os.path.exists(base_tmpdir):
            os.mkdir(base_tmpdir)
        name = '.'.join((
            self.__module__.split('.')[-1],
            self.__class__.__name__,
            self._testMethodName))
        self.tmp_dir = tempfile.mkdtemp(dir=base_tmpdir, prefix=u'%s.' % name)
        # Change storage directories.
        home_dir = os.path.join(self.tmp_dir, 'home')
        os.mkdir(home_dir)
        os.environ['HOME'] = home_dir
        os.environ['XDG_DATA_HOME'] = os.path.join(home_dir, 'data')
        os.environ['XDG_CONFIG_HOME'] = os.path.join(home_dir, 'config')
        # Create and setup temporary directory.
        temp_dir = os.path.join(self.tmp_dir, 'tmp')
        os.mkdir(temp_dir)
        os.environ['TMPDIR'] = os.environ['TEMP'] = os.environ['TMP'] = temp_dir
        # Make sure tempfile module uses the correct directory.
        tempfile.tempdir = temp_dir
        # Reset preferences to default.
        prefs.clear()
        prefs.update(default_prefs)

    def tearDown(self):
        name = '.'.join((
            self.__module__.split('.')[-1],
            self.__class__.__name__,
            self._testMethodName))
        failed = False
        if hasattr(self._resultForDoCleanups, '_excinfo'):
            # When running under py.test2
            exclist = self._resultForDoCleanups._excinfo
            if exclist is not None:
                for exc in exclist:
                    if 'XFailed' != exc.typename:
                        failed = True
                        break
        if hasattr(self._resultForDoCleanups, 'failures'):
            # When running under nosetest2
            for failure, traceback in self._resultForDoCleanups.failures:
                if failure.id() == self.id():
                    failed = True
                    break
        if not failed:
            shutil.rmtree(self.tmp_dir)

# Helper to get path to testsuite sample files.

def get_testfile_path(*components):
    return unicode(os.path.join(os.path.dirname(__file__), 'files', *components))


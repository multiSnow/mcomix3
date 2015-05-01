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
    __builtin__.__dict__['_'] = lambda text: unicode(text)

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
        # Change storage directories.
        self.home_dir = tempfile.mkdtemp(dir=u'test', prefix=u'tmp.home.')
        os.environ['HOME'] = self.home_dir
        os.environ['XDG_DATA_HOME'] = os.path.join(self.home_dir, 'data')
        os.environ['XDG_CONFIG_HOME'] = os.path.join(self.home_dir, 'config')
        # Reset preferences to default.
        prefs.clear()
        prefs.update(default_prefs)

    def tearDown(self):
        shutil.rmtree(self.home_dir)


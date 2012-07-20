# -*- coding: utf-8 -*-

import unittest
import tempfile
import os

from mcomix import constants
from mcomix import last_read_page
from mcomix.library import backend

class OpenLastPageBasicTest(unittest.TestCase):
    def setUp(self):
        # Database file
        fp, self.db = tempfile.mkstemp('.db', 'mcomix-test')
        os.close(fp)
        constants.LIBRARY_DATABASE_PATH = self.db

        # Dummy archive (files are checked for existance)
        self.archive1 = os.path.abspath(u'test/files/archives/01-ZIP-Normal.zip')
        self.archive2 = os.path.abspath(u'test/files/archives/02-TAR-Normal.tar')

        # Library backend
        self.backend = backend.LibraryBackend()

        self.lastread = last_read_page.LastReadPage(self.backend)
        self.lastread.set_enabled(True)

    def tearDown(self):
        self.backend.close()
        os.unlink(self.db)

    def test_init(self):
        self.assertEqual(0, self.lastread.count())

    def test_count(self):
        self.lastread.set_page(self.archive1, 1)
        self.assertEqual(1, self.lastread.count())
        self.lastread.set_page(self.archive2, 1)
        self.assertEqual(2, self.lastread.count())

    def test_set_last_page(self):
        self.lastread.set_page(self.archive1, 1)
        self.assertEqual(1, self.lastread.get_page(self.archive1))

    def test_multiple_archives(self):
        self.lastread.set_page(self.archive1, 1)
        self.lastread.set_page(self.archive2, 2)

        self.assertEqual(1, self.lastread.get_page(self.archive1))
        self.assertEqual(2, self.lastread.get_page(self.archive2))

    def test_clear_page(self):
        self.lastread.set_page(self.archive1, 1)
        self.lastread.clear_page(self.archive1)
        self.assertIsNone(self.lastread.get_page(self.archive1))

    def test_clear_all(self):
        self.lastread.set_page(self.archive1, 1)
        self.lastread.clear_all()
        self.assertEqual(0, self.lastread.count())

    def test_overwrite(self):
        self.lastread.set_page(self.archive1, 1)
        self.assertEqual(1, self.lastread.get_page(self.archive1))
        self.lastread.set_page(self.archive1, 2)
        self.assertEqual(2, self.lastread.get_page(self.archive1))

    def test_enabled(self):
        self.lastread.set_enabled(False)
        self.lastread.set_page(self.archive1, 1)
        self.assertIsNone(self.lastread.get_page(self.archive1))

    def test_nonexistant_file(self):
        self.assertRaises(ValueError, self.lastread.set_page,
            '/root/mcomix/file-that-should-not-exist-hopefully', 1)

    def test_invalid_page(self):
        self.assertRaises(ValueError, self.lastread.set_page,
            self.archive1, 0)
        self.assertRaises(ValueError, self.lastread.set_page,
            self.archive1, -1)

    def test_date(self):
        self.lastread.set_page(self.archive1, 1)
        self.assertIsNotNone(self.lastread.get_date(self.archive1))

    def test_reopen(self):
        self.lastread.set_page(self.archive1, 1)
        self.lastread.set_page(self.archive2, 2)
        self.assertEqual(1, self.lastread.get_page(self.archive1))
        self.assertEqual(2, self.lastread.get_page(self.archive2))

        self.backend.close()
        self.backend = backend.LibraryBackend()
        self.lastread = last_read_page.LastReadPage(self.backend)
        self.lastread.set_enabled(True)

        self.assertEqual(1, self.lastread.get_page(self.archive1),
                'Page should be remembered after shutdown')
        self.assertEqual(2, self.lastread.get_page(self.archive2),
                'Page should be remembered after shutdown')

# vim: expandtab:sw=4:ts=4

# -*- coding: utf-8 -*-

import unittest
import tempfile
import os

from mcomix import last_read_page

class OpenLastPageBasicTest(unittest.TestCase):
    def setUp(self):
        # Database file
        fp, self.db = tempfile.mkstemp('.db', 'mcomix-test')
        os.close(fp)
        # Dummy archive (files are checked for existance)
        fp, self.archive1 = tempfile.mkstemp('.zip', 'test-archive')
        os.close(fp)
        fp, self.archive2 = tempfile.mkstemp('.rar', 'test-archive')
        os.close(fp)

        self.lastread = last_read_page.LastReadPage(self.db)
        self.lastread.set_enabled(True)

    def tearDown(self):
        self.lastread.cleanup()
        os.unlink(self.db)
        os.unlink(self.archive1)
        os.unlink(self.archive2)

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

    def test_cleanup(self):
        self.lastread.cleanup()
        self.assertFalse(self.lastread.enabled)

        # Closing twice shouldn't lead to exception
        self.lastread.cleanup()

    def test_reopen(self):
        self.lastread.set_page(self.archive1, 1)
        self.lastread.set_page(self.archive2, 2)
        self.assertEqual(1, self.lastread.get_page(self.archive1))
        self.assertEqual(2, self.lastread.get_page(self.archive2))

        self.lastread.cleanup()
        self.lastread = last_read_page.LastReadPage(self.db)
        self.lastread.set_enabled(True)

        self.assertEqual(1, self.lastread.get_page(self.archive1),
                'Page should be remembered after shutdown')
        self.assertEqual(2, self.lastread.get_page(self.archive2),
                'Page should be remembered after shutdown')

# vim: expandtab:sw=4:ts=4

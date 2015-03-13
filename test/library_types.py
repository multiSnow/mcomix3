import unittest
import tempfile
import shutil
import os

from mcomix import constants
from mcomix.library import backend
from mcomix.library import backend_types

class CollectionTest(unittest.TestCase):

    def setUp(self):
        # Database file
        fp, self.db = tempfile.mkstemp('.db', 'mcomix-test')
        os.close(fp)

        # Initialize library (path must be patched for testing)
        constants.LIBRARY_DATABASE_PATH = self.db
        self.library = backend.LibraryBackend()

        # Initialize database
        self.library.add_collection("Test")
        self.library.add_collection("Subtest")
        test_col = self.library.get_collection_by_name("Test")
        sub_col = self.library.get_collection_by_name("Subtest")
        test_col.add_collection(sub_col)
        # There is also a collection Recent that is added by default!

        # Add first two archives to no collection, remaining two
        # to subcollections.
        directory = 'test/files/archives'
        zip_archive = unicode(os.path.join(directory, '01-ZIP-Normal.zip'))
        tar_archive = unicode(os.path.join(directory, '02-TAR-Normal.tar'))
        rar_archive = unicode(os.path.join(directory, '03-RAR-Normal.rar'))
        sz_archive = unicode(os.path.join(directory, '04-7Z-Normal.7z'))

        self.library.add_book(zip_archive, None)
        self.library.add_book(tar_archive, None)
        self.library.add_book(rar_archive, test_col.id)
        self.library.add_book(sz_archive, sub_col.id)
 
    def tearDown(self):
        self.library.close()
        # Remove singleton instance
        backend._backend = None
        os.unlink(self.db)

    def test_get_books_default(self):
        default_col = backend_types.DefaultCollection

        # All books
        books = default_col.get_books()
        self.assertEqual(len(books), 4)
        # Only RAR
        books = default_col.get_books('rar')
        self.assertEqual(len(books), 1)
        # No matches
        books = default_col.get_books('NOMATCH')
        self.assertEqual(len(books), 0)

    def test_get_books_normal_collection(self):
        test_col = self.library.get_collection_by_name("Test")

        # Two books should be stored (including subcollections)
        self.assertEqual(len(test_col.get_books()), 2)
        # Only RAR
        self.assertEqual(len(test_col.get_books('rar')), 1)
        # ZIP shouldn't be included
        self.assertEqual(len(test_col.get_books('zip')), 0)

    def test_get_book_with_attribs(self):
        books = backend_types.DefaultCollection.get_books('zip')

        self.assertEqual(len(books), 1)

        zipbook = books[0]
        self.assertEqual(zipbook.id, 1)
        self.assertEqual(zipbook.pages, 4)

    def test_add_subcollection_normal_collection(self):
        test_col = self.library.get_collection_by_name("Test")

        self.library.add_collection("New test")
        new_col  = self.library.get_collection_by_name("New test")
        test_col.add_collection(new_col)

        self.assertIsNone(test_col.supercollection, None)
        self.assertEqual(new_col.supercollection, test_col.id)

    def test_get_collections_default(self):
        col = backend_types.DefaultCollection
        root_collections = col.get_collections()

        self.assertEqual(len(root_collections), 2)
        self.assertEqual(root_collections[1].name, "Test")

    def test_get_collections_normal_collection(self):
        col = self.library.get_collection_by_name("Test")
        root_collections = col.get_collections()

        self.assertEqual(len(root_collections), 1)
        self.assertEqual(root_collections[0].name, "Subtest")

    def test_equal(self):
        test_col1 = self.library.get_collection_by_name("Test")
        test_col2 = self.library.get_collection_by_name("Test")
        other = 123

        self.assertEqual(test_col1, test_col2)
        self.assertNotEqual(test_col1, other)

    def test_get_all_collections(self):
        all_cols = backend_types.DefaultCollection.get_all_collections()
        self.assertEqual(len(all_cols), 3)

        col = self.library.get_collection_by_name("Test")
        subcol = self.library.get_collection_by_name("Subtest")
        self.library.add_collection("New test")
        new_col  = self.library.get_collection_by_name("New test")
        subcol.add_collection(new_col)

        self.assertEqual(len(backend_types.DefaultCollection.get_all_collections()), 4)
        self.assertEqual(len(col.get_all_collections()), 2)

    def test_get_default_collection(self):
        collection = self.library.get_collection_by_id(None)
        self.assertEqual(collection, backend_types.DefaultCollection)
    

class WatchListEntryTest(unittest.TestCase):

    def test_invalid_dir(self):
        tmpdir = tempfile.mkdtemp(dir=u'test', prefix=u'tmp.library_types.')
        entry = backend_types._WatchListEntry(os.path.join(tmpdir, "invalid-directory"), False, None)
        self.assertFalse(entry.is_valid())
        self.assertIsInstance(entry.get_new_files([]), list)
        self.assertEqual(len(entry.get_new_files([])), 0)
        shutil.rmtree(tmpdir)

    def test_valid_dir(self):
        tmpdir = os.path.abspath(tempfile.mkdtemp(dir=u'test', prefix=u'tmp.library_types.'))
        directory = unicode(os.path.abspath('test/files/archives'))
        available = [u'01-ZIP-Normal.zip', u'02-TAR-Normal.tar']
        others = [u'03-RAR-Normal.rar', u'04-7Z-Normal.7z']
        for entry_list in (available, others):
            for n, entry in enumerate(entry_list):
                src = os.path.join(directory, entry)
                dst = os.path.join(tmpdir, entry)
                shutil.copy(src, dst)
                entry_list[n] = dst

        entry = backend_types._WatchListEntry(tmpdir, True, None)
        new_files = entry.get_new_files(available)
        new_files.sort()

        self.assertIsInstance(new_files, list)
        self.assertEqual(new_files, others)

        shutil.rmtree(tmpdir)

# vim: expandtab:sw=4:ts=4

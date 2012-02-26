""" Data class for library books and collections. """

import os

from mcomix import constants


class _BackendObject(object):

    def get_backend(self):
        # XXX: Delayed import to avoid circular import
        from mcomix.library.backend import LibraryBackend
        return LibraryBackend()


class _Book(_BackendObject):
    """ Library book instance. """

    def __init__(self, id, name, path, pages, format, size, added):
        """ Creates a book instance.
        @param id: Book id
        @param name: Base name of the book
        @param path: Full path to the book
        @param pages: Number of pages
        @param format: One of the archive formats in L{constants}
        @param size: File size in bytes
        @param added: Datetime when book was added to library """

        self.id = id
        self.name = name
        self.path = path
        self.pages = pages
        self.format = format
        self.size = size
        self.added = added


class _Collection(_BackendObject):
    """ Library collection instance. 
    This class should NOT be instianted directly, but only with methods from
    L{LibraryBackend} instead. """

    def __init__(self, id, name, supercollection=None):
        """ Creates a collection instance.
        @param id: Collection id
        @param name: Name of the collection
        @param supercollection: Parent collection, or C{None} """

        self.id = id
        self.name = name
        self.supercollection = supercollection

    def __eq__(self, other):
        if isinstance(other, _Collection):
            return self.id == other.id
        else:
            return False

    def get_books(self, filter_string=None):
        """ Returns all books that are part of this collection,
        including subcollections. """

        books = []
        for collection in [ self ] + self.get_all_collections():
            sql = '''SELECT book.id, book.name, book.path, book.pages, book.format,
                            book.size, book.added
                     FROM book
                     JOIN contain ON contain.book = book.id
                                     AND contain.collection = ?
                  '''

            sql_args = [collection.id]
            if filter_string:
                sql += ''' WHERE book.name LIKE '%' || ? || '%' '''
                sql_args.append(filter_string)

            cursor = self.get_backend().execute(sql, sql_args)
            rows = cursor.fetchall()
            cursor.close()

            books.extend([ _Book(*cols) for cols in rows ])

        return books

    def get_collections(self):
        """ Returns a list of all direct subcollections of this instance. """

        cursor = self.get_backend().execute('''SELECT id, name, supercollection
                FROM collection
                WHERE supercollection = ?
                ORDER by name''', [self.id])
        result = cursor.fetchall()
        cursor.close()

        return [ _Collection(*row) for row in result ]

    def get_all_collections(self):
        """ Returns all collections that are subcollections of this instance,
        or subcollections of a subcollection of this instance. """

        to_search = [ self ]
        collections = [ ]
        # This assumes that the library is built like a tree, so no circular references.
        while len(to_search) > 0:
            collection = to_search.pop()
            subcollections = collection.get_collections()
            collections.extend(subcollections)
            to_search.extend(subcollections)

        return collections

    def add_collection(self, subcollection):
        """ Sets C{subcollection} as child of this collection. """

        self.get_backend().execute('''UPDATE collection
                SET supercollection = ?
                WHERE id = ?''', (self.id, subcollection.id))
        subcollection.supercollection = self.id


class _DefaultCollection(_Collection):
    """ Represents the default collection that books belong to if
    no explicit collection was specified. """

    def __init__(self):

        self.id = None
        self.name = _("All books")
        self.supercollection = None

    def get_books(self, filter_string=None):
        """ Returns all books in the library """
        sql = '''SELECT book.id, book.name, book.path, book.pages, book.format,
                        book.size, book.added
                 FROM book
              '''

        sql_args = []
        if filter_string:
            sql += ''' WHERE book.name LIKE '%' || ? || '%' '''
            sql_args.append(filter_string)

        cursor = self.get_backend().execute(sql, sql_args)
        rows = cursor.fetchall()
        cursor.close()

        return [ _Book(*cols) for cols in rows ]

    def add_collection(self, subcollection):
        """ Removes C{subcollection} from any supercollections and moves
        it to the root level of the tree. """

        assert subcollection is not DefaultCollection, "Cannot change DefaultCollection"

        self.get_backend().execute('''UPDATE collection
                SET supercollection = NULL
                WHERE id = ?''', (subcollection.id,))
        subcollection.supercollection = None

    def get_collections(self):
        """ Returns a list of all root collections. """
        
        cursor = self.get_backend().execute('''SELECT id, name, supercollection
                FROM collection
                WHERE supercollection IS NULL
                ORDER by name''')
        result = cursor.fetchall()
        cursor.close()

        return [ _Collection(*row) for row in result ]


DefaultCollection = _DefaultCollection()


class _WatchList(object):
    """ Scans watched directories and updates the database when new books have
    been added. This object is part of the library backend, i.e.
    C{library.backend.watchlist}. """

    def __init__(self, backend):
        self.backend = backend

    def add_directory(self, path, collection=DefaultCollection):
        """ Adds a new watched directory. """

        directory = os.path.abspath(path)
        sql = """INSERT OR IGNORE INTO watchlist (path, collection)
                 VALUES (?, ?)"""
        cursor = self.backend.execute(sql, [directory, collection.id])
        cursor.close()

    def get_watchlist(self):
        """ Returns a list of watched directories.
        @return: List of L{_WatchListEntry} objects. """

        sql = """SELECT watchlist.path,
                        collection.id, collection.name,
                        collection.supercollection
                 FROM watchlist
                 LEFT JOIN collection ON watchlist.collection = collection.id"""

        cursor = self.backend.execute(sql)
        entries = []
        for row in cursor.fetchall():
            collection_id = row[1]
            if collection_id:
                collection = _Collection(*row[1:])
            else:
                collection = DefaultCollection

            entries.append(_WatchListEntry(row[0], collection))

        return entries


class _WatchListEntry(_BackendObject):
    """ A watched directory. """

    def __init__(self, directory, collection):
        self.directory = os.path.abspath(directory)
        self.collection = collection

    def get_new_files(self, filelist):
        """ Returns a list of files that are present in the watched directory,
        but not in the list of files passed in C{filelist}. """

        if not self.is_valid():
            return []

        old_files = frozenset([os.path.abspath(path) for path in filelist])
        available_files = frozenset([os.path.join(self.directory, filename)
            for filename in os.listdir(self.directory)
            if constants.SUPPORTED_ARCHIVE_REGEX.search(filename)])

        return list(available_files.difference(old_files))

    def is_valid(self):
        """ Check if the watched directory is a valid directory and exists. """
        return os.path.isdir(self.directory)

    def remove(self):
        """ Removes this entry from the watchlist, deleting its associated
        path from the database. """
        sql = """DELETE FROM watchlist WHERE path = ?"""
        cursor = self.get_backend().execute(sql, (self.directory,))
        cursor.close()

        self.directory = u""
        self.collection = None

    def set_collection(self, new_collection):
        """ Updates the collection associated with this watchlist entry. """
        if new_collection != self.collection:
            sql = """UPDATE watchlist SET collection = ? WHERE path = ?"""
            cursor = self.get_backend().execute(sql,
                    (new_collection.id, self.directory))
            cursor.close()
            self.collection = new_collection


# vim: expandtab:sw=4:ts=4

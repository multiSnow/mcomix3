""" Data class for library books and collections. """

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


class _WatchListEntry(_BackendObject):
    """ A watched directory. """

    def __init__(self, directory, collection):
        self.directory = directory
        self.collection = collection


# vim: expandtab:sw=4:ts=4

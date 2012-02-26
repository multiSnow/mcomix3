"""library_backend.py - Comic book library backend using sqlite."""

import os

from mcomix import archive_tools
from mcomix import constants
from mcomix import thumbnail_tools
from mcomix import log
from mcomix.library import backend_types

try:
    from sqlite3 import dbapi2
except ImportError:
    try:
        from pysqlite2 import dbapi2
    except ImportError:
        log.warning( _('! Could neither find pysqlite2 nor sqlite3.') )
        dbapi2 = None


class _LibraryBackend:

    """The LibraryBackend handles the storing and retrieval of library
    data to and from disk.
    """

    #: Current version of the library database structure.
    # See method _upgrade_database() for changes between versions.
    DB_VERSION = 2

    def __init__(self):

        def row_factory(cursor, row):
            """Return rows as sequences only when they have more than
            one element.
            """
            if len(row) == 1:
                return row[0]
            return row

        self._con = dbapi2.connect(constants.LIBRARY_DATABASE_PATH)
        self._con.row_factory = row_factory

        self.watchlist = backend_types._WatchList(self)

        version = self._library_version()
        self._upgrade_database(version, _LibraryBackend.DB_VERSION)

    def get_books_in_collection(self, collection=None, filter_string=None):
        """Return a sequence with all the books in <collection>, or *ALL*
        books if <collection> is None. If <filter_string> is not None, we
        only return books where the <filter_string> occurs in the path.
        """
        if collection is None:
            if filter_string is None:
                cur = self._con.execute('''select id from Book''')
            else:
                cur = self._con.execute('''select id from Book
                    where path like ?''', ("%%%s%%" % filter_string, ))

            return cur.fetchall()
        else:
            books = []
            subcollections = self.get_all_collections_in_collection(collection)
            for coll in [ collection ] + subcollections:
                if filter_string is None:
                    cur = self._con.execute('''select id from Book
                        where id in (select book from Contain where collection = ?)
                        ''', (coll,))
                else:
                    cur = self._con.execute('''select id from Book
                        where id in (select book from Contain where collection = ?)
                        and path like ?''', (coll, "%%%s%%" % filter_string))
                books.extend(cur.fetchall())
            return books

    def get_book_cover(self, book):
        """Return a pixbuf with a thumbnail of the cover of <book>, or
        None if the cover can not be fetched.
        """
        try:
            path = self._con.execute('''select path from Book
                where id = ?''', (book,)).fetchone()
        except Exception:
            log.error( _('! Non-existant book #%i'), book )
            return None

        return self.get_book_thumbnail(path)

    def get_book_path(self, book):
        """Return the filesystem path to <book>, or None if <book> isn't
        in the library.
        """
        try:
            path = self._con.execute('''select path from Book
                where id = ?''', (book,)).fetchone()
        except Exception:
            log.error( _('! Non-existant book #%i'), book )
            return None

        return path

    def get_book_thumbnail(self, path):
        """ Returns a pixbuf with a thumbnail of the cover of the book at <path>,
        or None, if no thumbnail could be generated. """

        thumbnailer = thumbnail_tools.Thumbnailer(dst_dir=constants.LIBRARY_COVERS_PATH)
        thumbnailer.set_store_on_disk(True)
        # This is the maximum image size allowed by the library, so that thumbnails might be downscaled,
        # but never need to be upscaled (and look ugly)
        thumbnailer.set_size(constants.MAX_LIBRARY_COVER_SIZE, constants.MAX_LIBRARY_COVER_SIZE)
        thumb = thumbnailer.thumbnail(path)

        if thumb is None: log.warning( _('! Could not get cover for book "%s"'), path )
        return thumb

    def get_book_name(self, book):
        """Return the name of <book>, or None if <book> isn't in the
        library.
        """
        cur = self._con.execute('''select name from Book
            where id = ?''', (book,))
        name = cur.fetchone()
        if name is not None:
            return name
        else:
            return None

    def get_book_pages(self, book):
        """Return the number of pages in <book>, or None if <book> isn't
        in the library.
        """
        cur = self._con.execute('''select pages from Book
            where id = ?''', (book,))
        return cur.fetchone()

    def get_book_format(self, book):
        """Return the archive format of <book>, or None if <book> isn't
        in the library.
        """
        cur = self._con.execute('''select format from Book
            where id = ?''', (book,))
        return cur.fetchone()

    def get_book_size(self, book):
        """Return the size of <book> in bytes, or None if <book> isn't
        in the library.
        """
        cur = self._con.execute('''select size from Book
            where id = ?''', (book,))
        return cur.fetchone()

    def get_collections_in_collection(self, collection=None):
        """Return a sequence with all the subcollections in <collection>,
        or all top-level collections if <collection> is None.
        """
        if collection is None:
            cur = self._con.execute('''select id from Collection
                where supercollection isnull
                order by name''')
        else:
            cur = self._con.execute('''select id from Collection
                where supercollection = ?
                order by name''', (collection,))
        return cur.fetchall()

    def get_all_collections_in_collection(self, collection):
        """ Returns a sequence of <all> subcollections in <collection>,
        that is, even subcollections that are again a subcollection of one
        of the previous subcollections. """

        if collection is None: raise ValueError("Collection must not be <None>")

        to_search = [ collection ]
        collections = [ ]
        # This assumes that the library is built like a tree, so no circular references.
        while len(to_search) > 0:
            collection = to_search.pop()
            subcollections = self.get_collections_in_collection(collection)
            collections.extend(subcollections)
            to_search.extend(subcollections)

        return collections

    def get_all_collections(self):
        """Return a sequence with all collections (flattened hierarchy).
        The sequence is sorted alphabetically by collection name.
        """
        cur = self._con.execute('''select id from Collection
            order by name''')
        return cur.fetchall()

    def get_collection_name(self, collection):
        """Return the name field of the <collection>, or None if the
        collection does not exist.
        """
        cur = self._con.execute('''select name from Collection
            where id = ?''', (collection,))
        name = cur.fetchone()
        if name is not None:
            return name
        else:
            return None

    def get_collection_by_name(self, name):
        """Return the collection called <name>, or None if no such
        collection exists. Names are unique, so at most one such collection
        can exist.
        """
        cur = self._con.execute('''select id, name, supercollection
            from collection
            where name = ?''', (name,))
        result = cur.fetchone()
        cur.close()
        if result:
            return backend_types._Collection(*result)
        else:
            return None

    def get_supercollection(self, collection):
        """Return the supercollection of <collection>."""
        cur = self._con.execute('''select supercollection from Collection
            where id = ?''', (collection,))
        return cur.fetchone()

    def add_book(self, path, collection=None):
        """Add the archive at <path> to the library. If <collection> is
        not None, it is the collection that the books should be put in.
        Return True if the book was successfully added (or was already
        added).
        """
        path = os.path.abspath(path)
        name = os.path.basename(path)
        info = archive_tools.get_archive_info(path)
        if info is None:
            return False
        format, pages, size = info

        # Thumbnail for the newly added book will be generated once it
        # is actually needed with get_book_thumbnail().
        old = self._con.execute('''select id from Book
            where path = ?''', (path,)).fetchone()
        try:
            if old is not None:
                self._con.execute('''update Book set
                    name = ?, pages = ?, format = ?, size = ?
                    where path = ?''', (name, pages, format, size, path))
            else:
                self._con.execute('''insert into Book
                    (name, path, pages, format, size)
                    values (?, ?, ?, ?, ?)''',
                    (name, path, pages, format, size))
        except dbapi2.Error:
            log.error( _('! Could not add book "%s" to the library'), path )
            return False
        if collection is not None:
            book = self._con.execute('''select id from Book
                where path = ?''', (path,)).fetchone()
            self.add_book_to_collection(book, collection)
        return True

    def add_collection(self, name):
        """Add a new collection with <name> to the library. Return True
        if the collection was successfully added.
        """
        try:
            self._con.execute('''insert into Collection
                (name) values (?)''', (name,))
            return True
        except dbapi2.Error:
            log.error( _('! Could not add collection "%s"'), name )
        return False

    def add_book_to_collection(self, book, collection):
        """Put <book> into <collection>."""
        try:
            self._con.execute('''insert into Contain
                (collection, book) values (?, ?)''', (collection, book))
        except dbapi2.DatabaseError: # E.g. book already in collection.
            pass
        except dbapi2.Error:
            log.error( _('! Could not add book %(book)s to collection %(collection)s'),
                {"book" : book, "collection" : collection} )

    def add_collection_to_collection(self, subcollection, supercollection):
        """Put <subcollection> into <supercollection>, or put
        <subcollection> in the root if <supercollection> is None.
        """
        if supercollection is None:
            self._con.execute('''update Collection
                set supercollection = NULL
                where id = ?''', (subcollection,))
        else:
            self._con.execute('''update Collection
                set supercollection = ?
                where id = ?''', (supercollection, subcollection))

    def rename_collection(self, collection, name):
        """Rename the <collection> to <name>. Return True if the renaming
        was successful.
        """
        try:
            self._con.execute('''update Collection set name = ?
                where id = ?''', (name, collection))
            return True
        except dbapi2.DatabaseError: # E.g. name taken.
            pass
        except dbapi2.Error:
            log.error( _('! Could not rename collection to "%s"'), name )
        return False

    def duplicate_collection(self, collection):
        """Duplicate the <collection> by creating a new collection
        containing the same books. Return True if the duplication was
        successful.
        """
        name = self.get_collection_name(collection)
        if name is None: # Original collection does not exist.
            return False
        copy_name = name + ' ' + _('(Copy)')
        while self.get_collection_by_name(copy_name):
            copy_name = copy_name + ' ' + _('(Copy)')
        if self.add_collection(copy_name) is None: # Could not create the new.
            return False
        copy_collection = self._con.execute('''select id from Collection
            where name = ?''', (copy_name,)).fetchone()
        self._con.execute('''insert or ignore into Contain (collection, book)
            select ?, book from Contain
            where collection = ?''', (copy_collection, collection))
        return True

    def clean_collection(self, collection=None):
        """ Removes files from <collection> that no longer exist. If <collection>
        is None, all collections are cleaned. Returns the number of deleted books. """
        book_ids = self.get_books_in_collection(collection)
        deleted = 0
        for id in book_ids:
            path = self.get_book_path(id)
            if path and not os.path.isfile(path):
                self.remove_book(id)
                deleted += 1

        return deleted

    def remove_book(self, book):
        """Remove the <book> from the library."""
        path = self.get_book_path(book)
        if path is not None:
            thumbnailer = thumbnail_tools.Thumbnailer(dst_dir=constants.LIBRARY_COVERS_PATH)
            thumbnailer.delete(path)
        self._con.execute('delete from Book where id = ?', (book,))
        self._con.execute('delete from Contain where book = ?', (book,))

    def remove_collection(self, collection):
        """Remove the <collection> (sans books) from the library."""
        self._con.execute('delete from Collection where id = ?', (collection,))
        self._con.execute('delete from Contain where collection = ?',
            (collection,))
        self._con.execute('''update Collection set supercollection = NULL
            where supercollection = ?''', (collection,))

    def remove_book_from_collection(self, book, collection):
        """Remove <book> from <collection>."""
        self._con.execute('''delete from Contain
            where book = ? and collection = ?''', (book, collection))

    def execute(self, *args):
        """ Passes C{args} directly to the C{execute} method of the SQL
        connection. """
        return self._con.execute(*args)

    def close(self):
        """Commit changes and close cleanly."""
        self._con.commit()
        self._con.close()

    def _table_exists(self, table):
        """ Checks if C{table} exists in the database. """
        cursor = self._con.cursor()
        exists = cursor.execute('pragma table_info(%s)' % table).fetchone() is not None
        cursor.close()
        return exists

    def _library_version(self):
        """ Examines the library database structure to determine
        which version of MComix created it.

        @return C{version} from the table C{Info} if available,
        C{0} otherwise. C{-1} if the database has not been created yet."""

        # Check if Comix' tables exist
        tables = ('book', 'collection', 'contain')
        for table in tables:
            if not self._table_exists(table):
                return -1

        if self._table_exists('info'):
            cursor = self._con.cursor()
            version = cursor.execute('''select value from info
                where key = 'version' ''').fetchone()
            cursor.close()

            if not version:
                log.warning(_('Could not determine library database version!'))
                return -1
            else:
                return int(version)
        else:
            # Comix database format
            return 0

    def _create_tables(self):
        """ Creates all required tables in the database. """
        self._create_table_book()
        self._create_table_collection()
        self._create_table_contain()
        self._create_table_info()
        self._create_table_watchlist()

    def _upgrade_database(self, from_version, to_version):
        """ Performs sequential upgrades to the database, bringing
        it from C{from_version} to C{to_version}. If C{from_version}
        is -1, the database structure will simply be re-created at the
        current version. """

        if from_version == -1:
            self._create_tables()
            return

        if from_version != to_version:
            upgrades = range(from_version, to_version)
            log.info(_("Upgrading library database version from %(from)d to %(to)d."),
                { "from" : from_version, "to" : to_version })

            if 0 in upgrades:
                # Upgrade from Comix database structure to DB version 1
                # (Added table 'info')
                self._create_table_info()

            if 1 in upgrades:
                # Upgrade to database structure version 2.
                # (Added table 'watchlist' for storing auto-add directories)
                self._create_table_watchlist()

            self._con.execute('''update info set value = ? where key = 'version' ''',
                              (str(_LibraryBackend.DB_VERSION),))

    def _create_table_book(self):
        self._con.execute('''create table if not exists book (
            id integer primary key,
            name string,
            path string unique,
            pages integer,
            format integer,
            size integer,
            added date default current_date)''')

    def _create_table_collection(self):
        self._con.execute('''create table if not exists collection (
            id integer primary key,
            name string unique,
            supercollection integer)''')

    def _create_table_contain(self):
        self._con.execute('''create table if not exists contain (
            collection integer not null,
            book integer not null,
            primary key (collection, book))''')

    def _create_table_info(self):
        self._con.execute('''create table if not exists info (
            key text primary key,
            value text)''')
        self._con.execute('''insert into info
            (key, value) values ('version', ?)''',
            (str(_LibraryBackend.DB_VERSION),))

    def _create_table_watchlist(self):
        self._con.execute('''create table if not exists watchlist (
            path text primary key,
            collection integer references collection (id) on delete set null)''')


_backend = None


def LibraryBackend():
    """ Returns the singleton instance of the library backend. """
    global _backend
    if _backend is not None:
        return _backend
    else:
        _backend = _LibraryBackend()
        return _backend

# vim: expandtab:sw=4:ts=4

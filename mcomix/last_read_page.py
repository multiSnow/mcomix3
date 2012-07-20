# -*- coding: utf-8 -*-

import os
import datetime

from mcomix import log
from mcomix import constants

# This import is only used for legacy data that is imported
# into the library at upgrade.
try:
    from sqlite3 import dbapi2
except ImportError:
    try:
        from pysqlite2 import dbapi2
    except ImportError:
        log.warning( _('! Could neither find pysqlite2 nor sqlite3.') )
        dbapi2 = None


class LastReadPage(object):
    """ Automatically stores the last page the user read for all book files,
    and restores the page the next time the archive is opened. When the book
    is finished, the page will be cleared.

    If L{enabled} is set to C{false}, all methods will do nothing. This
    simplifies code in other places, as it does not have to check each time
    if the preference option to store pages automatically is enabled.
    """

    def __init__(self, backend):
        """ Constructor.
        @param backend: Library backend instance.
        """
        #: If disabled, all methods will be no-ops.
        self.enabled = False
        #: Library backend.
        self.backend = backend

    def set_enabled(self, enabled):
        """ Enables (or disables) all functionality of this module.
        @type enabled: bool
        """
        self.enabled = enabled

    def count(self):
        """ Number of stored book/page combinations. This method is
        not affected by setting L{enabled} to false.
        @return: The number of entries stored by this module. """

        cursor = self.backend.execute("""SELECT COUNT(*) FROM recent""")
        count = cursor.fetchone()[0]
        cursor.close()

        return count

    def set_page(self, path, page):
        """ Sets C{page} as last read page for the book at C{path}.
        @param path: Path to book. Raises ValueError if file doesn't exist.
        @param page: Page number.
        """
        raise NotImplementedError()
        if not self.enabled:
            return

        if page < 1:
            raise ValueError()

        full_path = os.path.abspath(path)
        if os.path.isfile(full_path):
            self.clear_page(full_path)
            sql = """INSERT INTO lastread (path, page, time_set)
                VALUES (?, ?, ?)"""
            cursor = self.db.execute(sql, (full_path, page,
                datetime.datetime.now()))
            cursor.close()
        else:
            raise ValueError(_("! Could not read %s") % full_path)

    def clear_page(self, path):
        """ Removes stored page for book at C{path}.
        @param path: Path to book.
        """
        if not self.enabled:
            return

        full_path = os.path.abspath(path)
        book = self.backend.get_book_by_path(full_path)

        if book:
            sql = """DELETE FROM recent WHERE book = ?"""
            cursor = self.db.execute(sql, (book.id,))
            cursor.close()

    def clear_all(self):
        """ Removes all stored books from the library's 'Recent' collection,
        and removes all information from the recent table. This method is
        not affected by setting L{enabled} to false. """

        cursor = self.db.execute("""DELETE FROM recent""")
        cursor.close()
        cursor = self.db.execute("""DELETE FROM contain WHERE collection = ?""",
                                 (self.backend.get_recent_collection().id,))
        cursor.close()


    def get_page(self, path):
        """ Gets the last read page for book at C{path}.

        @param path: Path to book.
        @return: Page that was last read, or C{None} if the book
                 wasn't opened before.
        """
        raise NotImplementedError()
        if not self.enabled:
            return None

        full_path = os.path.abspath(path)
        sql = """SELECT page FROM lastread WHERE path = ?"""
        cursor = self.db.execute(sql, (full_path,))
        page = cursor.fetchone()
        cursor.close()

        if page:
            # cursor.fetchone() returns a tuple
            return page[0]
        else:
            return None

    def get_date(self, path):
        """ Gets the date at which the page for path was set.

        @param path: Path to book.
        @return: C{datetime} object, or C{None} if no page was set.
        """
        raise NotImplementedError()
        if not self.enabled:
            return None

        full_path = os.path.abspath(path)
        sql = """SELECT time_set FROM lastread WHERE path = ?"""
        cursor = self.db.execute(sql, (full_path,))
        date = cursor.fetchone()
        cursor.close()

        if date:
            # cursor.fetchone() returns a tuple
            return datetime.datetime.strptime(date[0], '%Y-%m-%d %H:%M:%S.%f')
        else:
            return None

    def migrate_database_to_library(self, recent_collection):
        """ Moves all information saved in the legacy database
        constants.LASTPAGE_DATABASE_PATH into the library,
        and deleting the old database. """

        database = self._init_database(constants.LASTPAGE_DATABASE_PATH)

        if database:
            cursor = database.execute('''SELECT path, page, time_set
                                         FROM lastread''')
            rows = cursor.fetchall()
            cursor.close()
            database.close()

            for path, page, time_set in rows:
                book = self.backend.get_book_by_path(path)

                if not book:
                    # The path doesn't exist in the library yet
                    self.backend.add_book(path, recent_collection)
                    book = self.backend.get_book_by_path(path)
                else:
                    # The book exists, move into recent collection
                    self.backend.add_book_to_collection(book.id, recent_collection)

                # TODO: Set recent info on retrieved book


            # TODO: Delete old database
            #os.unlink(constants.LASTPAGE_DATABASE_PATH)

    def _init_database(self, dbfile):
        """ Creates or opens new SQLite database at C{dbfile}, and initalizes
        the required table(s).

        @param dbfile: Database file name. This file needn't exist.
        @return: Open SQLite database connection.
        """
        if not dbapi2:
            return None

        db = dbapi2.connect(dbfile, isolation_level=None)
        sql = """CREATE TABLE IF NOT EXISTS lastread (
            path TEXT PRIMARY KEY,
            page INTEGER,
            time_set DATETIME
        )"""
        cursor = db.execute(sql)
        cursor.close()

        return db

# vim: expandtab:sw=4:ts=4

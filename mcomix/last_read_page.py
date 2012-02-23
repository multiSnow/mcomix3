# -*- coding: utf-8 -*-

import os
import datetime
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

    def __init__(self, dbfile):
        """ Constructor.
        @param dbfile: Path to the SQLite database that should be used.
                       Will be created if not existant yet.
        """
        #: If disabled, all methods will be no-ops.
        self.enabled = False
        #: Database storing pages.
        self.db = self._init_database(dbfile)

    def cleanup(self):
        """ Closes the database connection used by this class. """
        if not dbapi2:
            return

        self.db.close()
        self.enabled = False

    def set_enabled(self, enabled):
        """ Enables (or disables) all functionality of this module.
        @type enabled: bool
        """
        if dbapi2:
            self.enabled = enabled
        else:
            self.enabled = False

    def count(self):
        """ Number of stored book/page combinations. This method is
        not affected by setting L{enabled} to false.
        @return: The number of entries stored by this module. """

        if not dbapi2:
            return 0

        sql = """SELECT COUNT(*) FROM lastread"""
        cursor = self.db.execute(sql)
        count = cursor.fetchone()[0]
        cursor.close()

        return count

    def set_page(self, path, page):
        """ Sets C{page} as last read page for the book at C{path}.
        @param path: Path to book. Raises ValueError if file doesn't exist.
        @param page: Page number.
        """
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
        sql = """DELETE FROM lastread WHERE path = ?"""
        cursor = self.db.execute(sql, (full_path,))
        cursor.close()

    def clear_all(self):
        """ Removes all stored books. This method is not affected by setting
        L{enabled} to false. """
        if not dbapi2:
            return

        sql = """DELETE FROM lastread"""
        cursor = self.db.execute(sql)
        cursor.close()

    def get_page(self, path):
        """ Gets the last read page for book at C{path}.

        @param path: Path to book.
        @return: Page that was last read, or C{None} if the book
                 wasn't opened before.
        """
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
        if not self.enabled:
            return None

        full_path = os.path.abspath(path)
        sql = """SELECT time_set FROM lastread WHERE path = ?"""
        cursor = self.db.execute(sql, (full_path,))
        date = cursor.fetchone()
        cursor.close()

        if date:
            # cursor.fetchone() returns a tuple
            return date[0]
        else:
            return None

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

from mcomix import log

try:
    import sqlite3
    log.debug(f'SQLite: {sqlite3.sqlite_version} sqlite3 version: {sqlite3.version}')
except ImportError:
    log.warning( _('! Could find sqlite3.') )
    sqlite3 = None

# Local Variables:
# coding: utf-8
# mode: python
# python-indent-offset: 4
# indent-tabs-mode: nil
# End:

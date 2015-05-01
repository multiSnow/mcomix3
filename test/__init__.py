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


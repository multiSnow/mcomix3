#!/usr/bin/python2

__requires__ = 'pytest'

import os
import shutil
import sys

from pkg_resources import load_entry_point

if __name__ == '__main__':

    test_dir = os.path.dirname(__file__)

    # Remove __pycache__ directory so pytest does not freak out
    # when switching between the Linux/Windows versions.
    pycache = os.path.join(test_dir, '__pycache__')
    if os.path.exists(pycache):
        shutil.rmtree(pycache)

    custom_testsuite = None
    args = []
    n = 1
    while n < len(sys.argv):
        a = sys.argv[n]
        if '-' == a[0]:
            if '-V' == a:
                n += 1
                os.environ['MCOMIXPATH'] = sys.argv[n]
            else:
                args.append(a)
        elif os.path.exists(a):
            custom_testsuite = a
            args.append(a)
        else:
            args.extend(('-k', a))
        n += 1
    if custom_testsuite is None:
        args.insert(0, test_dir)
    sys.argv[1:] = args

    sys.exit(
        load_entry_point('pytest', 'console_scripts', 'py.test')()
    )

#!/usr/bin/env python2

from __future__ import print_function

import os
import sys
import subprocess


arch = '32'
runtime = '9'
pyversion = '2.7'
srcdir = sys.argv[1]
dstdir = sys.argv[2]
package_list = set(sys.argv[3:])


def get_package_directories(package):
    format_args = {
        'arch': arch,
        'package': package,
        'runtime': runtime,
        'srcdir': srcdir,
    }
    datadir = '%(srcdir)s/noarch/%(package)s' % format_args
    bindir = '%(srcdir)s/rtvc%(runtime)s-%(arch)s/%(package)s' % format_args
    return datadir, bindir

def get_package_dependencies(package):
    datadir, bindir = get_package_directories(package)
    depends = '%s/depends.txt' % datadir
    if not os.path.exists(depends):
        return set()
    with open(depends, 'r') as fp:
        dependencies = set(fp.read().split())
    for sub_package in tuple(dependencies):
        dependencies.update(get_package_dependencies(sub_package))
    return dependencies

def install_archive(archive):
    if 'win32' == sys.platform:
        exe = '%s/setup/7zr.exe' % srcdir
    else:
        exe = '7z'
    cmd = [exe, 'x', '-o%s' % dstdir, '-y', archive]
    print(' '.join(cmd))
    with open(os.devnull, 'wb') as null:
        subprocess.check_call(cmd, stdout=null)

def install_package(package):
    datadir, bindir = get_package_directories(package)
    install_archive('%s/%s.data.7z' % (datadir, package))
    install_archive('%s/%s.bin.7z' % (bindir, package))

def install_binding():
    archive = '%(srcdir)s/binding/py%(pyversion)s-%(arch)s/py%(pyversion)s-%(arch)s.7z' % {
        'arch': arch,
        'srcdir': srcdir,
        'pyversion': pyversion,
    }
    install_archive(archive)


for package in tuple(package_list):
    package_list.update(get_package_dependencies(package))

package_list = ['Base'] + sorted(package_list)

print('installing package(s): %s' % ' '.join(package_list))

install_binding()

for package in package_list:
    install_package(package)


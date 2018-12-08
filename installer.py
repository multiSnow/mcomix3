#!/usr/bin/python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser,ArgumentDefaultsHelpFormatter
from multiprocessing.dummy import Pool
from os import chmod,makedirs,stat,utime,walk
from os.path import dirname,isdir,join,splitext
from subprocess import run,DEVNULL

msgfmt_cmd=['msgfmt',]

def copy(srcdir,filename,dstdir,pool):
    finame,foname=join(srcdir,filename),join(dstdir,filename)
    fistat=stat(finame)
    times_ns=(fistat.st_atime_ns,fistat.st_mtime_ns)
    makedirs(dstdir,exist_ok=True)
    with open(finame,mode='rb') as fi,open(foname,mode='wb') as fo:
        fo.write(fi.read())
    utime(foname,ns=times_ns,times=None)
    chmod(foname,fistat.st_mode)
    print('install:',finame,foname)

def check_msgfmt():
    try:
        run(msgfmt_cmd+['-V'],check=True,stdout=DEVNULL,stderr=DEVNULL)
    except:
        # msgfmt not found or usable
        msgfmt_cmd.clear()
        print('msgfmt not found')
        return

def msgfmt(srcdir,filename,dstdir,pool):
    if not msgfmt_cmd:return
    if pool:
        pool.apply_async(msgfmt,(srcdir,filename,dstdir,None))
        return
    b,e=splitext(filename)
    finame,foname=join(srcdir,filename),join(dstdir,'{}.mo'.format(b))
    makedirs(dstdir,exist_ok=True)
    run(msgfmt_cmd+['-o',foname,finame])
    print('msgfmt:',foname,finame)

install_methods={'.1':copy,
                 '.py':copy,
                 '.png':copy,
                 '.css':copy,
                 '.po':msgfmt}

def install(srcdir,filename,target,pool):
    b,e=splitext(filename)
    if e not in install_methods:return
    install_methods[e](srcdir,filename,join(target,srcdir),pool)
    while True:
        sstat,d=stat(srcdir),join(target,srcdir)
        if not isdir(d):return
        times_ns=(sstat.st_atime_ns,sstat.st_mtime_ns)
        utime(d,ns=times_ns,times=None)
        chmod(d,sstat.st_mode)
        srcdir=dirname(srcdir)
        if not srcdir:return

def scandir(root,dest,pool=None):
    for r,dl,fl in walk(root):
        for f in fl:
            yield r,f,dest,pool

def main():
    argp=ArgumentParser(prog='installer',add_help=False,formatter_class=ArgumentDefaultsHelpFormatter)

    argp.add_argument('--srcdir',dest='srcdir',default='mcomix',
                      help='source directory.',metavar='DIR')
    argp.add_argument('--target',dest='target',default='target',
                      help='target directory.',metavar='DIR')
    argp.add_argument('-h','--help',action='help',
                      help='show help options.')

    ns=argp.parse_args()

    check_msgfmt()
    with Pool() as p:
        for args in scandir(ns.srcdir,ns.target,pool=p):
            install(*args)
        p.close()
        p.join()

if __name__=='__main__':
    exit(main())

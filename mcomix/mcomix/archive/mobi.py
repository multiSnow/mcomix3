# -*- coding: utf-8 -*-

''' MobiPocket handling (extract pictures) for MComix.

    Based on code from mobiunpack by Charles M. Hannum et al.
'''

import os
import re
import struct

from gi.repository import Gio

from mcomix import image_tools
from mcomix.archive import archive_base

class UnpackException(Exception):
    pass

class Sectionizer:
    def __init__(self, f):
        self.f = f
        header = self.f.read(78)
        self.ident = header[0x3C:0x3C+8]
        self.num_sections, = struct.unpack_from('>H', header, 76)
        sections = self.f.read(self.num_sections*8)
        self.sections = struct.unpack_from('>%dL' % (self.num_sections*2), sections, 0)[::2] + (0x7fffffff, )

    def loadSection(self, section, limit=0x7fffffff):
        before, after = self.sections[section:section+2]
        self.f.seek(before)
        if limit > after - before:
            limit = after - before
        return self.f.read(limit)

class MobiArchive(archive_base.NonUnicodeArchive):
    def __init__(self, archive):
        super(MobiArchive, self).__init__(archive)
        f = open(archive, 'rb')
        try:
            self.file = f
            self.sect = Sectionizer(self.file)
            if self.sect.ident != b'BOOKMOBI':
                raise UnpackException('invalid file format')
            self.header = self.sect.loadSection(0)
            self.crypto_type, = struct.unpack_from('>H', self.header, 0xC)
            if self.crypto_type != 0:
                raise UnpackException('file is encrypted')
            self.firstimg, = struct.unpack_from('>L', self.header, 0x6C)
        except:
            self.file = None
            f.close()
            raise

    def _close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def iter_contents(self):
        ''' List archive contents. '''
        supported_mimes={}
        for mimes,exts in image_tools.get_supported_formats().values():
            ext = next(iter(exts))
            for mime in mimes:
                supported_mimes[mime] = ext
        for i in range(self.firstimg, self.sect.num_sections):
            magic = self.sect.loadSection(i, 10)
            mime, uncertain = Gio.content_type_guess(data=magic)
            mime = mime.lower()
            if mime in supported_mimes:
                ext = supported_mimes[mime]
                yield "image%05d%s" % (1+i-self.firstimg, ext)

    def extract(self, filename, destination_dir):
        ''' Extract <filename> from the archive to <destination_dir>. '''
        destination_path = os.path.join(destination_dir, filename)
        fnparts = re.split('^image([0-9]*)\.', filename)
        if len(fnparts) == 3:
            i = int(fnparts[1])-1+self.firstimg
            data = self.sect.loadSection(i)
            with self._create_file(destination_path) as new:
                new.write(data)
        return destination_path

    def close(self):
        ''' Close the archive handle '''
        self._close()

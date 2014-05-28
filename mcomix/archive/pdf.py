# -*- coding: utf-8 -*-

""" PDF handler. """

from mcomix import log
from mcomix import process
from mcomix.archive import archive_base

import math
import os
import re

# Default DPI for rendering.
PDF_RENDER_DPI_DEF = 72 * 4
# Maximum DPI for rendering.
PDF_RENDER_DPI_MAX = 72 * 10

_pdf_possible = None

class PdfArchive(archive_base.BaseArchive):

    """ Concurrent calls to extract welcome! """
    support_concurrent_extractions = True

    def __init__(self, archive):
        super(PdfArchive, self).__init__(archive)
        self.pdf = archive

    def list_contents(self):
        pages = []
        proc = process.Process(['mutool', 'show', self.pdf, 'pages'])
        fd = proc.spawn()
        if fd is not None:
            for line in fd.read().splitlines():
                if line.startswith('page '):
                    pages.append(line.split()[1] + '.png')
            fd.close()
        return pages

    def extract(self, filename, destination_dir):
        self._create_directory(destination_dir)
        destination_path = os.path.join(destination_dir, filename)
        page_num = int(filename[0:-4])
        # Try to find optimal DPI.
        proc = process.Process(['mudraw', '-x', self.pdf, str(page_num)])
        fd = proc.spawn()
        max_width = 0
        max_dpi = PDF_RENDER_DPI_DEF
        if fd is not None:
            for line in fd.read().splitlines():
                m = re.match('<fill_image .* matrix="([0-9.]+) [^"]*".* width="([0-9]+)"', line)
                if m is not None:
                    width = int(m.group(2))
                    if width > max_width:
                        dpi = int(width * 72 / float(m.group(1)))
                        if dpi > PDF_RENDER_DPI_MAX:
                            dpi = PDF_RENDER_DPI_MAX
                        max_width = width
                        max_dpi = dpi
            fd.close()
        # Render...
        cmd = ['mudraw', '-r', str(max_dpi), '-o', destination_path, self.pdf, str(page_num)]
        log.debug('rendering %s: %s' % (filename, ' '.join(cmd)))
        proc = process.Process(cmd)
        fd = proc.spawn()
        if fd is not None:
            fd.close()
        proc.wait()

    def close(self):
        self.pdf = None

    @staticmethod
    def is_available():
        global _pdf_possible
        if _pdf_possible is None:
            proc = process.Process(['mudraw'])
            fd = proc.spawn()
            if fd is not None:
                fd.close()
                _pdf_possible = True
            else:
                log.info('MuPDF not available.')
                _pdf_possible = False
        return _pdf_possible

# vim: expandtab:sw=4:ts=4

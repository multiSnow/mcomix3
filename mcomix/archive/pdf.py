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

    _fill_image_regex = re.compile(r'^\s*<fill_image\b.*\bmatrix="(?P<matrix>[^"]+)".*\bwidth="(?P<width>\d+)".*\bheight="(?P<height>\d+)".*/>\s*$')

    def __init__(self, archive):
        super(PdfArchive, self).__init__(archive)
        self.pdf = archive

    def iter_contents(self):
        proc = process.popen(['mutool', 'show', '--', self.pdf, 'pages'])
        try:
            for line in proc.stdout:
                if line.startswith('page '):
                    yield line.split()[1] + '.png'
        finally:
            proc.stdout.close()
            proc.wait()

    def extract(self, filename, destination_dir):
        self._create_directory(destination_dir)
        destination_path = os.path.join(destination_dir, filename)
        page_num = int(filename[0:-4])
        # Try to find optimal DPI.
        proc = process.popen(['mudraw', '-x', '--', self.pdf, str(page_num)])
        try:
            max_size = 0
            max_dpi = PDF_RENDER_DPI_DEF
            for line in proc.stdout:
                match = self._fill_image_regex.match(line)
                if not match:
                    continue
                matrix = [float(f) for f in match.group('matrix').split()]
                for size, coeff1, coeff2 in (
                    (int(match.group('width')), matrix[0], matrix[1]),
                    (int(match.group('height')), matrix[2], matrix[3]),
                ):
                    if size < max_size:
                        continue
                    render_size = math.sqrt(coeff1 * coeff1 + coeff2 * coeff2)
                    dpi = int(size * 72 / render_size)
                    if dpi > PDF_RENDER_DPI_MAX:
                        dpi = PDF_RENDER_DPI_MAX
                    max_size = size
                    max_dpi = dpi
        finally:
            proc.stdout.close()
            proc.wait()
        # Render...
        cmd = ['mudraw', '-r', str(max_dpi), '-o', destination_path, '--', self.pdf, str(page_num)]
        log.debug('rendering %s: %s', filename, ' '.join(cmd))
        process.call(cmd)

    def close(self):
        self.pdf = None

    @staticmethod
    def is_available():
        global _pdf_possible
        if _pdf_possible is None:
            try:
                process.call(['mudraw'])
                _pdf_possible = True
            except:
                log.info('MuPDF not available.')
                _pdf_possible = False
        return _pdf_possible

# vim: expandtab:sw=4:ts=4

# -*- coding: utf-8 -*-

''' PDF handler. '''

import math
import os
import re
from threading import Lock

from mcomix import log
from mcomix import process
from mcomix.archive import archive_base

# Default DPI for rendering.
PDF_RENDER_DPI_DEF = 72 * 4
# Maximum DPI for rendering.
PDF_RENDER_DPI_MAX = 72 * 10

_mupdf = {}

def _find_mupdf():
    _mupdf['found'] = False
    _mupdf['version'] = None
    _mupdf['mutool'] = []
    _mupdf['mudraw'] = []
    _mupdf['mudraw_trace_args'] = []
    if (mutool:=process.find_executable(('mutool',))) is None:
        return log.debug('mutool executable not found')
    _mupdf['mutool'].append(mutool)
    # Find MuPDF version; assume 1.6 version since
    # the '-v' switch is only supported from 1.7 onward...
    _mupdf['version'] = (1,6)
    with process.popen([mutool, '-v'], stdout=process.NULL, stderr=process.PIPE,
                       universal_newlines=True) as proc:
        if output:=re.match(r'mutool version (?P<version>[\d.]+)([^\d].*)?',
                            proc.stderr.read()):
            _mupdf['version'] = tuple(map(int,output.group('version').split('.')))
    if _mupdf['version'] >= (1,8):
        # Mutool executable with draw support.
        _mupdf['found'] = True
        _mupdf['mudraw'].extend((mutool, 'draw', '-q'))
        _mupdf['mudraw_trace_args'].extend(('-F', 'trace'))
        return
    # Separate mudraw executable.
    if (mudraw:=process.find_executable(('mudraw',))) is None:
        return log.debug('mudraw executable not found')
    _mupdf['found'] = True
    _mupdf['mudraw'].append(mudraw)
    if _mupdf['version'] >= (1,7):
        _mupdf['mudraw_trace_args'].extend(('-F', 'trace'))
    else:
        _mupdf['mudraw_trace_args'].append('-x')

class PdfArchive(archive_base.BaseArchive):

    ''' Concurrent calls to extract welcome! '''
    support_concurrent_extractions = True

    _fill_image_regex = re.compile(r'^\s*<fill_image\b.*\bmatrix="(?P<matrix>[^"]+)".*\bwidth="(?P<width>\d+)".*\bheight="(?P<height>\d+)".*/>\s*$')

    def __init__(self, archive):
        super(PdfArchive, self).__init__(archive)
        self._pdf_procs = {}
        self._pdf_procs_lock = Lock()

    def iter_contents(self):
        with process.popen(_mupdf['mutool'] + ['show', '--', self.archive, 'pages'],
                           universal_newlines=True) as proc:
            for line in proc.stdout:
                if line.startswith('page '):
                    yield line.split()[1] + '.png'

    def extract(self, filename, destination_dir):
        self._create_directory(destination_dir)
        destination_path = os.path.join(destination_dir, filename)
        page_num, ext = os.path.splitext(filename)
        # Try to find optimal DPI.
        cmd = _mupdf['mudraw'] + _mupdf['mudraw_trace_args'] + ['--', self.archive, str(page_num)]
        log.debug('finding optimal DPI for %s: %s', filename, ' '.join(cmd))
        with process.popen(cmd, universal_newlines=True) as proc:
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
        # Render...
        cmd = _mupdf['mudraw'] + ['-r', str(max_dpi), '-o', destination_path, '--', self.archive, str(page_num)]
        log.debug('rendering %s: %s', filename, ' '.join(cmd))
        with process.popen(cmd,stdout=process.NULL) as proc:
            with self._pdf_procs_lock:
                self._pdf_procs[(pid:=proc.pid)]=proc
            proc.wait()
            with self._pdf_procs_lock:
                self._pdf_procs.pop(pid)
        return destination_path

    def stop(self):
        with self._pdf_procs_lock:
            for proc in self._pdf_procs.values():
                proc.terminate()

    @staticmethod
    def is_available():
        if _mupdf:
            return _mupdf['found']
        _find_mupdf()
        if _mupdf['found']:
            log.info('Using MuPDF version: %s', '.'.join(map(str,_mupdf['version'])))
            log.debug('mutool: %s', ' '.join(_mupdf['mutool']))
            log.debug('mudraw: %s', ' '.join(_mupdf['mudraw']))
            log.debug('mudraw trace arguments: %s', ' '.join(_mupdf['mudraw_trace_args']))
        else:
            log.info('MuPDF not available.')
        return _mupdf['found']

# vim: expandtab:sw=4:ts=4

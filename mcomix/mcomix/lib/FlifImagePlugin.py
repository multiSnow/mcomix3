# Copyright (c) 2019, multiSnow <infinity.blick.winkel@gmail.com>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all
# copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
# AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
# DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR
# PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import io
import ctypes
import ctypes.util as cutil
import threading

from PIL import Image,ImageFile,ImagePalette

_LIBFLIF={
    'cdll':None,
    'failed':False,
}

_COLORS_MODE={
    1:'L',
    3:'RGBX',
    4:'RGBA',
}

_LOCK=threading.Lock()

class FLIF_DECODER(ctypes.Structure):pass
class FLIF_IMAGE(ctypes.Structure):pass
class FLIF_INFO(ctypes.Structure):pass

def _getloader():
    if _LIBFLIF['failed']:
        return
    if _LIBFLIF['cdll'] is None:
        path=cutil.find_library('flif_dec') or cutil.find_library('flif')
        flif=ctypes.CDLL(path)
        if not hasattr(flif,'flif_create_decoder'):
            _LIBFLIF['failed']=True
            return
        _LIBFLIF['cdll']=flif

        # set restype of some functions

        # image functions
        flif.flif_create_image.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_create_image_RGB.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_create_image_GRAY.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_create_image_GRAY16.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_create_image_PALETTE.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_create_image_HDR.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_import_image_RGBA.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_import_image_RGB.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_import_image_GRAY.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_import_image_GRAY16.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_import_image_PALETTE.restype=ctypes.POINTER(FLIF_IMAGE)
        flif.flif_image_get_metadata.restype=ctypes.POINTER(ctypes.c_bool)
        # decoder functions
        flif.flif_create_decoder.restype=ctypes.POINTER(FLIF_DECODER)
        flif.flif_decoder_get_image.restype=ctypes.POINTER(FLIF_IMAGE)
        # info functions
        flif.flif_read_info_from_memory.restype=ctypes.POINTER(FLIF_INFO)

    return _LIBFLIF['cdll']


class FlifDecoder:
    def __init__(self,data):
        _LOCK.acquire()
        self.ctx=_getloader()
        self.decoder=self.ctx.flif_create_decoder()
        rc=self.ctx.flif_decoder_decode_memory(
            self.decoder,data,len(data))
        if not rc:
            self.decoder=None
            raise RuntimeError('failed to decode.')
        self.num_images=self.ctx.flif_decoder_num_images(self.decoder)
        self.num_loops=self.ctx.flif_decoder_num_loops(self.decoder)

    def get_image(self,index=0):
        return FlifImage(self.ctx.flif_decoder_get_image(self.decoder,index))

    def close(self):
        if self.decoder is not None:
            self.ctx.flif_destroy_decoder(self.decoder)
            self.decoder=None
        _LOCK.release()

    def __enter__(self):
        return self

    def __exit__(self,etype,value,tb):
        self.close()


class FlifImage:
    def __init__(self,image,size=(1,1),mode='RGBA'):
        self.ctx=_getloader()
        if image is None:
            funcmap={
                'RGBA':self.ctx.flif_create_image,
                'RGBX':self.ctx.flif_create_image_RGB,
                'L'   :self.ctx.flif_create_image_GRAY,
                'P'   :self.ctx.flif_create_image_PALETTE,
            }
            if mode not in funcmap:
                raise KeyError('mode {} is not supported.'.format(mode))
            image=funcmap[mode](*size)

            self.palette_size=0
            self.nb_channels=self.ctx.flif_image_get_nb_channels(image)
            self.mode=mode

        else:
            # guess mode by nb_channels and palette size
            self.palette_size=self.ctx.flif_image_get_palette_size(image)
            self.nb_channels=self.ctx.flif_image_get_nb_channels(image)
            self.mode='P' if self.palette_size else _COLORS_MODE[self.nb_channels]

        self.width=self.ctx.flif_image_get_width(image)
        self.height=self.ctx.flif_image_get_height(image)
        self.size=self.width,self.height
        self.depth=self.ctx.flif_image_get_depth(image)
        self.delay=self.ctx.flif_image_get_frame_delay(image)

        self.palette=None
        if self.palette_size:
            d=ctypes.create_string_buffer(self.palette_size*4) # RGBA colors
            self.ctx.flif_image_get_palette(image,ctypes.byref(d))
            self.palette=d.raw

        self._write_func_map={8:{
            'RGBA':self.ctx.flif_image_write_row_RGBA8,
            'RGBX':self.ctx.flif_image_write_row_RGBA8,
            'L':   self.ctx.flif_image_write_row_GRAY8,
            'P':   self.ctx.flif_image_write_row_PALETTE8,
        },16:{
            'RGBA':self.ctx.flif_image_write_row_RGBA16,
            'RGBX':self.ctx.flif_image_write_row_RGBA16,
            'L':   self.ctx.flif_image_write_row_GRAY16,
            'P':   None,
        },}
        self._read_func_map={8:{
            'RGBA':self.ctx.flif_image_read_row_RGBA8,
            'RGBX':self.ctx.flif_image_read_row_RGBA8,
            'L':   self.ctx.flif_image_read_row_GRAY8,
            'P':   self.ctx.flif_image_read_row_PALETTE8,
        },16:{
            'RGBA':self.ctx.flif_image_read_row_RGBA16,
            'RGBX':self.ctx.flif_image_read_row_RGBA16,
            'L':   self.ctx.flif_image_read_row_GRAY16,
            'P':   None,
        },}

        reader=self._read_func_map[self.depth][self.mode]
        if reader is None:
            raise NotImplementedError(
                'unsupported, depth: {}, mode: {}'.format(self.depth,self.mode))

        rowsize=len(self.mode)*self.width
        d=ctypes.create_string_buffer(rowsize)

        buf=io.BytesIO()
        for r in range(self.height):
            reader(image,r,ctypes.byref(d),rowsize)
            buf.write(d.raw)
        self.raw=buf.getvalue()
        buf.close()

        self.exif=None
        metalen=ctypes.c_uint()
        metaptr=ctypes.POINTER(ctypes.c_ubyte)()
        rc=self.ctx.flif_image_get_metadata(
            image,b'eXif',ctypes.byref(metaptr),ctypes.byref(metalen))
        if rc:
            self.exif=bytes(bytearray(metaptr[:metalen.value]))


class FlifInfo:
    def __init__(self,data):
        self.ctx=_getloader()
        self.info=self.ctx.flif_read_info_from_memory(data[:32],32)

        self.depth=self.ctx.flif_image_get_depth(self.info)
        self.width=self.ctx.flif_info_get_width(self.info)
        self.height=self.ctx.flif_info_get_height(self.info)
        self.size=self.width,self.height
        self.nb_channels=self.ctx.flif_info_get_nb_channels(self.info)
        self.num_images=self.ctx.flif_info_num_images(self.info)

    def close(self):
        if self.info is not None:
            self.ctx.flif_destroy_info(self.info)
            self.info=None

    def __enter__(self):
        return self

    def __exit__(self,etype,value,tb):
        self.close()


def _accept(head):
    if _getloader() is None:
        return False
    return head[:4]==b'FLIF'

class FlifImageFile(ImageFile.ImageFile):
    format='FLIF'
    format_description='Free Lossless Image Format'

    def _open(self):
        data=self.fp.read()
        self.fp.close()
        self.fp=None
        self._data=data

        self._images=[] # list of FlifImage
        self._pos=0 # position of currect frame

        with FlifInfo(self._data) as info:
            self._size=info.width,info.height
            self._n_frames=info.num_images
            mode=_COLORS_MODE[info.nb_channels]
        self.mode='RGB' if mode=='RGBX' else mode
        self.tile=[]
        with FlifDecoder(self._data) as dec:
            self.info['loop']=dec.num_loops
            for n in range(dec.num_images):
                self._images.append(dec.get_image(index=n))
        self.seek(0)

    def tobytes(self):
        self.load()
        return super().tobytes()

    def seek(self,pos):
        if pos>=self._n_frames:
            raise EOFError('seek beyond the end of the sequence')
        if pos<0:
            raise EOFError("negative frame index is not valid")
        self._pos=pos
        curimg=self._images[self._pos]

        mode=curimg.mode
        self.mode='RGB' if mode=='RGBX' else mode
        self._size=curimg.width,curimg.height
        self.rawmode=mode
        self.info['timestamp']=curimg.delay
        self.info['duration']=0
        if self._pos:
            self.info['duration']=self.info['timestamp']-self._images[self._pos-1].delay
        self.info['depth']=curimg.depth
        if self.fp is not None:
            self.fp.close()
        self.fp=io.BytesIO(curimg.raw)
        if self.mode=='P':
            # TODO: alpha is lost here.
            self.palette=ImagePalette.raw('RGBX',curimg.palette)
        self.tile.clear()
        self.tile.append(('raw',(0,0,*self.size),0,self.rawmode))
        if curimg.exif is None:
            self.info.pop('exif',None)
        else:
            self.info['exif']=curimg.exif

        return self.load()

    def tell(self):
        return self._pos

    @property
    def n_frames(self):
        return self._n_frames

    @property
    def is_animated(self):
        return self._n_frames>1

if _getloader() is not None:
    Image.register_open(FlifImageFile.format,FlifImageFile,_accept)
    Image.register_extension(FlifImageFile.format,'.flif')
    Image.register_mime(FlifImageFile.format,'image/flif')

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
import multiprocessing
import sys

from PIL import Image,ImageFile,ImagePalette

_LIBFLIF={
    'path':None,
    'failed':False,
}

_COLORS_MODE={
    1:'L',
    3:'RGBX',
    4:'RGBA',
}

FLIF_NOT_FOUND,DECODE_ERROR,UNSUPPORTED_FORMAT=range(3)

class FLIF_DECODER(ctypes.Structure):pass
class FLIF_IMAGE(ctypes.Structure):pass
class FLIF_INFO(ctypes.Structure):pass

class FlifInfo:
    def __init__(self,data):
        self.ctx=ctypes.CDLL(_getloader())
        self.ctx.flif_read_info_from_memory.restype=ctypes.POINTER(FLIF_INFO)
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

class ImageNS:
    def __init__(self,mode,width,height,depth,delay,exif,palette,raw):
        self.mode=mode
        self.width=width
        self.height=height
        self.depth=depth
        self.delay=delay
        self.exif=exif
        self.palette=palette
        self.raw=raw
        self.size=width,height

def decodeflif(const,loop,
               modelist,widthlist,heightlist,depthlist,delaylist,
               exiflist,palettelist,rawlist):
    data,path,draft_width,draft_height=const
    if not path:
        exit(FLIF_NOT_FOUND)
    flif=ctypes.CDLL(path)
    flif.flif_create_decoder.restype=ctypes.POINTER(FLIF_DECODER)
    flif.flif_decoder_get_image.restype=ctypes.POINTER(FLIF_IMAGE)
    decoder=flif.flif_create_decoder()
    flif.flif_decoder_set_crc_check(decoder,1)
    if draft_width and draft_height:
        # TODO: flif_decoder_set_fit should be used, which caused segfault
        flif.flif_decoder_set_resize(decoder,draft_width,draft_height)
    if not flif.flif_decoder_decode_memory(decoder,data,len(data)):
        flif.flif_destroy_decoder(decoder)
        exit(DECODE_ERROR)
    _read_func_map={8:{
        'RGBA':flif.flif_image_read_row_RGBA8,
        'RGBX':flif.flif_image_read_row_RGBA8,
        'L':   flif.flif_image_read_row_GRAY8,
        'P':   flif.flif_image_read_row_PALETTE8,
    },16:{
        'RGBA':flif.flif_image_read_row_RGBA16,
        'RGBX':flif.flif_image_read_row_RGBA16,
        'L':   flif.flif_image_read_row_GRAY16,
        'P':   None,
    },}

    num_images=flif.flif_decoder_num_images(decoder)
    try:
        loop.value=flif.flif_decoder_num_loops(decoder)
    except:
        flif.flif_destroy_decoder(decoder)
        exit(DECODE_ERROR)

    for n in range(num_images):
        image=flif.flif_decoder_get_image(decoder,n)
        palette_size=flif.flif_image_get_palette_size(image)
        nb_channels=flif.flif_image_get_nb_channels(image)

        mode='P' if palette_size else _COLORS_MODE[nb_channels]
        width=flif.flif_image_get_width(image)
        height=flif.flif_image_get_height(image)
        depth=flif.flif_image_get_depth(image)
        delay=flif.flif_image_get_frame_delay(image)

        palette=None
        if palette_size:
            d=ctypes.create_string_buffer(palette_size*4) # RGBA colors
            flif.flif_image_get_palette(image,ctypes.byref(d))
            palette=d.raw

        reader=_read_func_map[depth][mode]
        if reader is None:
            flif.flif_destroy_decoder(decoder)
            exit(UNSUPPORTED_FORMAT)
        rowsize=len(mode)*width
        d=ctypes.create_string_buffer(rowsize)
        buf=io.BytesIO()
        for r in range(height):
            reader(image,r,ctypes.byref(d),rowsize)
            buf.write(d.raw)
        raw=buf.getvalue()
        buf.close()

        exif=None
        metalen=ctypes.c_uint()
        metaptr=ctypes.POINTER(ctypes.c_ubyte)()
        if flif.flif_image_get_metadata(
                image,b'eXif',ctypes.byref(metaptr),ctypes.byref(metalen)):
            exif=bytes(bytearray(metaptr[:metalen.value]))

        try:
            modelist.append(mode)
            widthlist.append(width)
            heightlist.append(height)
            depthlist.append(depth)
            delaylist.append(delay)
            exiflist.append(exif)
            palettelist.append(palette)
            rawlist.append(raw)
        except:
            flif.flif_destroy_decoder(decoder)
            exit(DECODE_ERROR)

    flif.flif_destroy_decoder(decoder)
    exit(0)

def _getloader():
    if _LIBFLIF['failed']:
        return
    if _LIBFLIF['path'] is None:
        path=cutil.find_library('flif_dec') or cutil.find_library('flif')
        if not hasattr(ctypes.CDLL(path),'flif_create_decoder'):
            _LIBFLIF['failed']=True
            return
        _LIBFLIF['path']=path

    return _LIBFLIF['path']

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
        self._draft_width=0
        self._draft_height=0

        self._images=[] # list of FlifImage
        self._pos=0 # position of currect frame

        with FlifInfo(self._data) as info:
            self._size=info.width,info.height
            self._n_frames=info.num_images
            mode=_COLORS_MODE[info.nb_channels]
        self.mode='RGB' if mode=='RGBX' else mode
        self.tile=[]

    def load(self):
        if self._images:
            return super().load()
        with multiprocessing.Manager() as manager:
            modelist=manager.list()
            widthlist=manager.list()
            heightlist=manager.list()
            depthlist=manager.list()
            delaylist=manager.list()
            exiflist=manager.list()
            palettelist=manager.list()
            rawlist=manager.list()

            const=manager.list([self._data,_getloader(),
                                self._draft_width,self._draft_height])

            loop=manager.Value('b',-1)
            proc=multiprocessing.Process(
                target=decodeflif,
                args=(const,loop,
                      modelist,widthlist,heightlist,depthlist,delaylist,
                      exiflist,palettelist,rawlist))
            proc.start()
            proc.join()

            if proc.exitcode:
                raise RuntimeError('failed to decode, {}.',proc.exitcode)
            self.info['loop']=loop.value
            for attrs in zip(modelist,widthlist,heightlist,depthlist,delaylist,
                             exiflist,palettelist,rawlist):
                self._images.append(ImageNS(*attrs))

        return self.seek(self._pos)

    def draft(self,mode,size):
        if mode:
            print('W: setting mode in draft is not supported.',file=sys.stderr)
        # TODO:
        # pass twice of the size to decoder and load, then let PIL to resize it,
        # so only first draft has effect.
        # it is because flif_decoder_set_resize typically causes a smaller image.
        # also see TODO in decodeflif
        w,h=size
        w_,h_=self._size
        size=min(w*2,w_),min(h*2,h_)
        self._draft_width,self._draft_height=size
        self._size=size
        self.load()

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

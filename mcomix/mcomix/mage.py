'''mage.py - the i(nternal)mage class.'''

from io import BytesIO

from gi.repository import Gio,GLib

# the 'Pixbuf' instance
from gi.repository import GdkPixbuf
# the 'PImage' instance
from PIL import Image

_ROTATE_DICT={
    90 :Image.ROTATE_90,
    180:Image.ROTATE_180,
    270:Image.ROTATE_270,
}

_PIL_FILTERS=(
    Image.NEAREST,
    Image.BILINEAR,
    Image.BICUBIC,
    Image.LANCZOS,
    Image.BOX,
    Image.HAMMING
)

def _pixbuf2pil(pixbuf):
    mode='RGBA' if pixbuf.get_has_alpha() else 'RGB'
    with Image.frombuffer(mode,(pixbuf.get_width(),pixbuf.get_height()),
                          pixbuf.get_pixels(),'raw',mode,pixbuf.get_rowstride(),1) as im:
        im.load()
        return im

class GioStreamIO(Gio.MemoryInputStream):
    def __init__(self,data=b''):
        super().__init__()
        if data:
            self.add_data(data)

    def __enter__(self):
        return self

    def __exit__(self,etype,value,tb):
        self.close()

class MageProp:
    # pixel-related attribute
    _attrib_=(
        # resize
        'size','resample','reducing','position','viewsize',
        # enhance
        'enhance_colorbalance','enhance_contrast',
        'enhance_brightness','enhance_sharpness',
        'autocontrast',
        # transposition
        'rotation','exif_rotation','implied_rotation',
        'vflip','hflip',
    )

    def __init__(self,im=None):
        # the full image size before any transposition
        self._size=(0,0)
        # PIL resample filter
        self._resample=Image.NEAREST
        # position of view, (x,y)
        self._position=(0,0)
        # output size of view, (width, height)
        self._viewsize=self._size
        # reduce level
        self.reducing=None
        # enhancement
        self.enhance_colorbalance=1
        self.enhance_contrast=1
        self.enhance_brightness=1
        self.enhance_sharpness=1
        self.autocontrast=False
        # additional rotation
        self._rotation=0
        # 'orientation' of exif
        self._exif_rotation=0
        # whether to apply exif rotation
        self._implied_rotation=False
        # vertical flip (top to bottom)
        self._vflip=False
        # horizontal flip (left to right)
        self._hflip=False
        # TODO: Image.TRANSPOSE and Image.TRANSVERSE
        # TODO: color profile

        if im is not None:
            self.size=im.size
            try:
                self.exif_rotation={3:180,6:90,8:270}.get(im.getexif().get(274,0),0)
            except:
                pass

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self,size):
        self._size=tuple(size)

    @property
    def resample(self):
        return self._resample

    @resample.setter
    def resample(self,resample_filter):
        assert resample_filter in _PIL_FILTERS,f'unsupported filter: {resample_filter}'
        self._resample=resample_filter

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self,position):
        self._position=tuple(position)

    @property
    def viewsize(self):
        return self._viewsize

    @viewsize.setter
    def viewsize(self,viewsize):
        self._viewsize=tuple(viewsize)

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self,rotation):
        assert not rotation%90,f'unsupported rotation: {rotation}'
        self._rotation=rotation

    @property
    def exif_rotation(self):
        return self._exif_rotation

    @exif_rotation.setter
    def exif_rotation(self,rotation):
        assert not rotation%90,f'unsupported rotation: {rotation}'
        self._exif_rotation=rotation

    @property
    def implied_rotation(self):
        return self._implied_rotation

    @implied_rotation.setter
    def implied_rotation(self,use_implied_rotation):
        self._implied_rotation=use_implied_rotation

    @property
    def vflip(self):
        return self._vflip

    @vflip.setter
    def vflip(self,is_flip):
        self._vflip=is_flip
        self.merge_transposition()

    @property
    def hflip(self):
        return self._hflip

    @hflip.setter
    def hflip(self,is_flip):
        self._hflip=is_flip
        self.merge_transposition()

    @property
    def total_rotation(self):
        return (self.rotation+(self.exif_rotation if self.implied_rotation else 0))%360

    @property
    def pixel(self):
        w,h=self.size
        return w*h

    def merge_transposition(self):
        if self.vflip and self.hflip:
            self.vflip=False
            self.hflip=False
            self.rotation+=180

    def is_resized(self,other):
        # True if self is resized compared to other
        assert isinstance(other,MageProp)
        return (
            self.size,self.resample,self.reducing,
        )!=(
            other.size,other.resample,other.reducing,
        )

    def is_view_moved(self,other):
        # True if view of self is moved compared to other
        assert isinstance(other,MageProp)
        return (self.position,self.viewsize)!=(other.position,other.viewsize)

    def is_enhanced(self,other):
        # True if self is enhanced compared to other
        assert isinstance(other,MageProp)
        return (
            self.enhance_colorbalance,self.enhance_contrast,
            self.enhance_brightness,self.enhance_sharpness,
            self.autocontrast,
        )!=(
            other.enhance_colorbalance,other.enhance_contrast,
            other.enhance_brightness,other.enhance_sharpness,
            other.autocontrast,
        )

    def is_rotated(self,other):
        # True if self is rotated compared to other
        assert isinstance(other,MageProp)
        return self.total_rotation!=other.total_rotation

    def is_flipped(self,other):
        # True if self is flipped compared to other
        assert isinstance(other,MageProp)
        return (self.vflip,self.hflip)!=(other.vflip,other.hflip)

    def is_pixel_changed(self,other):
        # True if any pixel of self should be changed compared to other
        # (resized, view changed, enhanced, icc applied)
        return self.is_resized(other) or self.is_view_moved(other) or self.is_enhanced(other)

    def is_transposed(self,other):
        # True if self is transposed compared to other
        return self.is_rotated(other) or self.is_flipped(other)

    def keys(self):
        yield from self._attrib_

    def copy(self):
        # deep copy
        copy=MageProp()
        for key in self.keys():
            setattr(copy,key,getattr(self,key))
        assert self==copy
        return copy

    def __eq__(self,other):
        return not self.is_pixel_changed(other)

    def __repr__(self):
        s=', '.join(f'{key}={getattr(self,key)}' for key in self.keys())
        return f'MageProp({s})'

class Mage:
    def __init__(self):

        # original image as PImage, or the first frame of animation
        self._im=None
        # a list of (PImage,int), as the frame and duration
        # if image is not animation, it should be empty.
        self._frames=[]
        # property of original image
        self._im_prop=None
        # loop animation
        self._loop=False
        # original background color as int (#RRGGBBAA).
        self._bgcolor=0
        # bytes data of color profile, or None.
        self._icc=None
        # dictionary of exif, or None.
        self._exif={}

        # cached image as PImage
        self._cache=None
        # cached image object, a list of (PImage,int)
        self._cache_frames=[]
        # property of cached image
        self._cache_prop=None
        # property of cache frames. (property of each frame should be same)
        self._frame_prop=None
        # property of required image
        self._required_prop=None
        # background color of cache as int (#RRGGBBAA) or checkered bg as -1
        self._bg=0

        # thumbnail as Pixbuf.
        # fast scale filter, no icc, no animation.
        self._thumbnail=None

    @property
    def image(self):
        # access to original image.
        if self._im is None:
            raise ValueError('image is not loaded')
        return self._im

    @image.setter
    def image(self,im):
        # set or update original image, close previous image.
        if self._im is not None:
            _im=self._im
            self._im=None
            _im.close()
            self._exif.clear()
            self.purge_frames()
            self.purge_cache()
        self._im=im
        self._bgcolor=0
        self._icc=im.info.get('icc_profile')
        try:
            self._exif.update(im.getexif())
        except AttributeError:
            # no exif support
            return
        # TODO: remove code below and increase PIL required version
        if self._exif:
            # exif recognized by PIL
            return
        # exif of PNG no recognized by PIL until 8.3.1
        try:
            l1,l2,size,*lines=im.info.get('Raw profile type exif').splitlines()
            assert l2=='exif'
            assert len(data:=bytes.fromhex(''.join(lines)))==int(size)
        except:
            # invalid exif data.
            return
        im.info['exif']=data
        # reload exif
        try:
            self._exif.update(im.getexif())
        except AttributeError:
            return

    @property
    def image_prop(self):
        if self._im_prop is None:
            self._im_prop=MageProp(self.image)
        return self._im_prop

    @property
    def frames(self):
        # access to original frames
        return self._frames

    @property
    def exif(self):
        # access to exif of original image
        self.image
        return self._exif

    def add_frame(self,frame,duration):
        self.frames.append((frame,duration))

    def purge_frames(self):
        # purge all frames
        while self.frames:
            im,duration=self.frames.pop()
            im.close()

    @property
    def cache(self):
        # get cached image, generate if not cached yet or need to be changed.
        assert self.image is not None # ensure original image is loaded
        if self.cache_prop!=self.required_prop:
            # pixel changed, purge all cached image and frames
            self.purge_cache()
        self._cache=self._create_cache(self._cache,self.cache_prop)
        self._cache_prop=self.required_prop.copy()
        return self._cache

    @property
    def cache_frames(self):
        # get cached frames, generate if not cached yet.
        assert self.cache is not None # ensure cache purged if needed
        if not self.frames:
            # no animation
            return []
        if not self._cache_frames:
            # cached frames not exists, generate new ones
            for im,duration in self.frames:
                self._cache_frames.append([self._create_cache(im,self.frame_prop),duration])
            self._frame_prop=self.required_prop.copy()
        elif self.required_prop.is_transposed(self.frame_prop):
            # cached frames still exists, modify in-place if needed
            for frame in self._cache_frames:
                frame[0]=self._create_cache(frame[0],self.frame_prop)
            self._frame_prop=self.required_prop.copy()
        return self._cache_frames

    @property
    def cache_prop(self):
        if self._cache_prop is None:
            self._cache_prop=self.image_prop.copy()
        return self._cache_prop

    @property
    def frame_prop(self):
        if self._frame_prop is None:
            self._frame_prop=self.image_prop.copy()
        return self._frame_prop

    @property
    def required_prop(self):
        if self._required_prop is None:
            self._required_prop=self.cache_prop.copy()
        return self._required_prop

    def purge_cache(self):
        # purge cached image and all cached frames
        if self._cache is not None:
            _cache=self._cache
            self._cache=None
            _cache.close()
            while self._cache_frames:
                im,duration=self._cache_frames.pop()
                im.close()
        self._cache_prop=None
        self._frame_prop=None

    @property
    def original_size(self):
        # get the width and height of the original image
        return self.image_prop.size

    @property
    def original_pixel(self):
        # get the total pixel of the original image
        return self.image_prop.pixel

    @property
    def size(self):
        # get the width and height of required image
        # no rotation applied
        return self.required_prop.size

    @size.setter
    def size(self,size):
        # set the width and height of required image
        self.required_prop.size=size

    @property
    def pixel(self):
        # get the total pixel of required image
        return self.required_prop.pixel

    @property
    def resample(self):
        # get the resample filter of required image
        return self.required_prop.resample

    @resample.setter
    def resample(self,resample_filter):
        # set the resample filter of required image
        self.required_prop.resample=resample_filter

    @property
    def rotation(self):
        # get the rotation of required image
        return self.required_prop.rotation

    @rotation.setter
    def rotation(self,rotation):
        # set the rotation of required image
        self.required_prop.rotation=rotation

    def _rotate(self,im):
        # apply rotation on im and return rotated copy
        with im.transpose(_ROTATE_DICT[self.required_prop.total_rotation]) as copy:
            return copy

    def _flip(self,im):
        # apply flip on im and return flipped copy
        # NOTE: vflip and hflip should never be both True
        if self.required_prop.vflip:
            with im.transpose(Image.FLIP_TOP_BOTTOM) as copy:
                return copy
        if self.required_prop.hflip:
            with im.transpose(Image.FLIP_LEFT_RIGHT) as copy:
                return copy
        return im

    def _scale(self,im,right_angle=False):
        # apply scale on im and return scaled copy
        # reverse width and height if right_angle is True
        # TODO: box/reducing_gap
        with im.resize(reversed(self.size) if right_angle else self.size,
                       resample=self.resample) as copy:
            return copy

    def _enhance(self,im):
        # apply enhance on im and return enhanced copy
        # TODO
        with im.copy() as copy:
            return copy

    def _precache(self,im,right_angle=False):
        # create a pixel-changed only copy of im
        # NOTE: do scale at first no matter upscale or downscale
        return self._enhance(self._scale(im,right_angle=right_angle))

    def _transpose(self,im):
        # create a transposed only copy of im
        return self._rotate(self._flip(im))

    def _create_cache(self,im,prop):
        # create a cached copy of im. prop is the prop of im.
        if im is None:
            # use original image
            with self.image.copy() as im:pass
        if self.required_prop.is_pixel_changed(prop):
            # pixel changed
            if self.original_pixel>self.pixel:
                # image downscaled, do precache before transpose
                return self._transpose(self._precache(im))
            if self.original_pixel<self.pixel:
                # image upscaled, do transpose before precache
                return self._precache(self._transpose(im),right_angle=True)
        if self.required_prop.is_transposed(prop):
            # pixel not changed, but still need to do transpose
            return self._transpose(im)
        # nothing changed
        return im

    def _load_fallback(self,data,animation=False,n_frames=1):
        # load image from data using GdkPixbuf.
        loader=GdkPixbuf.PixbufAnimation if animation else GdkPixbuf.Pixbuf
        with GioStreamIO(data) as stream:
            pixbuf=loader.new_from_stream(stream)
            if not animation or n_frames<2:
                # return static image if n_frames is less than 2.
                # GdkPixbuf.PixbufAnimation does not report total frames.
                self.image=_pixbuf2pil(pixbuf)
                try:
                    orientation=int(pixbuf.get_option('orientation'))
                except:
                    pass
                else:
                    self.exif[274]=orientation
                return
            self.image=_pixbuf2pil(pixbuf.get_static_image())
            frame_iter=pixbuf.get_iter(cur:=GLib.TimeVal())
            for n in range(n_frames):
                frame=(frame_ref:=frame_iter.get_pixbuf()).copy()
                frame_ref.copy_options(frame)
                cur.tv_usec+=(delay:=frame_iter.get_delay_time())*1000
                while not frame_iter.advance(cur):
                    cur.tv_usec+=(delay:=delay+frame_iter.get_delay_time())*1000
                self.add_frame(_pixbuf2pil(frame),delay)
                if n==n_frames-1:
                    return

    def load(self,data,enable_anime=False):
        # load image from data, set to self.image and append to self.frames.
        try:
            with Image.open(BytesIO(data)) as im:
                im.load()
        except:
            # unsupported by PIL, fallback to GdkPixbuf.
            # disable animation if unsupported by PIL.
            return self._load_fallback(data)
        if not (enable_anime and getattr(im,'is_animated',False)):
            self.image=im
            return
        if im.format=='GIF' and im.mode=='P':
            # fallback to GdkPixbuf for gif animation
            # See https://github.com/python-pillow/Pillow/labels/GIF
            self._load_fallback(data,animation=True,n_frames=im.n_frames)
        else:
            for n,frame in enumerate(ImageSequence.Iterator(im)):
                if n==0:
                    self.image=frame
                self.add_frame(frame,int(frame.info.get('duration',0)))
            if isinstance(background:=im.info.get('background',0),tuple):
                self._bgcolor=int(''.join(f'{c:02x}' for c in background),16)
            else:
                self._bgcolor=background
        self._loop=im.info['loop']

    # TODO: more property and method

if __name__=='__main__':
    import sys
    import time

    class Timer:
        def __init__(self,prefix):
            self.prefix=prefix
            self.start=time.time()
        def __enter__(self):
            return self
        def __exit__(self,etype,value,tb):
            print(self.prefix,time.time()-self.start)

    m=Mage()
    with open(sys.argv[1],mode='rb') as f:
        m.load(f.read(),enable_anime=True)
    with Timer('untouched'):
        print(m.cache,m.cache.entropy())
        for im,duration in m.cache_frames:
            print(duration,im,im.entropy())
    with Timer('rotate'):
        m.rotation=270
        print(m.cache,m.cache.entropy())
        for im,duration in m.cache_frames:
            print(duration,im,im.entropy())
    with Timer('scale'):
        m.resample=Image.LANCZOS
        w,h=m.size
        m.size=(w*2,h*2)
        print(m.cache,m.cache.entropy())
        for im,duration in m.cache_frames:
            print(duration,im,im.entropy())
    with Timer('rotate after scale'):
        m.rotation=90
        print(m.cache,m.cache.entropy())
        for im,duration in m.cache_frames:
            print(duration,im,im.entropy())
    input('end')

# Local Variables:
# coding: utf-8
# mode: python
# python-indent-offset: 4
# indent-tabs-mode: nil
# End:

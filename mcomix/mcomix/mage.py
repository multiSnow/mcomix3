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
    _attrib_pixel=(
        # resize
        'size','resample','reducing','position','viewsize',
        # enhance
        'enhance_colorbalance','enhance_contrast',
        'enhance_brightness','enhance_sharpness',
        'autocontrast',
    )
    # pixel-unrelated attribute
    _attrib_trans=(
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

    def merge_transposition(self):
        if self.vflip and self.hflip:
            self.vflip=False
            self.hflip=False
            self.rotation+=180

    def keys(self):
        yield from self._attrib_pixel
        yield from self._attrib_trans

    def copy(self):
        # deep copy
        copy=MageProp()
        for key in self.keys():
            setattr(copy,key,getattr(self,key))
        assert self==copy
        return copy

    def __eq__(self,other):
        assert isinstance(other,MageProp)
        for key in self._attrib_pixel:
            if getattr(self,key)!=getattr(other,key):
                return False
        return self.total_rotation==other.total_rotation

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

    def _create_cache(self,im):
        copy=im.copy()
        if self.size!=self.original_size:
            # TODO: box/reducing_gap
            copy=copy.resize(self.size,resample=self.required_prop.resample)
        if rotation:=self.required_prop.total_rotation:
            copy=copy.transpose(_ROTATE_DICT[rotation])
        if self.required_prop.vflip:
            copy=copy.transpose(Image.FLIP_TOP_BOTTOM)
        if self.required_prop.hflip:
            copy=copy.transpose(Image.FLIP_LEFT_RIGHT)
        # TODO: enhance
        return copy

    @property
    def cache(self):
        # get cached image, generate if not cached yet or need to be changed.
        if self.cache_prop!=self.required_prop:
            self.purge_cache()
        if self._cache is None:
            self._cache=self._create_cache(self.image)
            self._cache_prop=self.required_prop.copy()
        return self._cache

    @property
    def cache_frames(self):
        # get cached frames, generate if not cached yet.
        if self.frames and not self._cache_frames:
            for im,duration in self.frames:
                self._cache_frames.append((self._create_cache(im),duration))
        return self._cache_frames

    @property
    def cache_prop(self):
        if self._cache_prop is None:
            self._cache_prop=self.image_prop.copy()
        return self._cache_prop

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

    @property
    def original_size(self):
        # get the (width, height) of the original image
        return self.image.size

    @property
    def size(self):
        # get the (width, height) of required image
        # no rotation applied
        return self.required_prop.size

    @size.setter
    def size(self,size):
        # set the (width, height) of required image
        self.required_prop.size=size

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
    m=Mage()
    with open(sys.argv[1],mode='rb') as f:
        m.load(f.read(),enable_anime=True)
    print('untouched')
    m.cache.load()
    print(m.cache,m.cache.entropy())
    for im,duration in m.cache_frames:
        im.load()
        print(duration,im,im.entropy())
    print('rotate')
    m.rotation=270
    m.cache.load()
    print(m.cache,m.cache.entropy())
    for im,duration in m.cache_frames:
        im.load()
        print(duration,im,im.entropy())
    print('scale')
    m.resample=Image.LANCZOS
    w,h=m.size
    m.size=(w*2,h*2)
    print(m.cache,m.cache.entropy())
    for im,duration in m.cache_frames:
        im.load()
        print(duration,im,im.entropy())
    input('end')

# Local Variables:
# coding: utf-8
# mode: python
# python-indent-offset: 4
# indent-tabs-mode: nil
# End:

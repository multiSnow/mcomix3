'''mage.py - the i(nternal)mage class.'''

# the 'Pixbuf' instance
from gi.repository import GdkPixbuf
# the 'PImage' instance
from PIL import Image

class Mage:
    def __init__(self,image=None):

        # original image as PImage, or the first frame of animation
        self._im=image
        # a list of (PImage,int), as the frame and duration
        # if image is not animation, it should be empty.
        self._frames=[]
        # original background color as int (#RRGGBBAA).
        self._bgcolor=0
        # bytes data of color profile, or None.
        self._icc=None
        # bytes data of exif, or None.
        self._exif=None

        # original image object, a list of (PImage,int)
        self._cache=[]
        # rotation of cache from original, should be in (0, 90, 180, 270).
        self._rotation=0
        # scale filter of cache.
        self._filter=None

        # thumbnail as Pixbuf.
        # fast scale filter, no icc, no animation.
        self._thumbnail=None

    @property
    def original_size(self):
        return self._im.size

    @property
    def size(self):
        raise NotImplementedError('property: Mage.size')

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self,rotation):
        raise NotImplementedError('setter: Mage.rotation')

    # TODO: more property and method

# Local Variables:
# coding: utf-8
# mode: python
# python-indent-offset: 4
# indent-tabs-mode: nil
# End:

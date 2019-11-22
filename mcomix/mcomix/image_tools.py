'''image_tools.py - Various image manipulations.'''

import binascii
from functools import reduce
from io import BytesIO
import os
import re
import sys
import operator

from gi.repository import GdkPixbuf, Gdk, Gio, GLib, Gtk
from PIL import Image
from PIL import ImageEnhance
from PIL import ImageOps
from PIL import ImageSequence

from mcomix import anime_tools
from mcomix import constants
from mcomix import log
from mcomix.lib import reader
from mcomix.lib import FlifImagePlugin
from mcomix.preferences import prefs

# Fallback pixbuf for missing images.
MISSING_IMAGE_ICON = None

_missing_icon_dialog = Gtk.Dialog()
_missing_icon_pixbuf = _missing_icon_dialog.render_icon(
    Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.LARGE_TOOLBAR
)
MISSING_IMAGE_ICON = _missing_icon_pixbuf
assert MISSING_IMAGE_ICON

GTK_GDK_COLOR_BLACK = Gdk.color_parse('black')
GTK_GDK_COLOR_WHITE = Gdk.color_parse('white')

if prefs['try FLIF support']:
    FlifImagePlugin._init_plugin()

def _getexif(im):
    exif={}
    try:
        exif.update(im.getexif())
    except AttributeError:
        pass
    if exif:
        return exif

    # Exif of PNG is still buggy in Pillow 6.0.0
    try:
        l1,l2,size,*lines=im.info.get('Raw profile type exif').splitlines()
        if l2!='exif':
            # Not valid Exif data.
            return {}
        size=int(size)
        data=binascii.unhexlify(''.join(lines))
        if len(data)!=size:
            # Size not match.
            return {}
        im.info['exif']=data
    except:
        # Not valid Exif data.
        return {}

    # load Exif again
    try:
        exif.update(im.getexif())
    except AttributeError:
        pass
    return exif

def rotate_pixbuf(src, rotation):
    rotation %= 360
    if 0 == rotation:
        return src
    if 90 == rotation:
        return src.rotate_simple(GdkPixbuf.PixbufRotation.CLOCKWISE)
    if 180 == rotation:
        return src.rotate_simple(GdkPixbuf.PixbufRotation.UPSIDEDOWN)
    if 270 == rotation:
        return src.rotate_simple(GdkPixbuf.PixbufRotation.COUNTERCLOCKWISE)
    raise ValueError('unsupported rotation: %s' % rotation)

def get_fitting_size(source_size, target_size,
                     keep_ratio=True, scale_up=False):
    ''' Return a scaled version of <source_size>
    small enough to fit in <target_size>.

    Both <source_size> and <target_size>
    must be (width, height) tuples.

    If <keep_ratio> is True, aspect ratio is kept.

    If <scale_up> is True, <source_size> is scaled up
    when smaller than <target_size>.
    '''
    width, height = target_size
    src_width, src_height = source_size
    if not scale_up and src_width <= width and src_height <= height:
        width, height = src_width, src_height
    else:
        if keep_ratio:
            if float(src_width) / width > float(src_height) / height:
                height = int(max(src_height * width / src_width, 1))
            else:
                width = int(max(src_width * height / src_height, 1))
    return (width, height)

def trans_pixbuf(src,flip=False,flop=False):
    if is_animation(src):
        return anime_tools.frame_executor(
            src, trans_pixbuf,
            kwargs=dict(flip=flip, flop=flop)
        )
    if flip: src = src.flip(horizontal=False)
    if flop: src = src.flip(horizontal=True)
    return src

def fit_pixbuf_to_rectangle(src, rect, rotation):
    if is_animation(src):
        return anime_tools.frame_executor(
            src, fit_pixbuf_to_rectangle,
            args=(rect, rotation)
        )
    return fit_in_rectangle(src, rect[0], rect[1],
                            rotation=rotation,
                            keep_ratio=False,
                            scale_up=True)

def fit_in_rectangle(src, width, height, keep_ratio=True, scale_up=False,
                     rotation=0, scaling_quality=None):
    '''Scale (and return) a pixbuf so that it fits in a rectangle with
    dimensions <width> x <height>. A negative <width> or <height>
    means an unbounded dimension - both cannot be negative.

    If <rotation> is 90, 180 or 270 we rotate <src> first so that the
    rotated pixbuf is fitted in the rectangle.

    Unless <scale_up> is True we don't stretch images smaller than the
    given rectangle.

    If <keep_ratio> is True, the image ratio is kept, and the result
    dimensions may be smaller than the target dimensions.

    If <src> has an alpha channel it gets a checkboard background.
    '''
    # "Unbounded" really means "bounded to 10000 px" - for simplicity.
    # MComix would probably choke on larger images anyway.
    if width < 0:
        width = 100000
    elif height < 0:
        height = 100000
    width = max(width, 1)
    height = max(height, 1)

    rotation %= 360
    if rotation not in (0, 90, 180, 270):
        raise ValueError('unsupported rotation: %s' % rotation)
    if rotation in (90, 270):
        width, height = height, width

    if scaling_quality is None:
        scaling_quality = prefs['scaling quality']

    src_width = src.get_width()
    src_height = src.get_height()

    width, height = get_fitting_size((src_width, src_height),
                                     (width, height),
                                     keep_ratio=keep_ratio,
                                     scale_up=scale_up)

    if src.get_has_alpha():
        if prefs['checkered bg for transparent images']:
            check_size, color1, color2 = 8, 0x777777, 0x999999
        else:
            check_size, color1, color2 = 1024, 0xFFFFFF, 0xFFFFFF
        if width == src_width and height == src_height:
            # Using anything other than nearest interpolation will result in a
            # modified image if no resizing takes place (even if it's opaque).
            scaling_quality = GdkPixbuf.InterpType.NEAREST
        src = src.composite_color_simple(width, height, scaling_quality,
                                         255, check_size, color1, color2)
    elif width != src_width or height != src_height:
        src = src.scale_simple(width, height, scaling_quality)

    src = rotate_pixbuf(src, rotation)

    return src

def add_border(pixbuf, thickness, colour=0x000000FF):
    '''Return a pixbuf from <pixbuf> with a <thickness> px border of
    <colour> added.
    '''
    canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8,
                                  pixbuf.get_width() + thickness * 2,
                                  pixbuf.get_height() + thickness * 2)
    canvas.fill(colour)
    pixbuf.copy_area(0, 0, pixbuf.get_width(), pixbuf.get_height(),
        canvas, thickness, thickness)
    return canvas


def get_most_common_edge_color(pixbufs, edge=2):
    '''Return the most commonly occurring pixel value along the four edges
    of <pixbuf>. The return value is a sequence, (r, g, b), with 16 bit
    values. If <pixbuf> is a tuple, the edges will be computed from
    both the left and the right image.

    Note: This could be done more cleanly with subpixbuf(), but that
    doesn't work as expected together with get_pixels().
    '''

    def group_colors(colors, steps=10):
        ''' This rounds a list of colors in C{colors} to the next nearest value,
        i.e. 128, 83, 10 becomes 130, 85, 10 with C{steps}=5. This compensates for
        dirty colors where no clear dominating color can be made out.

        @return: The color that appears most often in the prominent group.'''

        # Start group
        group = (0, 0, 0)
        # List of (count, color) pairs, group contains most colors
        colors_in_prominent_group = []
        color_count_in_prominent_group = 0
        # List of (count, color) pairs, current color group
        colors_in_group = []
        color_count_in_group = 0

        for count, color in colors:

            # Round color
            rounded = [0] * len(color)
            for i, color_value in enumerate(color):
                if steps % 2 == 0:
                    middle = steps // 2
                else:
                    middle = steps // 2 + 1

                remainder = color_value % steps
                if remainder >= middle:
                    color_value = color_value + (steps - remainder)
                else:
                    color_value = color_value - remainder

                rounded[i] = min(255, max(0, color_value))

            # Change prominent group if necessary
            if rounded == group:
                # Color still fits in the previous color group
                colors_in_group.append((count, color))
                color_count_in_group += count
            else:
                # Color group changed, check if current group has more colors
                # than last group
                if color_count_in_group > color_count_in_prominent_group:
                    colors_in_prominent_group = colors_in_group
                    color_count_in_prominent_group = color_count_in_group

                group = rounded
                colors_in_group = [ (count, color) ]
                color_count_in_group = count

        # Cleanup if only one edge color group was found
        if color_count_in_group > color_count_in_prominent_group:
            colors_in_prominent_group = colors_in_group

        colors_in_prominent_group.sort(key=operator.itemgetter(0), reverse=True)
        # List is now sorted by color count, first color appears most often
        return colors_in_prominent_group[0][1]

    def get_edge_pixbuf(pixbuf, side, edge):
        ''' Returns a pixbuf corresponding to the side passed in <side>.
        Valid sides are 'left', 'right', 'top', 'bottom'. '''
        pixbuf = static_image(pixbuf)
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        edge = min(edge, width, height)

        subpix = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                      pixbuf.get_has_alpha(), 8, edge, height)
        if side == 'left':
            pixbuf.copy_area(0, 0, edge, height, subpix, 0, 0)
        elif side == 'right':
            pixbuf.copy_area(width - edge, 0, edge, height, subpix, 0, 0)
        elif side == 'top':
            pixbuf.copy_area(0, 0, width, edge, subpix, 0, 0)
        elif side == 'bottom':
            pixbuf.copy_area(0, height - edge, width, edge, subpix, 0, 0)
        else:
            assert False, 'Invalid edge side'

        return subpix

    if not pixbufs:
        return (0, 0, 0)

    if not isinstance(pixbufs, (tuple, list)):
        left_edge = get_edge_pixbuf(pixbufs, 'left', edge)
        right_edge = get_edge_pixbuf(pixbufs, 'right', edge)
    else:
        assert len(pixbufs) == 2, 'Expected two pages in list'
        left_edge = get_edge_pixbuf(pixbufs[0], 'left', edge)
        right_edge = get_edge_pixbuf(pixbufs[1], 'right', edge)

    # Find all edge colors. Color count is separate for all four edges
    ungrouped_colors = []
    for edge in (left_edge, right_edge):
        im = pixbuf_to_pil(edge)
        ungrouped_colors.extend(im.getcolors(im.size[0] * im.size[1]))

    # Sum up colors from all edges
    ungrouped_colors.sort(key=operator.itemgetter(1))
    most_used = group_colors(ungrouped_colors)
    return [color/255 for color in most_used]

def pil_to_pixbuf(im, keep_orientation=False):
    '''Return a pixbuf created from the PIL <im>.'''
    if im.mode.startswith('RGB'):
        has_alpha = im.mode == 'RGBA'
    elif im.mode in ('LA', 'P'):
        has_alpha = True
    else:
        has_alpha = False
    target_mode = 'RGBA' if has_alpha else 'RGB'
    if im.mode != target_mode:
        im = im.convert(target_mode)
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        GLib.Bytes.new(im.tobytes()), GdkPixbuf.Colorspace.RGB,
        has_alpha, 8,
        im.size[0], im.size[1],
        (4 if has_alpha else 3) * im.size[0]
    )
    if keep_orientation:
        # Keep orientation metadata.
        orientation = _getexif(im).get(274, None)
        if orientation is not None:
            setattr(pixbuf, 'orientation', str(orientation))
    return pixbuf

def pixbuf_to_pil(pixbuf):
    '''Return a PIL image created from <pixbuf>.'''
    dimensions = pixbuf.get_width(), pixbuf.get_height()
    stride = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()
    mode = 'RGBA' if pixbuf.get_has_alpha() else 'RGB'
    im = Image.frombuffer(mode, dimensions, pixels, 'raw', mode, stride, 1)
    return im

def is_animation(pixbuf):
    return isinstance(pixbuf, GdkPixbuf.PixbufAnimation)

def disable_transform(pixbuf):
    if is_animation(pixbuf):
        if not hasattr(pixbuf,'_framebuffer'):
            return True
        if not prefs['animation transform']:
            return True
    return False

def static_image(pixbuf):
    ''' Returns a non-animated version of the specified pixbuf. '''
    if is_animation(pixbuf):
        return pixbuf.get_static_image()
    return pixbuf

def unwrap_image(image):
    ''' Returns an object that contains the image data based on
    gtk.Image.get_storage_type or None if image is None or image.get_storage_type
    returns Gtk.ImageType.EMPTY. '''
    if image is None:
        return None
    t = image.get_storage_type()
    if t == Gtk.ImageType.EMPTY:
        return None
    if t == Gtk.ImageType.PIXBUF:
        return image.get_pixbuf()
    if t == Gtk.ImageType.ANIMATION:
        return image.get_animation()
    if t == Gtk.ImageType.PIXMAP:
        return image.get_pixmap()
    if t == Gtk.ImageType.IMAGE:
        return image.get_image()
    if t == Gtk.ImageType.STOCK:
        return image.get_stock()
    if t == Gtk.ImageType.ICON_SET:
        return image.get_icon_set()
    raise ValueError()

def set_from_pixbuf(image, pixbuf):
    if is_animation(pixbuf):
        return image.set_from_animation(pixbuf)
    else:
        return image.set_from_pixbuf(pixbuf)

def load_animation(im):
    if im.format=='GIF' and im.mode=='P':
        # TODO: Pillow has bug with gif animation
        # https://github.com/python-pillow/Pillow/labels/GIF
        raise NotImplementedError('Pillow has bug with gif animation, '
                                  'fallback to GdkPixbuf')
    anime=anime_tools.AnimeFrameBuffer(im.n_frames,loop=im.info['loop'])
    background=im.info.get('background',None)
    if isinstance(background,tuple):
        color=0
        for n,c in enumerate(background):
            color|=c<<n*8
        background=color
    frameiter=ImageSequence.Iterator(im)
    for n,frame in enumerate(frameiter):
        anime.add_frame(n,pil_to_pixbuf(frame),
                        frame.info.get('duration',0),
                        background=background)
    return anime.create_animation()

def load_pixbuf(path):
    ''' Loads a pixbuf from a given image file. '''
    enable_anime = prefs['animation mode'] != constants.ANIMATION_DISABLED
    try:
        with Image.open(reader.LockedFileIO(path)) as im:
            # make sure n_frames loaded
            im.load()
            if enable_anime and getattr(im,'is_animated',False):
                return load_animation(im)
            return pil_to_pixbuf(im, keep_orientation=True)
    except:
        pass
    if enable_anime:
        pixbuf = GdkPixbuf.PixbufAnimation.new_from_file(path)
        if pixbuf.is_static_image():
            return pixbuf.get_static_image()
        return pixbuf
    return GdkPixbuf.Pixbuf.new_from_file(path)

def load_pixbuf_size(path, width, height):
    ''' Loads a pixbuf from a given image file and scale it to fit
    inside (width, height). '''
    try:
        with Image.open(reader.LockedFileIO(path)) as im:
            im.thumbnail((width, height), resample=Image.BOX)
            return pil_to_pixbuf(im, keep_orientation=True)
    except:
        info, image_width, image_height = GdkPixbuf.Pixbuf.get_file_info(path)
        # If we could not get the image info, still try to load
        # the image to let GdkPixbuf raise the appropriate exception.
        if not info:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        # Don't upscale if smaller than target dimensions!
        if image_width <= width and image_height <= height:
            width, height = image_width, image_height
        # Work around GdkPixbuf bug
        # https://gitlab.gnome.org/GNOME/gdk-pixbuf/issues/45
        # TODO: GIF should be always supported by Pillow.
        #       Is this workaround really needed?
        if info.get_name() == 'gif':
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        else:
            # directly return pixbuf
            return GdkPixbuf.Pixbuf.new_from_file_at_size(path, width, height)
        return fit_in_rectangle(pixbuf, width, height,
                                scaling_quality=GdkPixbuf.InterpType.BILINEAR)

def load_pixbuf_data(imgdata):
    ''' Loads a pixbuf from the data passed in <imgdata>. '''
    try:
        with Image.open(BytesIO(imgdata)) as im:
            return pil_to_pixbuf(im, keep_orientation=True)
    except:
        pass
    loader = GdkPixbuf.PixbufLoader()
    loader.write(imgdata)
    loader.close()
    return loader.get_pixbuf()

def enhance(pixbuf, brightness=1.0, contrast=1.0, saturation=1.0,
            sharpness=1.0, autocontrast=False):
    '''Return a modified pixbuf from <pixbuf> where the enhancement operations
    corresponding to each argument has been performed. A value of 1.0 means
    no change. If <autocontrast> is True it overrides the <contrast> value,
    but only if the image mode is supported by ImageOps.autocontrast (i.e.
    it is L or RGB.)
    '''
    if is_animation(pixbuf):
        return anime_tools.frame_executor(
            pixbuf, enhance,
            kwargs=dict(
                brightness=brightness, contrast=contrast,
                saturation=saturation, sharpness=1.0,
                autocontrast=False
            )
        )
    im = pixbuf_to_pil(pixbuf)
    if brightness != 1.0:
        im = ImageEnhance.Brightness(im).enhance(brightness)
    if autocontrast and im.mode in ('L', 'RGB'):
        im = ImageOps.autocontrast(im, cutoff=0.1)
    elif contrast != 1.0:
        im = ImageEnhance.Contrast(im).enhance(contrast)
    if saturation != 1.0:
        im = ImageEnhance.Color(im).enhance(saturation)
    if sharpness != 1.0:
        im = ImageEnhance.Sharpness(im).enhance(sharpness)
    return pil_to_pixbuf(im)

def get_implied_rotation(pixbuf):
    '''Return the implied rotation in degrees: 0, 90, 180, or 270.

    The implied rotation is the angle (in degrees) that the raw pixbuf should
    be rotated in order to be displayed "correctly". E.g. a photograph taken
    by a camera that is held sideways might store this fact in its Exif data,
    and the pixbuf loader will set the orientation option correspondingly.
    '''
    pixbuf = static_image(pixbuf)
    orientation = getattr(pixbuf, 'orientation', None)
    if orientation is None:
        orientation = pixbuf.get_option('orientation')
    if orientation == '3':
        return 180
    elif orientation == '6':
        return 90
    elif orientation == '8':
        return 270
    return 0

def combine_pixbufs( pixbuf1, pixbuf2, are_in_manga_mode ):
    if are_in_manga_mode:
        r_source_pixbuf = pixbuf1
        l_source_pixbuf = pixbuf2
    else:
        l_source_pixbuf = pixbuf1
        r_source_pixbuf = pixbuf2

    has_alpha = False

    if l_source_pixbuf.get_property('has-alpha') or \
       r_source_pixbuf.get_property('has-alpha'):
        has_alpha = True

    bits_per_sample = 8

    l_source_pixbuf_width = l_source_pixbuf.get_property('width')
    r_source_pixbuf_width = r_source_pixbuf.get_property('width')

    l_source_pixbuf_height = l_source_pixbuf.get_property('height')
    r_source_pixbuf_height = r_source_pixbuf.get_property('height')

    new_width = l_source_pixbuf_width + r_source_pixbuf_width

    new_height = max(l_source_pixbuf_height, r_source_pixbuf_height)

    new_pix_buf = GdkPixbuf.Pixbuf.new(colorspace=GdkPixbuf.Colorspace.RGB,
                                       has_alpha=has_alpha,
                                       bits_per_sample=bits_per_sample,
                                       width=new_width, height=new_height)

    l_source_pixbuf.copy_area(0, 0, l_source_pixbuf_width,
                               l_source_pixbuf_height,
                               new_pix_buf, 0, 0)

    r_source_pixbuf.copy_area(0, 0, r_source_pixbuf_width,
                              r_source_pixbuf_height,
                              new_pix_buf, l_source_pixbuf_width, 0)

    return new_pix_buf

def convert_rgb16list_to_rgba8int(c):
    return 0x000000FF | (c[0] >> 8 << 24) | (c[1] >> 8 << 16) | (c[2] >> 8 << 8)

def rgb_to_y_601(color):
    return color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114

def text_color_for_background_color(bgcolor):
    return GTK_GDK_COLOR_BLACK if rgb_to_y_601(bgcolor) >= \
        65535.0 / 2.0 else GTK_GDK_COLOR_WHITE

def get_image_info(path):
    '''Return image informations:
        (format, width, height)
    '''
    info = None
    try:
        with Image.open(reader.LockedFileIO(path)) as im:
            return (im.format,) + im.size
    except:
        info = GdkPixbuf.Pixbuf.get_file_info(path)
        if info[0] is None:
            info = None
        else:
            info = info[0].get_name().upper(), info[1], info[2]
    if info is None:
        info = (_('Unknown filetype'), 0, 0)
    return info

SUPPORTED_IMAGE_EXTS=set()
SUPPORTED_IMAGE_MIMES=set()
SUPPORTED_IMAGE_FORMATS={}

def init_supported_formats():
    # formats supported by PIL
    # Make sure all supported formats are registered.
    Image.init()
    for ext,name in Image.EXTENSION.items():
        fmt=SUPPORTED_IMAGE_FORMATS.setdefault(name,(set(),set()))
        fmt[1].add(ext.lower())
        mime=Image.MIME.get(
            name, Gio.content_type_guess(filename='file'+ext)[0]).lower()
        if mime and mime != 'application/octet-stream':
            fmt[0].add(mime)

    # formats supported by gdk-pixbuf
    for gdkfmt in GdkPixbuf.Pixbuf.get_formats():
        fmt=SUPPORTED_IMAGE_FORMATS.setdefault(
            gdkfmt.get_name().upper(),(set(),set()))
        for m in map(lambda s:s.lower(),gdkfmt.get_mime_types()):
            fmt[0].add(m)
        # get_extensions() return extensions without '.'
        for e in map(lambda s:'.'+s.lower(),gdkfmt.get_extensions()):
            fmt[1].add(e)
            m = Gio.content_type_guess(filename='file'+e)[0].lower()
            if m and m != 'application/octet-stream':
                fmt[0].add(m)

    # cache a supported extensions list
    for mimes,exts in SUPPORTED_IMAGE_FORMATS.values():
        SUPPORTED_IMAGE_EXTS.update(exts)
        SUPPORTED_IMAGE_MIMES.update(mimes)

def get_supported_formats():
    if not SUPPORTED_IMAGE_FORMATS:
        init_supported_formats()
    return SUPPORTED_IMAGE_FORMATS

def is_image_file(path, check_mimetype=False):
    # if check_mimetype is True,
    # read starting bytes and using Gio.content_type_guess
    # to guess if path is supported, ignoring file extension.
    if not SUPPORTED_IMAGE_FORMATS:
        init_supported_formats()
    if prefs['check image mimetype'] and check_mimetype and os.path.isfile(path):
        with open(path, mode='rb') as fd:
            magic = fd.read(10)
        mime, uncertain = Gio.content_type_guess(data=magic)
        return mime.lower() in SUPPORTED_IMAGE_MIMES
    return path.lower().endswith(tuple(SUPPORTED_IMAGE_EXTS))

# vim: expandtab:sw=4:ts=4

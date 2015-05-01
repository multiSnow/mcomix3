"""image_tools.py - Various image manipulations."""

from collections import namedtuple
import binascii
import re
import sys
import operator
import gtk
from PIL import Image
from PIL import ImageEnhance
from PIL import ImageOps
from PIL.JpegImagePlugin import _getexif
try:
    from PIL import PILLOW_VERSION
    PIL_VERSION = ('Pillow', PILLOW_VERSION)
except ImportError:
    from PIL import VERSION as PIL_VERSION
    PIL_VERSION = ('PIL', PIL_VERSION)
from cStringIO import StringIO

from mcomix.preferences import prefs
from mcomix import constants
from mcomix import log


if sys.platform == 'win32':
    # Works around GTK's slowness on Win32 by using PIL
    # for loading instead and converting it afterwards.
    USE_PIL = True
else:
    USE_PIL = False

log.info('Using %s for loading images (versions: %s [%s], GDK [%s])',
         'PIL' if USE_PIL else 'GDK',
         PIL_VERSION[0], PIL_VERSION[1],
         # Unfortunately gdk_pixbuf_version is not exported,
         # so show the GTK+ version instead.
         'GTK+ ' + '.'.join(map(str, gtk.gtk_version)))


def rotate_pixbuf(src, rotation):
    rotation %= 360
    if 0 == rotation:
        return src
    if 90 == rotation:
        return src.rotate_simple(gtk.gdk.PIXBUF_ROTATE_CLOCKWISE)
    if 180 == rotation:
        return src.rotate_simple(gtk.gdk.PIXBUF_ROTATE_UPSIDEDOWN)
    if 270 == rotation:
        return src.rotate_simple(gtk.gdk.PIXBUF_ROTATE_COUNTERCLOCKWISE)
    raise ValueError("unsupported rotation: %s" % rotation)

def fit_pixbuf_to_rectangle(src, rect, rotation):
    return fit_in_rectangle(src, rect[0], rect[1],
                            rotation=rotation,
                            keep_ratio=False,
                            scale_up=True)

def fit_in_rectangle(src, width, height, keep_ratio=True, scale_up=False, rotation=0, scaling_quality=None):
    """Scale (and return) a pixbuf so that it fits in a rectangle with
    dimensions <width> x <height>. A negative <width> or <height>
    means an unbounded dimension - both cannot be negative.

    If <rotation> is 90, 180 or 270 we rotate <src> first so that the
    rotated pixbuf is fitted in the rectangle.

    Unless <scale_up> is True we don't stretch images smaller than the
    given rectangle.

    If <keep_ratio> is True, the image ratio is kept, and the result
    dimensions may be smaller than the target dimensions.

    If <src> has an alpha channel it gets a checkboard background.
    """
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
        raise ValueError("unsupported rotation: %s" % rotation)
    if rotation in (90, 270):
        width, height = height, width

    if scaling_quality is None:
        scaling_quality = prefs['scaling quality']

    src_width = src.get_width()
    src_height = src.get_height()

    if not scale_up and src_width <= width and src_height <= height:
        if src.get_has_alpha():
            if prefs['checkered bg for transparent images']:
                src = src.composite_color_simple(src_width, src_height,
                    scaling_quality, 255, 8, 0x777777, 0x999999)
            else:
                src = src.composite_color_simple(src_width, src_height,
                    scaling_quality, 255, 1024, 0xFFFFFF, 0xFFFFFF)
    else:
        if keep_ratio:
            if float(src_width) / width > float(src_height) / height:
                height = int(max(src_height * width / src_width, 1))
            else:
                width = int(max(src_width * height / src_height, 1))

        if src.get_has_alpha():
            if prefs['checkered bg for transparent images']:
                src = src.composite_color_simple(width, height,
                    scaling_quality, 255, 8, 0x777777, 0x999999)
            else:
                src = src.composite_color_simple(width, height,
                    scaling_quality, 255, 1024, 0xFFFFFF, 0xFFFFFF)
        elif width != src_width or height != src_height:
            src = src.scale_simple(width, height, prefs['scaling quality'])

    src = rotate_pixbuf(src, rotation)

    return src


def add_border(pixbuf, thickness, colour=0x000000FF):
    """Return a pixbuf from <pixbuf> with a <thickness> px border of
    <colour> added.
    """
    canvas = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8,
        pixbuf.get_width() + thickness * 2,
        pixbuf.get_height() + thickness * 2)
    canvas.fill(colour)
    pixbuf.copy_area(0, 0, pixbuf.get_width(), pixbuf.get_height(),
        canvas, thickness, thickness)
    return canvas


def get_most_common_edge_colour(pixbufs, edge=2):
    """Return the most commonly occurring pixel value along the four edges
    of <pixbuf>. The return value is a sequence, (r, g, b), with 16 bit
    values. If <pixbuf> is a tuple, the edges will be computed from
    both the left and the right image.

    Note: This could be done more cleanly with subpixbuf(), but that
    doesn't work as expected together with get_pixels().
    """

    def group_colors(colors, steps=10):
        """ This rounds a list of colors in C{colors} to the next nearest value,
        i.e. 128, 83, 10 becomes 130, 85, 10 with C{steps}=5. This compensates for
        dirty colors where no clear dominating color can be made out.

        @return: The color that appears most often in the prominent group."""

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
        """ Returns a pixbuf corresponding to the side passed in <side>.
        Valid sides are 'left', 'right', 'top', 'bottom'. """
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        edge = min(edge, width, height)

        subpix = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,
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
    return [color * 257 for color in most_used]

def pil_to_pixbuf(image, keep_orientation=False):
    """Return a pixbuf created from the PIL <image>."""
    if image.mode.startswith('RGB'):
        imagestr = image.tostring()
        has_alpha = image.mode == 'RGBA'
    else:
        imagestr = image.convert('RGB').tostring()
        has_alpha = False
    pixbuf = gtk.gdk.pixbuf_new_from_data(
        imagestr, gtk.gdk.COLORSPACE_RGB,
        has_alpha, 8,
        image.size[0], image.size[1],
        (4 if has_alpha else 3) * image.size[0]
    )
    if keep_orientation:
        # Keep orientation metadata.
        orientation = None
        exif = image.info.get('exif')
        if exif is not None:
            exif = _getexif(image)
            orientation = exif.get(274, None)
        if orientation is None:
            # Maybe it's a PNG? Try alternative method.
            orientation = _get_png_implied_rotation(image)
        if orientation is not None:
            setattr(pixbuf, 'orientation', str(orientation))
    return pixbuf

def pixbuf_to_pil(pixbuf):
    """Return a PIL image created from <pixbuf>."""
    dimensions = pixbuf.get_width(), pixbuf.get_height()
    stride = pixbuf.get_rowstride()
    pixels = pixbuf.get_pixels()
    mode = pixbuf.get_has_alpha() and 'RGBA' or 'RGB'
    image = Image.frombuffer(mode, dimensions, pixels, 'raw', mode, stride, 1)
    return image

def load_pixbuf(path):
    """ Loads a pixbuf from a given image file. """
    if USE_PIL:
        pixbuf = pil_to_pixbuf(Image.open(path), keep_orientation=True)
    else:
        pixbuf = gtk.gdk.pixbuf_new_from_file(path)
    return pixbuf

def load_pixbuf_size(path, width, height):
    """ Loads a pixbuf from a given image file and scale it to fit
    inside (width, height). """
    if USE_PIL:
        im = Image.open(path)
        im.thumbnail((width, height))
        pixbuf = pil_to_pixbuf(im, keep_orientation=True)
    else:
        format, image_width, image_height = get_image_info(path)
        # Do not rescale if smaller than target dimensions.
        if image_width <= width and image_height <= height:
            pixbuf = gtk.gdk.pixbuf_new_from_file(path)
            width, height = image_width, image_height
        else:
            # Work around GdkPixbuf bug: https://bugzilla.gnome.org/show_bug.cgi?id=735422
            if 'GIF' == format:
                pixbuf = gtk.gdk.pixbuf_new_from_file(path)
                pixbuf = fit_in_rectangle(pixbuf, width, height, scaling_quality=gtk.gdk.INTERP_BILINEAR)
            else:
                pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(path, width, height)
    if pixbuf.get_has_alpha():
        if prefs['checkered bg for transparent images']:
            pixbuf = pixbuf.composite_color_simple(width, height,
                prefs['scaling quality'], 255, 8, 0x777777, 0x999999)
        else:
            pixbuf = pixbuf.composite_color_simple(width, height,
                prefs['scaling quality'], 255, 1024, 0xFFFFFF, 0xFFFFFF)
    return pixbuf

def load_pixbuf_data(imgdata):
    """ Loads a pixbuf from the data passed in <imgdata>. """
    if USE_PIL:
        pixbuf = pil_to_pixbuf(Image.open(StringIO(imgdata)), keep_orientation=True)
    else:
        loader = gtk.gdk.PixbufLoader()
        loader.write(imgdata, len(imgdata))
        loader.close()
        pixbuf = loader.get_pixbuf()
    return pixbuf

def enhance(pixbuf, brightness=1.0, contrast=1.0, saturation=1.0,
  sharpness=1.0, autocontrast=False):
    """Return a modified pixbuf from <pixbuf> where the enhancement operations
    corresponding to each argument has been performed. A value of 1.0 means
    no change. If <autocontrast> is True it overrides the <contrast> value,
    but only if the image mode is supported by ImageOps.autocontrast (i.e.
    it is L or RGB.)
    """
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

def _get_png_implied_rotation(pixbuf_or_image):
    """Same as <get_implied_rotation> for PNG files.

    Lookup for Exif data in the tEXt chunk.
    """
    if isinstance(pixbuf_or_image, gtk.gdk.Pixbuf):
        exif = pixbuf_or_image.get_option('tEXt::Raw profile type exif')
    elif isinstance(pixbuf_or_image, Image.Image):
        exif = pixbuf_or_image.info.get('Raw profile type exif')
    else:
        raise ValueError()
    if exif is None:
        return None
    exif = exif.split('\n')
    if len(exif) < 4 or 'exif' != exif[1]:
        # Not valid Exif data.
        return None
    size = int(exif[2])
    try:
        data = binascii.unhexlify(''.join(exif[3:]))
    except TypeError:
        # Not valid hexadecimal content.
        return None
    if size != len(data):
        # Sizes should match.
        return None
    im = namedtuple('FakeImage', 'info')({ 'exif': data })
    exif = _getexif(im)
    orientation = exif.get(274, None)
    if orientation is not None:
        orientation = str(orientation)
    return orientation

def get_implied_rotation(pixbuf):
    """Return the implied rotation in degrees: 0, 90, 180, or 270.

    The implied rotation is the angle (in degrees) that the raw pixbuf should
    be rotated in order to be displayed "correctly". E.g. a photograph taken
    by a camera that is held sideways might store this fact in its Exif data,
    and the pixbuf loader will set the orientation option correspondingly.
    """
    orientation = getattr(pixbuf, 'orientation', None)
    if orientation is None:
        orientation = pixbuf.get_option('orientation')
    if orientation is None:
        # Maybe it's a PNG? Try alternative method.
        orientation = _get_png_implied_rotation(pixbuf)
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

    if l_source_pixbuf.get_property( 'has-alpha' ) or \
       r_source_pixbuf.get_property( 'has-alpha' ):
        has_alpha = True

    bits_per_sample = 8

    l_source_pixbuf_width = l_source_pixbuf.get_property( 'width' )
    r_source_pixbuf_width = r_source_pixbuf.get_property( 'width' )

    l_source_pixbuf_height = l_source_pixbuf.get_property( 'height' )
    r_source_pixbuf_height = r_source_pixbuf.get_property( 'height' )

    new_width = l_source_pixbuf_width + r_source_pixbuf_width

    new_height = max( l_source_pixbuf_height, r_source_pixbuf_height )

    new_pix_buf = gtk.gdk.Pixbuf( gtk.gdk.COLORSPACE_RGB, has_alpha,
        bits_per_sample, new_width, new_height )

    l_source_pixbuf.copy_area( 0, 0, l_source_pixbuf_width,
                                     l_source_pixbuf_height,
                                     new_pix_buf, 0, 0 )

    r_source_pixbuf.copy_area( 0, 0, r_source_pixbuf_width,
                                     r_source_pixbuf_height,
                                     new_pix_buf, l_source_pixbuf_width, 0 )

    return new_pix_buf

def is_image_file(path):
    """Return True if the file at <path> is an image file recognized by PyGTK.
    """
    return SUPPORTED_IMAGE_REGEX.search(path) is not None

def convert_rgb16list_to_rgba8int(c):
    return 0x000000FF | (c[0] >> 8 << 24) | (c[1] >> 8 << 16) | (c[2] >> 8 << 8)

def rgb_to_y_601(color):
    return color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114

def text_color_for_background_color(bgcolor):
    return constants.GTK_GDK_COLOR_BLACK if rgb_to_y_601(bgcolor) >= \
        65535.0 / 2.0 else constants.GTK_GDK_COLOR_WHITE

def get_image_info(path):
    """Return image informations:
        (format, width, height)
    """
    info = None
    if USE_PIL:
        try:
            im = Image.open(path)
            info = (im.format,) + im.size
        except IOError:
            # If the file cannot be found, or the image
            # cannot be opened and identified.
            im = None
    else:
        info = gtk.gdk.pixbuf_get_file_info(path)
        if info is not None:
            info = info[0]['name'].upper(), info[1], info[2]
    if info is None:
        info = (_('Unknown filetype'), 0, 0)
    return info

def get_supported_formats():
    if USE_PIL:
        # Make sure all supported formats are registered.
        Image.init()
        # Not all PIL formats register a mime type,
        # fill in the blanks ourselves.
        supported_formats = {
            'BMP': (['image/bmp', 'image/x-bmp', 'image/x-MS-bmp'], []),
            'ICO': (['image/x-icon', 'image/x-ico', 'image/x-win-bitmap'], []),
            'PCX': (['image/x-pcx'], []),
            'PPM': (['image/x-portable-pixmap'], []),
            'TGA': (['image/x-tga'], []),
        }
        for name, mime in Image.MIME.items():
            mime_types, extensions = supported_formats.get(name, ([], []))
            supported_formats[name] = mime_types + [mime], extensions
        for ext, name in Image.EXTENSION.items():
            assert '.' == ext[0]
            mime_types, extensions = supported_formats.get(name, ([], []))
            supported_formats[name] = mime_types, extensions + [ext[1:]]
        # Remove formats with no mime type or extension.
        for name in supported_formats.keys():
            mime_types, extensions = supported_formats[name]
            if not mime_types or not extensions:
                del supported_formats[name]
        # Remove archives/videos formats.
        for name in (
            'MPEG',
            'PDF',
        ):
            if name in supported_formats:
                del supported_formats[name]
    else:
        supported_formats = {}
        for format in gtk.gdk.pixbuf_get_formats():
            name = format['name'].upper()
            assert name not in supported_formats
            supported_formats[name] = (
                format['mime_types'],
                format['extensions'],
            )
    return supported_formats

# Set supported image extensions regexp from list of supported formats.
SUPPORTED_IMAGE_REGEX = re.compile(r'\.(%s)$' %
                                   '|'.join(sorted(reduce(
                                       operator.add,
                                       [fmt[1] for fmt
                                        in get_supported_formats().values()]
                                   ))), re.I)

# vim: expandtab:sw=4:ts=4

# coding: utf-8

import binascii
import os
import sys
import tempfile

import gtk, gobject

from collections import namedtuple
from PIL import Image, ImageDraw
from cStringIO import StringIO
from difflib import unified_diff

from . import MComixTest

from mcomix import image_tools
from mcomix.preferences import prefs


_IMAGE_MODES = (
    # Can be
    # saved    GDK     PIL
    # to PNG?  mode    mode
    ( True  , 'RGB'  , '1'     ), # (1-bit pixels, black and white, stored with one pixel per byte)
    ( True  , 'RGB'  , 'L'     ), # (8-bit pixels, black and white)
    ( True  , 'RGBA' , 'LA'    ), # (8-bit pixels, black and white with alpha)
    ( True  , 'RGBA' , 'P'     ), # (8-bit pixels, mapped to any other mode using a color palette)
    ( True  , 'RGB'  , 'RGB'   ), # (3x8-bit pixels, true color)
    ( True  , 'RGBA' , 'RGBA'  ), # (4x8-bit pixels, true color with transparency mask)
    ( False , 'RGB'  , 'RGBX'  ), # (4x8-bit pixels, true color with padding)
    ( False , 'RGB'  , 'CMYK'  ), # (4x8-bit pixels, color separation)
    ( False , 'RGB'  , 'YCbCr' ), # (3x8-bit pixels, color video format)
    ( False , 'RGB'  , 'HSV'   ), # (3x8-bit pixels, Hue, Saturation, Value color space)
    ( False , 'RGB'  , 'I'     ), # (32-bit signed integer pixels)
    ( False , 'RGB'  , 'F'     ), # (32-bit floating point pixels)
)

_PIL_MODE_TO_GDK_MODE = dict([(pil_mode, gdk_mode)
                              for _, gdk_mode, pil_mode
                              in _IMAGE_MODES])

_TestImage = namedtuple('TestImage', 'name format size mode has_alpha rotation')

_TEST_IMAGES = (
    _TestImage('01-JPG-Indexed.jpg'             , 'JPEG', (  1,   1), 'L'   , False, 0  ),
    _TestImage('02-JPG-RGB.jpg'                 , 'JPEG', (  1,   1), 'RGB' , False, 0  ),
    _TestImage('03-PNG-RGB.png'                 , 'PNG' , (  1,   1), 'RGB' , False, 0  ),
    _TestImage('04-PNG-Indexed.png'             , 'PNG' , (  1,   1), 'P'   , False, 0  ),
    _TestImage('05-PNG-RGBA.png'                , 'PNG' , (  1,   1), 'RGBA', True , 0  ),
    _TestImage('animated.gif'                   , 'GIF' , (210, 210), 'RGBA', True , 0  ),
    _TestImage('blue.png'                       , 'PNG' , (100, 100), 'RGB' , False, 0  ),
    _TestImage('checkerboard.png'               , 'PNG' , (128, 128), 'RGBA', True , 0  ),
    _TestImage('landscape-exif-270-rotation.jpg', 'JPEG', (210, 297), 'L'   , False, 270),
    _TestImage('landscape-exif-270-rotation.png', 'PNG' , (210, 297), 'LA'  , True , 270),
    _TestImage('landscape-no-exif.jpg'          , 'JPEG', (297, 210), 'L'   , False, 0  ),
    _TestImage('landscape-no-exif.png'          , 'PNG' , (297, 210), 'LA'  , True , 0  ),
    _TestImage('pattern.jpg'                    , 'JPEG', (200, 100), 'RGB' , False, 0  ),
    _TestImage('pattern-opaque-rgba.png'        , 'PNG' , (200, 100), 'RGBA', True , 0  ),
    _TestImage('pattern-opaque-rgb.png'         , 'PNG' , (200, 100), 'RGB' , False, 0  ),
    _TestImage('pattern-transparent-rgba.png'   , 'PNG' , (200, 100), 'RGBA', True , 0  ),
    _TestImage('portrait-exif-180-rotation.jpg' , 'JPEG', (210, 297), 'L'   , False, 180),
    _TestImage('portrait-exif-180-rotation.png' , 'PNG' , (210, 297), 'LA'  , True , 180),
    _TestImage('portrait-no-exif.jpg'           , 'JPEG', (210, 297), 'L'   , False, 0  ),
    _TestImage('portrait-no-exif.png'           , 'PNG' , (210, 297), 'LA'  , True , 0  ),
    _TestImage('red.png'                        , 'PNG' , (100, 100), 'RGB' , False, 0  ),
    _TestImage('transparent.png'                , 'PNG' , (200, 150), 'RGBA', True , 0  ),
    _TestImage('transparent-indexed.png'        , 'PNG' , (200, 150), 'P'   , True , 0  ),
)

_TEST_IMAGE_BY_NAME = dict([(im.name, im) for im in _TEST_IMAGES])


def pil_mode_to_gdk_mode(mode):
    return _PIL_MODE_TO_GDK_MODE[mode]

def get_test_image(name):
    return _TEST_IMAGE_BY_NAME[name]

def get_image_path(basename):
    return os.path.join(os.path.dirname(__file__), 'files', 'images', basename)

def new_pixbuf(size, with_alpha, fill_colour):
    pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,
                            with_alpha, 8, size[0], size[1])
    pixbuf.fill(fill_colour)
    return pixbuf

# Example output:
#
#              ____ data in hexadecimal format, '*' indicate repeated content
#             v
#
# 0001800: ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff ffffffff
# 0000080: *
# 0001880: cbcbcbff 232323ff ffffffff ffffffff 717171ff 0e0e0eff 666666ff ffffffff
#
#    ^____ data address, or size of repeated content
#
def xhexdump(data, group_size=4):
    addr, size = 0, 0
    io = StringIO(data)
    chunk_size = group_size * 8
    prev_addr, prev_hex = (0, '')
    format_line = lambda addr, hex: '%07x: %s' % (addr, hex)
    while True:
        chunk = io.read(chunk_size)
        if not chunk:
            if addr > (prev_addr + chunk_size):
                yield format_line(addr - prev_addr, '*')
            break
        size += len(chunk)
        chunk = binascii.hexlify(chunk)
        hex = []
        for s in range(0, chunk_size * 2, group_size * 2):
            hex.append(chunk[s:s+(group_size*2)])
        hex = ' '.join(hex)
        if hex != prev_hex:
            if addr > (prev_addr + chunk_size):
                yield format_line(addr - prev_addr, '*')
            yield format_line(addr, hex)
            prev_addr, prev_hex = addr, hex
        addr += chunk_size
    if size != prev_addr:
        yield '%07x' % size

def hexdump(data, group_size=4):
    return [line for line in xhexdump(data, group_size=group_size)]

def composite_image(im1, im2):
    if isinstance(im1, gtk.gdk.Pixbuf):
        im1 = image_tools.pixbuf_to_pil(im1)
    if isinstance(im2, gtk.gdk.Pixbuf):
        im2 = image_tools.pixbuf_to_pil(im2)
    im = Image.new('RGBA',
                   (im1.size[0] + im2.size[0],
                    max(im1.size[1], im2.size[1])))
    im.paste(im1, (0, 0, im1.size[0], im1.size[1]))
    im.paste(im2, (im1.size[0], 0, im1.size[0]+im2.size[0], im2.size[1]))
    return im


class ImageToolsTest(object):

    set_use_pil = False
    use_pil = False

    def setUp(self):
        if self.set_use_pil:
            self.orig_use_pil = image_tools.USE_PIL
            image_tools.USE_PIL = self.use_pil
        super(ImageToolsTest, self).setUp()

    def tearDown(self):
        if self.set_use_pil:
            image_tools.USE_PIL = self.orig_use_pil
        super(ImageToolsTest, self).tearDown()

    def assertImagesEqual(self, im1, im2, msg=None, max_diff=20):
        def fail(diff_type, diff_fmt, *args):
            if msg is None:
                fmt = 'Images are not equal, result %(diff_type)s differs: %(diff)s'
            else:
                fmt = msg
            self.fail(fmt % {
                'diff_type': diff_type,
                'diff': diff_fmt % args,
            })
        def info(im):
            if isinstance(im, gtk.gdk.Pixbuf):
                width, stride = im.get_width(), im.get_rowstride()
                line_size = width * im.get_n_channels()
                if stride == line_size:
                    pixels = im.get_pixels()
                else:
                    assert stride > line_size
                    io = StringIO(im.get_pixels())
                    pixels = ''
                    while True:
                        line = io.read(line_size)
                        if not line:
                            break
                        pixels += line
                        leftover = io.read(stride - line_size)
                        assert len(leftover) == (stride - line_size)
                mode = 'RGBA' if im.get_has_alpha() else 'RGB'
                return mode, (im.get_width(), im.get_height()), pixels
            if isinstance(im, Image.Image):
                return im.mode, im.size, im.tostring()
            raise ValueError('unsupported class %s' % type(im))
        mode1, size1, pixels1 = info(im1)
        mode2, size2, pixels2 = info(im2)
        if mode1 != mode2:
            fail('mode', '%s instead of %s', mode1, mode2)
        if size1 != size2:
            fail('size', '%s instead of %s', size1, size2)
        assert mode1 in ('RGB', 'RGBA')
        group_size = 3 if 'RGB' == mode1 else 4
        hex1 = hexdump(pixels1, group_size=group_size)
        hex2 = hexdump(pixels2, group_size=group_size)
        diff = unified_diff(hex1, hex2, fromfile='result', tofile='expected', lineterm='')
        diff_lines = []
        for line in diff:
            if len(diff_lines) > max_diff:
                diff_lines.append('[...] diff truncated, change max_diff to increase limit.')
                break
            diff_lines.append(line)
        if len(diff_lines) > 0:
            composite_image(im1, im2).show()
            fail('content', '\n%s\n', '\n'.join(diff_lines))

    def test_load_pixbuf_basic(self):
        for image in _TEST_IMAGES:
            image_path = get_image_path(image.name)
            if self.use_pil:
                # When using PIL, indexed formats will be
                # converted to RGBA by pixbuf_to_pil.
                expected_mode = pil_mode_to_gdk_mode(image.mode)
            else:
                expected_mode = 'RGBA' if image.has_alpha else 'RGB'
            im = Image.open(image_path).convert(expected_mode)
            pixbuf = image_tools.load_pixbuf(image_path)
            msg = (
                'load_pixbuf("%s") failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % (image.name,)
            )
            self.assertImagesEqual(pixbuf, im, msg=msg)

    def test_load_pixbuf_modes(self):
        tmp_file = tempfile.NamedTemporaryFile(prefix=u'image.',
                                               suffix=u'.png', delete=False)
        tmp_file.close()
        base_im = Image.open(get_image_path('transparent.png'))
        for supported, expected_pixbuf_mode, mode in _IMAGE_MODES:
            if not supported:
                continue
            input_im = base_im.convert(mode)
            input_im.save(tmp_file.name)
            pixbuf = image_tools.load_pixbuf(tmp_file.name)
            expected_im = input_im.convert(expected_pixbuf_mode)
            msg = (
                'load_pixbuf("%s") failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % (mode,)
            )
            self.assertImagesEqual(pixbuf, expected_im, msg=msg)

    def test_load_pixbuf_invalid(self):
        if self.use_pil:
            exception = IOError
        else:
            exception = gobject.GError
        self.assertRaises(exception, image_tools.load_pixbuf, os.devnull)

    def test_load_pixbuf_size_basic(self):
        # Same as test_load_pixbuf_basic:
        # load bunch of images at their
        # normal resolution.
        prefs['checkered bg for transparent images'] = False
        for image in _TEST_IMAGES:
            if image.name in (
                'transparent.png',
                'transparent-indexed.png',
            ):
                # Avoid complex transparent image, since PIL
                # and GdkPixbuf may yield different results.
                continue
            image_path = get_image_path(image.name)
            if self.use_pil:
                # When using PIL, indexed formats will be
                # converted to RGBA by pixbuf_to_pil.
                expected_mode = pil_mode_to_gdk_mode(image.mode)
            else:
                expected_mode = 'RGBA' if image.has_alpha else 'RGB'
            expected = Image.open(image_path).convert(expected_mode)
            if image.has_alpha:
                background = Image.new('RGBA', image.size, color='white')
                expected = Image.alpha_composite(background, expected)
            result = image_tools.load_pixbuf_size(image_path,
                                                  image.size[0],
                                                  image.size[1])
            msg = (
                'load_pixbuf("%s") failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % (image.name,)
            )
            self.assertImagesEqual(result, expected, msg=msg)

    def test_load_pixbuf_size_dimensions(self):
        # Use both:
        # - a format with support for resizing at the decoding stage: JPEG
        # - a format that does not support resizing at the decoding stage: PNG
        for name in (
            'pattern.jpg',
            'pattern-opaque-rgba.png',
        ):
            image = get_test_image(name)
            image_path = get_image_path(image.name)
            # Check image is unchanged if smaller than target dimensions.
            target_size = 2 * image.size[0], 2 * image.size[1]
            expected = Image.open(image_path).convert(image.mode)
            result = image_tools.load_pixbuf_size(image_path, *target_size)
            msg = (
                'load_pixbuf_size("%s", %dx%d) failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % ((name,) + target_size)
            )
            self.assertImagesEqual(result, expected, msg=msg)
            # Check image is scaled down if bigger than target dimensions,
            # and that aspect ratio is kept.
            target_size = image.size[0], image.size[1] / 2
            result = image_tools.load_pixbuf_size(image_path,
                                                  *target_size)
            msg = (
                'load_pixbuf_size("%s", %dx%d) failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % ((name,) + target_size)
            )
            self.assertEqual((result.get_width(), result.get_height()),
                             (image.size[0] / 2, image.size[1] / 2))

    def test_load_pixbuf_size_invalid(self):
        if self.use_pil:
            exception = IOError
        else:
            exception = gobject.GError
        self.assertRaises(exception, image_tools.load_pixbuf_size, os.devnull, 50, 50)

    def test_pixbuf_to_pil(self):
        for image in (
            'transparent.png',
            'transparent-indexed.png',
            'pattern-opaque-rgb.png',
            'pattern-opaque-rgba.png',
            'pattern-transparent-rgba.png',
        ):
            pixbuf = image_tools.load_pixbuf(get_image_path(image))
            im = image_tools.pixbuf_to_pil(pixbuf)
            msg = (
                'pixbuf_to_pil("%s") failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % (image,)
            )
            self.assertImagesEqual(im, pixbuf, msg=msg)

    def test_pil_to_pixbuf(self):
        base_im = Image.open(get_image_path('transparent.png'))
        for _, expected_pixbuf_mode, mode in _IMAGE_MODES:
            input_im = base_im.convert(mode)
            pixbuf = image_tools.pil_to_pixbuf(input_im)
            expected_im = input_im.convert(expected_pixbuf_mode)
            msg = (
                'pil_to_pixbuf("%s") failed; '
                'result %%(diff_type)s differs: %%(diff)s'
                % (mode,)
            )
            self.assertImagesEqual(pixbuf, expected_im, msg=msg)
        # TODO: test keep_orientation

    def test_get_image_info(self):
        for image in _TEST_IMAGES:
            image_path = get_image_path(image.name)
            expected = (image.format,) + image.size
            result = image_tools.get_image_info(image_path)
            msg = (
                'get_image_info("%s") failed; '
                'result differs: %s:%dx%d instead of %s:%dx%d'
                % ((image.name,) + result + expected)
            )
            self.assertEqual(result, expected, msg=msg)

    def test_get_image_info_invalid(self):
        expected = (u'Unknown filetype', 0, 0)
        result = image_tools.get_image_info(os.devnull)
        msg = (
            'get_image_info() on invalid image failed; '
            'result differs: %s:%dx%d instead of %s:%dx%d'
            % (result + expected)
        )
        self.assertEqual(result, expected, msg=msg)

    def test_get_implied_rotation(self):
        for name in (
            # JPEG.
            'landscape-exif-270-rotation.jpg',
            'landscape-no-exif.jpg',
            'portrait-exif-180-rotation.jpg',
            'portrait-no-exif.jpg',
            # PNG.
            'landscape-exif-270-rotation.png',
            'landscape-no-exif.png',
            'portrait-exif-180-rotation.png',
            'portrait-no-exif.png',
        ):
            image = get_test_image(name)
            pixbuf = image_tools.load_pixbuf(get_image_path(name))
            rotation = image_tools.get_implied_rotation(pixbuf)
            self.assertEqual(rotation, image.rotation,
                             msg='get_implied_rotation(%s) failed: %u instead of %u'
                             % (image, rotation, image.rotation))

    def test_fit_in_rectangle_dimensions(self):
        # Test dimensions handling.
        for input_size, target_size, scale_up, keep_ratio, expected_size in (
            # Exactly the same size.
            ((200, 100), (200, 100), False, False, (200, 100)),
            ((200, 100), (200, 100), False,  True, (200, 100)),
            ((200, 100), (200, 100),  True, False, (200, 100)),
            ((200, 100), (200, 100),  True,  True, (200, 100)),
            # Smaller.
            ((200, 100), (400, 400), False, False, (200, 100)),
            ((200, 100), (400, 400), False,  True, (200, 100)),
            ((200, 100), (400, 400),  True, False, (400, 400)),
            ((200, 100), (400, 400),  True,  True, (400, 200)),
            # Bigger.
            ((800, 600), (200, 200), False, False, (200, 200)),
            ((800, 600), (200, 200), False,  True, (200, 150)),
            ((800, 600), (200, 200),  True, False, (200, 200)),
            ((800, 600), (200, 200),  True,  True, (200, 150)),
            # One dimension bigger, the other smaller.
            ((200, 400), (200, 200), False, False, (200, 200)),
            ((200, 400), (200, 200), False,  True, (100, 200)),
            ((200, 400), (200, 200),  True, False, (200, 200)),
            ((200, 400), (200, 200),  True,  True, (100, 200)),
        ):
            for invert_dimensions in (False, True):
                if invert_dimensions:
                    input_size = input_size[1], input_size[0]
                    target_size = target_size[1], target_size[0]
                    expected_size = expected_size[1], expected_size[0]
                pixbuf = new_pixbuf(input_size, False, 0)
                result = image_tools.fit_in_rectangle(pixbuf,
                                                      target_size[0],
                                                      target_size[1],
                                                      scale_up=scale_up,
                                                      keep_ratio=keep_ratio)
                result_size = result.get_width(), result.get_height()
                msg = (
                    'fit_in_rectangle(%dx%d => %dx%d, scale up=%s, keep ratio=%s) failed; '
                    'result size differs: %dx%d instead of %dx%d' % (
                        input_size + target_size +
                        (scale_up, keep_ratio) +
                        result_size + expected_size
                    )
                )
                self.assertEqual(result_size, expected_size, msg=msg)

    def test_fit_in_rectangle_rotation(self):
        image_size = 128
        rect_size = 32
        # Start with a black image.
        im = Image.new('RGB', (image_size, image_size), color='black')
        draw = ImageDraw.Draw(im)
        # Paint top-left corner white.
        draw.rectangle((0, 0, rect_size, rect_size), fill='white')
        # Corner colors, starting top-left, rotating clock-wise.
        corners_colors = ('white', 'black', 'black', 'black')
        pixbuf = image_tools.pil_to_pixbuf(im)
        for rotation in (
            0, 90, 180, 270,
            -90, -180, -270,
            90 * 5, -90 * 7
        ):
            for target_size in (
                (image_size, image_size),
                (image_size / 2, image_size / 2),
            ):
                result = image_tools.fit_in_rectangle(pixbuf,
                                                      target_size[0],
                                                      target_size[1],
                                                      rotation=rotation)
                # First check size.
                input_size = (image_size, image_size)
                result_size = result.get_width(), result.get_height()
                msg = (
                    'fit_in_rectangle(%dx%d => %dx%d, rotation=%d) failed; '
                    'result size: %dx%d' % (
                        input_size + target_size + (rotation,) + result_size
                    )
                )
                self.assertEqual(result_size, target_size, msg=msg)
                # And then check corners.
                expected_corners_colors = list(corners_colors)
                for _ in range(1, 1 + (rotation % 360) / 90):
                    expected_corners_colors.insert(0, expected_corners_colors.pop(-1))
                result_corners_colors = []
                corner = new_pixbuf((1, 1), False, 0x888888)
                corners_positions = [0, 0, target_size[0] - 1, target_size[0] - 1]
                for _ in range(4):
                    x, y = corners_positions[0:2]
                    result.copy_area(x, y, 1, 1, corner, 0, 0)
                    color = corner.get_pixels()[0:3]
                    color = binascii.hexlify(color)
                    if 'ffffff' == color:
                        color = 'white'
                    elif '000000' == color:
                        color = 'black'
                    result_corners_colors.append(color)
                    corners_positions.insert(0, corners_positions.pop(-1))
                # Swap bottom corners for spatial display.
                result_corners_colors.append(result_corners_colors.pop(-2))
                expected_corners_colors.append(expected_corners_colors.pop(-2))
                msg = (
                    'fit_in_rectangle(%dx%d => %dx%d, rotation=%d) failed; '
                    'result corners differs:\n'
                    '%s\t%s\n'
                    '%s\t%s\n'
                    'instead of:\n'
                    '%s\t%s\n'
                    '%s\t%s\n' % (
                        input_size + target_size + (rotation, ) +
                        tuple(result_corners_colors) +
                        tuple(expected_corners_colors)
                    )
                )
                self.assertEqual(result_corners_colors,
                                 expected_corners_colors,
                                 msg=msg)

    def test_fit_in_rectangle_opaque_no_resize(self):
        # Check opaque image is unchanged when not resizing.
        for image in (
            'pattern-opaque-rgb.png',
            'pattern-opaque-rgba.png',
        ):
            input = image_tools.load_pixbuf(get_image_path(image))
            width, height = input.get_width(), input.get_height()
            for scaling_quality in range(4):
                prefs['scaling quality'] = scaling_quality
                result = image_tools.fit_in_rectangle(input, width, height,
                                                      scaling_quality=scaling_quality)
                msg = (
                    'fit_in_rectangle("%s", scaling quality=%d) failed; '
                    'result %%(diff_type)s differs: %%(diff)s'
                    % (image, scaling_quality)
                )
                self.assertImagesEqual(result, input, msg=msg)

    def test_fit_in_rectangle_transparent_no_resize(self):
        # And with a transparent test image, check alpha blending.
        image = 'pattern-transparent-rgba.png'
        control = Image.open(get_image_path(image))
        # Create checkerboard background.
        checker_bg = Image.new('RGBA', control.size)
        checker = Image.open(get_image_path('checkerboard.png'))
        for x in range(0, control.size[0], checker.size[0]):
            for y in range(0, control.size[1], checker.size[1]):
                checker_bg.paste(checker, (x, y))
        # Create whhite background.
        white_bg = Image.new('RGBA', control.size, color='white')
        assert control.size == white_bg.size
        width, height = control.size
        for use_checker_bg in (False, True):
            prefs['checkered bg for transparent images'] = use_checker_bg
            expected = Image.alpha_composite(
                checker_bg if use_checker_bg else white_bg,
                control
            )
            for scaling_quality in range(4):
                prefs['scaling quality'] = scaling_quality
                result = image_tools.fit_in_rectangle(image_tools.pil_to_pixbuf(control),
                                                      width, height,
                                                      scaling_quality=scaling_quality)
                msg = (
                    'fit_in_rectangle("%s", scaling quality=%d, background=%s) failed; '
                    'result %%(diff_type)s differs: %%(diff)s'
                    % (image, scaling_quality, 'checker' if checker_bg else 'white')
                )
                self.assertImagesEqual(result, expected, msg=msg)


class_list = []

if hasattr(image_tools, 'USE_PIL'):
    class_list.extend((
        ('GDK', {'set_use_pil': True, 'use_pil': False}),
        ('PIL', {'set_use_pil': True, 'use_pil': True }),
    ))
else:
    if 'win32' == sys.platform:
        variant = 'GDK'
        use_pil = False
    else:
        variant = 'PIL'
        use_pil = True
    class_list.append((variant, {'use_pil': use_pil}))

for class_variant, class_dict in class_list:
    class_name = 'ImageTools%sTest' % class_variant
    globals()[class_name] = type(class_name, (ImageToolsTest, MComixTest), class_dict)


"""histogram.py - Draw histograms (RGB) from pixbufs."""

import PIL.Image as Image
import PIL.ImageDraw as ImageDraw
import PIL.ImageOps as ImageOps

from mcomix import image_tools

def draw_histogram(pixbuf, height=170, fill=170, text=True):
    """Draw a histogram from <pixbuf> and return it as another pixbuf.

    The returned prixbuf will be 262x<height> px.

    The value of <fill> determines the colour intensity of the filled graphs,
    valid values are between 0 and 255.

    If <text> is True a label with the maximum pixel value will be added to
    one corner.
    """
    im = Image.new('RGB', (258, height - 4), (30, 30, 30))
    hist_data = image_tools.pixbuf_to_pil(pixbuf).histogram()
    maximum = max(hist_data[:768] + [1])
    y_scale = float(height - 6) / maximum
    r = [int(hist_data[n] * y_scale) for n in range(256)]
    g = [int(hist_data[n] * y_scale) for n in range(256, 512)]
    b = [int(hist_data[n] * y_scale) for n in range(512, 768)]
    im_data = im.getdata()
    # Draw the filling colours
    for x in range(256):
        for y in range(1, max(r[x], g[x], b[x]) + 1):
            r_px = y <= r[x] and fill or 0
            g_px = y <= g[x] and fill or 0
            b_px = y <= b[x] and fill or 0
            im_data.putpixel((x + 1, height - 5 - y), (r_px, g_px, b_px))
    # Draw the outlines
    for x in range(1, 256):
        for y in list(range(r[x-1] + 1, r[x] + 1)) + [r[x]] * (r[x] != 0):
            r_px, g_px, b_px = im_data.getpixel((x + 1, height - 5 - y))
            im_data.putpixel((x + 1, height - 5 - y), (255, g_px, b_px))
        for y in range(r[x] + 1, r[x-1] + 1):
            r_px, g_px, b_px = im_data.getpixel((x, height - 5 - y))
            im_data.putpixel((x, height - 5 - y), (255, g_px, b_px))
        for y in list(range(g[x-1] + 1, g[x] + 1)) + [g[x]] * (g[x] != 0):
            r_px, g_px, b_px = im_data.getpixel((x + 1, height - 5 - y))
            im_data.putpixel((x + 1, height - 5 - y), (r_px, 255, b_px))
        for y in range(g[x] + 1, g[x-1] + 1):
            r_px, g_px, b_px = im_data.getpixel((x, height - 5 - y))
            im_data.putpixel((x, height - 5 - y), (r_px, 255, b_px))
        for y in list(range(b[x-1] + 1, b[x] + 1)) + [b[x]] * (b[x] != 0):
            r_px, g_px, b_px = im_data.getpixel((x + 1, height - 5 - y))
            im_data.putpixel((x + 1, height - 5 - y), (r_px, g_px, 255))
        for y in list(range(b[x] + 1, b[x-1] + 1)):
            r_px, g_px, b_px = im_data.getpixel((x, height - 5 - y))
            im_data.putpixel((x, height - 5 - y), (r_px, g_px, 255))
    if text:
        maxstr = 'max: ' + str(maximum)
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, len(maxstr) * 6 + 2, 10), fill=(30, 30, 30))
        draw.text((2, 0), maxstr, fill=(255, 255, 255))
    im = ImageOps.expand(im, 1, (80, 80, 80))
    im = ImageOps.expand(im, 1, (0, 0, 0))
    return image_tools.pil_to_pixbuf(im)


# vim: expandtab:sw=4:ts=4

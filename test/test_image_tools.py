# coding: utf-8

import unittest
import os

from mcomix import image_tools


class ImageToolsTest(unittest.TestCase):

    def test_implied_rotation(self):
        for image, rotation in (
            ('landscape-exif-270-rotation.jpg', 270),
            ('landscape-no-exif.jpg'          , 0  ),
            ('portrait-exif-180-rotation.jpg' , 180),
            ('portrait-no-exif.jpg'           , 0  ),
        ):
            pixbuf = image_tools.load_pixbuf(os.path.join('test', 'files', 'images', image))
            self.assertEqual(rotation, image_tools.get_implied_rotation(pixbuf))


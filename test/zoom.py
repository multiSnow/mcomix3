# -*- coding: utf-8 -*-

import unittest
from mcomix.zoom import ZoomModel, FitMode, NoFitMode, BestFitMode, FitToWidthMode
from mcomix import constants

class ZoomModelTest(unittest.TestCase):
    def setUp(self):
        self.zoom = ZoomModel()

    def test_bestfit_zoom(self):
        self.zoom.set_fit_mode(FitMode.create(constants.ZOOM_MODE_BEST))
        img_size = (1000, 2000)
        scr_size = (1000, 500)
        size = self.zoom.get_zoomed_size(img_size, scr_size)

        self.assertEqual(size, (250, 500))
        self.assertAlmostEqual(self.zoom.get_zoom(), 0.25)

class NoFitTest(unittest.TestCase):
    def setUp(self):
        self.fitmode = NoFitMode()
        self.fitmode.set_scale_up(False)

    def test_smaller_than_screen_scale(self):
        img_size = (400, 200)
        scr_size = (800, 600)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            img_size,
            "No upsizing should take place")

    def test_larger_than_screen_scale(self):
        img_size = (1000, 2000)
        scr_size = (800, 600)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            img_size,
            "No downsizing should take place")

    def test_smaller_than_screen_with_upscale(self):
        self.fitmode.set_scale_up(True)
        img_size = (100, 50)
        scr_size = (400, 400)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (400, 200),
            "Image should fit to width")

        img_size = (50, 100)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (200, 400),
            "Image should fit to height")

class BestFitTest(unittest.TestCase):
    def setUp(self):
        self.fitmode = BestFitMode()
        self.fitmode.set_scale_up(False)

    def test_wider_than_screen(self):
        img_size = (1000, 2000)
        scr_size = (500, 500)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (250, 500),
            "Image should fit to both width and height")

    def test_higher_than_screen(self):
        img_size = (2000, 1000)
        scr_size = (500, 500)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (500, 250),
            "Image should fit to both width and height")

    def test_smaller_than_screen(self):
        img_size = (500, 500)
        scr_size = (1000, 1000)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (500, 500),
            "No scaling should take place")

    def test_overflow_on_one_side(self):
        img_size = (250, 1000)
        scr_size = (500, 500)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (125, 500),
            "Image should fit to both width and height")

    def test_scale_up_smaller_than_screen(self):
        img_size = (250, 500)
        scr_size = (2000, 1000)

        self.fitmode.set_scale_up(True)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (500, 1000),
            "Image should fit to both width and height")

class FitToWidthTest(unittest.TestCase):
    def setUp(self):
        self.fitmode = FitToWidthMode()
        self.fitmode.set_scale_up(False)

    def test_identical_to_screen(self):
        img_size = (500, 1000)
        scr_size = (500, 250)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (500, 1000),
            "Image should fit to width")

    def test_smaller_than_screen(self):
        img_size = (500, 1000)
        scr_size = (1000, 500)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (500, 1000),
            "Image should fit to width")

    def test_larger_than_screen(self):
        img_size = (1000, 1000)
        scr_size = (500, 500)

        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (500, 500),
            "Image should fit to width")

    def test_scale_smaller_than_screen(self):
        img_size = (500, 1000)
        scr_size = (1000, 1000)

        self.fitmode.set_scale_up(True)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (1000, 2000))#,
            #"Image should fit to width")

    def test_scale_larger_than_screen(self):
        img_size = (500, 1000)
        scr_size = (250, 1000)

        self.fitmode.set_scale_up(True)
        self.assertEqual(
            self.fitmode.get_scaled_size(img_size, scr_size),
            (250, 500),
            "Image should fit to width")



# vim: expandtab:sw=4:ts=4

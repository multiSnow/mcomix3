"""enhance_backend.py - Image enhancement handler and dialog (e.g. contrast,
brightness etc.)
"""

import image_tools

class ImageEnhancer:

    """The ImageEnhancer keeps track of the "enhancement" values and performs
    these enhancements on pixbufs. Changes to the ImageEnhancer's values
    can be made using an _EnhanceImageDialog.
    """

    def __init__(self, window):
        self._window = window
        self.brightness = 1.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0
        self.autocontrast = False

    def enhance(self, pixbuf):
        """Return an "enhanced" version of <pixbuf>."""

        if (self.brightness != 1.0 or self.contrast != 1.0 or
          self.saturation != 1.0 or self.sharpness != 1.0 or
          self.autocontrast):

            return image_tools.enhance(pixbuf, self.brightness, self.contrast,
                self.saturation, self.sharpness, self.autocontrast)

        return pixbuf

    def signal_update(self):
        """Signal to the main window that a change in the enhancement
        values has been made.
        """
        self._window.draw_image()

# vim: expandtab:sw=4:ts=4

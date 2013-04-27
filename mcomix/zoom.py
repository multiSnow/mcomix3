""" Handles zoom and fit of images in the main display area. """

from mcomix import constants
from mcomix import callback
from mcomix.preferences import prefs

MIN_ZOOM = 0.05
MAX_ZOOM = 6.0

class ZoomModel(object):
    """ Handles zoom and fit modes. """

    def __init__(self):
        #: Base zoom level. 100% (1.0) indicates that no scaling takes place.
        self._base_zoom = 1.0
        #: User zoom level. This value is added/substracted to/from L{_base_zoom}.
        self._user_zoom = 0.0
        #: Image fit mode. Determines the base zoom level for an image by
        #: calculating its maximum size.
        self._fitmode = NoFitMode()

    def get_fit_mode(self):
        return self._fitmode

    def set_fit_mode(self, fitmode):
        self._fitmode = fitmode
        self.reset_zoom()

    def get_zoom(self):
        return self._base_zoom + self._user_zoom

    def set_zoom(self, zoom):
        new_zoom = min(max(self._base_zoom + zoom, MIN_ZOOM), MAX_ZOOM)
        if new_zoom == self.get_zoom():
            return False

        self._user_zoom = new_zoom - self._base_zoom
        self.zoom_changed(self.get_zoom())
        return True

    def zoom_in(self):
        return self.set_zoom(self._user_zoom + self._get_zoom_advancement())

    def zoom_out(self):
        return self.set_zoom(self._user_zoom - self._get_zoom_advancement())

    def reset_zoom(self):
        self.set_zoom(0.0)
        self.zoom_changed(self.get_zoom())

    def _get_zoom_advancement(self):
        if self.get_zoom() > 2.0:
            return 0.5
        elif self.get_zoom() > 1.0:
            return 0.1
        else:
            return 0.05

    @callback.Callback
    def zoom_changed(self, zoomlevel):
        pass

    def _recalculate_zoom(self, image_size, screen_size):
        if self._fitmode:
            scaled_size = self._fitmode.get_scaled_size(image_size, screen_size)
            # Using width/height shouldn't matter as images are always scaled proportionally
            self._base_zoom = _calc_scale(image_size[0], scaled_size[0])

        # Prevent overflow from negative zoom factors
        if self.get_zoom() <= 0.001:
            self._user_zoom = MIN_ZOOM - self._base_zoom

        return self._base_zoom

    def get_zoomed_size(self, image_size, screen_size):
        self._recalculate_zoom(image_size, screen_size)
        return _scale_int(image_size, self.get_zoom())


class FitMode(object):
    """ Base class that handles scaling of images to predefined sizes. """

    ID = -1

    def __init__(self):
        #: No upscaling is done unless this is True
        self.scale_up = False

    def get_scale_up(self):
        return self.scale_up

    def set_scale_up(self, scale_up):
        self.scale_up = scale_up

    def get_scaled_size(self, img_size, screen_size):
        """ Returns the base image size (scaled to fit into screen_size,
        depending on algorithm).

        @param img_size: Tuple of (width, height), original image size
        @param screen_size: Tuple of (width, height), available screen size
        @return: Tuple of (width, height), scaled image size
        """
        raise NotImplementedError()

    @classmethod
    def get_mode_identifier(cls):
        """ Returns an unique identifier for a fit mode (for serialization) """
        return cls.ID

    @staticmethod
    def create(fitmode):
        for cls in (NoFitMode, BestFitMode, FitToWidthMode, FitToHeightMode,
                    FitToSizeMode):
            if cls.get_mode_identifier() == fitmode:
                return cls()

        raise ValueError("No fit mode registered for identifier '%d'." % fitmode)


class NoFitMode(FitMode):
    """ No automatic scaling depending on image size (unless L{scale_up} is
    True, in which case the image will be fit to screen size). """

    ID = constants.ZOOM_MODE_MANUAL

    def get_scaled_size(self, img_size, screen_size):
        if (self.get_scale_up() and
                img_size[0] < screen_size[0] and
                img_size[1] < screen_size[1]):

            scale_x = _calc_scale(img_size[0], screen_size[0])
            scale_y = _calc_scale(img_size[1], screen_size[1])
            scale = min(scale_x, scale_y)
            return _scale_int(img_size, scale)
        else:
            return int(img_size[0]), int(img_size[1])


class BestFitMode(FitMode):
    """ Scales to fit both width and height into the screen frame. """

    ID = constants.ZOOM_MODE_BEST

    def get_scaled_size(self, img_size, screen_size):
        scale = min(self.get_scale_x(img_size[0], screen_size[0]),
                self.get_scale_y(img_size[1], screen_size[1]))
        return _scale_int(img_size, scale)

    def get_scale_x(self, img_width, screen_width):
        scale_x = _calc_scale(img_width, screen_width)

        if scale_x > 1.0 and not self.get_scale_up():
            return 1.0
        else:
            return scale_x

    def get_scale_y(self, img_height, screen_height):
        scale_y = _calc_scale(img_height, screen_height)

        if scale_y > 1.0 and not self.get_scale_up():
            return 1.0
        else:
            return scale_y


class FitToWidthMode(BestFitMode):
    """ Scales images to fit into screen width. """

    ID = constants.ZOOM_MODE_WIDTH

    def get_scaled_size(self, img_size, screen_size):
        scale = self.get_scale_x(img_size[0], screen_size[0])
        return _scale_int(img_size, scale)


class FitToHeightMode(BestFitMode):
    """ Scales images to fit into screen height. """

    ID = constants.ZOOM_MODE_HEIGHT

    def get_scaled_size(self, img_size, screen_size):
        scale = self.get_scale_y(img_size[1], screen_size[1])
        return _scale_int(img_size, scale)


class FitToSizeMode(FitMode):
    """ Scales to a fix size (either height or width). This mode
    ignores "Strech small images", as it is the default behaviour. """

    ID = constants.ZOOM_MODE_SIZE

    def __init__(self):
        super(FitToSizeMode, self).__init__()
        self.size = int(prefs['fit to size px'])
        self.mode = prefs['fit to size mode']

    def get_scaled_size(self, img_size, screen_size):
        if self.mode == constants.ZOOM_MODE_WIDTH:
            side = img_size[0]
        elif self.mode == constants.ZOOM_MODE_HEIGHT:
            side = img_size[1]
        else:
            assert False, 'Invalid fit to size mode specified in preferences'

        # If the image is smaller than the desired size,
        # only scale up if scale_up = True.
        if not self.get_scale_up() and side < self.size:
            return img_size

        scale = _calc_scale(side, self.size)
        return _scale_int(img_size, scale)


def _scale_int(x, scale):
    return int(x[0] * scale), int(x[1] * scale)

def _calc_scale(length, desired_length):
    """ Calculates the factor a number must be multiplied with to reach
    a desired size. """
    return float(desired_length) / float(length)


# vim: expandtab:sw=4:ts=4

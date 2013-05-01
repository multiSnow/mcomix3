""" Handles zoom and fit of images in the main display area. """

from mcomix import constants
from mcomix.preferences import prefs

IDENTITY_ZOOM = 1.0
ZOOM_STEP = 2 ** (1.0 / 4)
MIN_USER_ZOOM = 1.0 / 32
MAX_USER_ZOOM = 8.0

class ZoomModel(object):
    """ Handles zoom and fit modes. """

    def __init__(self):
        #: User zoom level.
        self._user_zoom = IDENTITY_ZOOM
        #: Image fit mode. Determines the base zoom level for an image by
        #: calculating its maximum size.
        self._fitmode = NoFitMode()
        self._scale_up = False

    def set_fit_mode(self, fitmode):
        self._fitmode = fitmode

    def get_scale_up(self):
        return self._scale_up

    def set_scale_up(self, scale_up):
        self._scale_up = scale_up

    def _set_user_zoom(self, zoom):
        self._user_zoom = min(max(zoom, MIN_USER_ZOOM), MAX_USER_ZOOM)

    def zoom_in(self):
        self._set_user_zoom(self._user_zoom * ZOOM_STEP)

    def zoom_out(self):
        self._set_user_zoom(self._user_zoom / ZOOM_STEP)

    def reset_user_zoom(self):
        self._set_user_zoom(IDENTITY_ZOOM)

    def get_zoomed_size(self, image_size, screen_size):
        preferred_scale = self._fitmode.get_preferred_scale(
            image_size, screen_size)
        if (preferred_scale > IDENTITY_ZOOM and
            image_size[0] < screen_size[0] and
            image_size[1] < screen_size[1] and
            not self.get_scale_up()):
            preferred_scale = IDENTITY_ZOOM

        return _scale_int(image_size, preferred_scale * self._user_zoom)


class FitMode(object):
    """ Base class that handles scaling of images to predefined sizes. """

    ID = -1

    def get_preferred_scale(self, img_size, screen_size):
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
        for cls in (NoFitMode, BestFitMode, FitToWidthMode,
            FitToHeightMode, FitToSizeMode):
            if cls.get_mode_identifier() == fitmode:
                return cls()

        raise ValueError("No fit mode registered for identifier '%d'." % fitmode)


class NoFitMode(FitMode):
    """ No automatic scaling depending on image size. """

    ID = constants.ZOOM_MODE_MANUAL

    def get_preferred_scale(self, img_size, screen_size):
        return IDENTITY_ZOOM


class BestFitMode(FitMode):
    """ Scales to fit both width and height into the screen frame. """

    ID = constants.ZOOM_MODE_BEST

    def get_preferred_scale(self, img_size, screen_size):
        return min(_calc_scale(img_size[0], screen_size[0]),
                _calc_scale(img_size[1], screen_size[1]))


class FitToWidthMode(FitMode):
    """ Scales images to fit into screen width. """

    ID = constants.ZOOM_MODE_WIDTH

    def get_preferred_scale(self, img_size, screen_size):
        return _calc_scale(img_size[0], screen_size[0])


class FitToHeightMode(FitMode):
    """ Scales images to fit into screen height. """

    ID = constants.ZOOM_MODE_HEIGHT

    def get_preferred_scale(self, img_size, screen_size):
        return _calc_scale(img_size[1], screen_size[1])


class FitToSizeMode(FitMode):
    """ Scales to a fix size (either height or width). """

    ID = constants.ZOOM_MODE_SIZE

    def __init__(self):
        super(FitToSizeMode, self).__init__()
        self.size = int(prefs['fit to size px'])
        self.mode = prefs['fit to size mode']

    def get_preferred_scale(self, img_size, screen_size):
        if self.mode == constants.ZOOM_MODE_WIDTH:
            side = img_size[0]
        elif self.mode == constants.ZOOM_MODE_HEIGHT:
            side = img_size[1]
        else:
            assert False, 'Invalid fit to size mode specified in preferences'

        return _calc_scale(side, self.size)


def _scale_int(x, scale):
    return int(x[0] * scale), int(x[1] * scale)

def _calc_scale(length, desired_length):
    """ Calculates the factor a number must be multiplied with to reach
    a desired size. """
    return float(desired_length) / float(length)


# vim: expandtab:sw=4:ts=4

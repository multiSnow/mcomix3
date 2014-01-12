""" Handles zoom and fit of images in the main display area. """

from mcomix import constants
from mcomix.preferences import prefs
import operator

IDENTITY_ZOOM = 1.0
IDENTITY_ZOOM_LOG = 0
USER_ZOOM_LOG_SCALE1 = 4.0
MIN_USER_ZOOM_LOG = -20
MAX_USER_ZOOM_LOG = 12

class ZoomModel(object):
    """ Handles zoom and fit modes. """

    def __init__(self):
        #: User zoom level.
        self._user_zoom_log = IDENTITY_ZOOM_LOG
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

    def _set_user_zoom_log(self, zoom_log):
        self._user_zoom_log = min(max(zoom_log, MIN_USER_ZOOM_LOG), MAX_USER_ZOOM_LOG)

    def zoom_in(self):
        self._set_user_zoom_log(self._user_zoom_log + 1)

    def zoom_out(self):
        self._set_user_zoom_log(self._user_zoom_log - 1)

    def reset_user_zoom(self):
        self._set_user_zoom_log(IDENTITY_ZOOM_LOG)

    def get_zoomed_size(self, image_size, screen_size):
        preferred_scale = self._fitmode.get_preferred_scale(
            image_size, screen_size)
        if (preferred_scale > IDENTITY_ZOOM and
            not self.get_scale_up() and
            any(_smaller(image_size, screen_size))):
            preferred_scale = IDENTITY_ZOOM

        return _scale_image_size(image_size,
            preferred_scale * 2 ** (self._user_zoom_log / USER_ZOOM_LOG_SCALE1))


class FitMode(object):
    """ Base class that handles scaling of images to predefined sizes. """

    ID = -1

    def get_preferred_scale(self, image_size, screen_size):
        """ Returns the base image size (scaled to fit into screen_size,
        depending on algorithm).

        @param image_size: Tuple of (width, height), original image size
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

    def get_preferred_scale(self, image_size, screen_size):
        if all(_smaller(image_size, screen_size)):
            return _calc_scale_all_axes(image_size, screen_size)
        return IDENTITY_ZOOM


class BestFitMode(FitMode):
    """ Scales to fit both width and height into the screen frame. """

    ID = constants.ZOOM_MODE_BEST

    def get_preferred_scale(self, image_size, screen_size):
        return _calc_scale_all_axes(image_size, screen_size)


class FitToWidthMode(FitMode):
    """ Scales images to fit into screen width. """

    ID = constants.ZOOM_MODE_WIDTH

    def get_preferred_scale(self, image_size, screen_size):
        return _calc_scale(image_size, screen_size, constants.WIDTH_AXIS)


class FitToHeightMode(FitMode):
    """ Scales images to fit into screen height. """

    ID = constants.ZOOM_MODE_HEIGHT

    def get_preferred_scale(self, image_size, screen_size):
        return _calc_scale(image_size, screen_size, constants.HEIGHT_AXIS)


class FitToSizeMode(FitMode):
    """ Scales to a fix size (either height or width). """

    ID = constants.ZOOM_MODE_SIZE

    def __init__(self):
        super(FitToSizeMode, self).__init__()
        self.size = int(prefs['fit to size px'])
        self.mode = prefs['fit to size mode']

    def get_preferred_scale(self, image_size, screen_size):
        if self.mode == constants.ZOOM_MODE_WIDTH:
            side = image_size[constants.WIDTH_AXIS]
        elif self.mode == constants.ZOOM_MODE_HEIGHT:
            side = image_size[constants.HEIGHT_AXIS]
        else:
            assert False, 'Invalid fit to size mode specified in preferences'

        return _calc_scale(side, self.size)


def _smaller(a, b):
    return map(operator.lt, a, b)

def _scale_image_size(size, scale):
    return _to_nonempty_tuple(_round_tuple(_scale_tuple(size, scale)))

def _calc_scale(from_size, to_size, axis=None):
    if axis is None:
        from_size = (from_size,)
        to_size = (to_size,)
        axis = 0
    return float(to_size[axis]) / float(from_size[axis])

def _calc_scale_all_axes(from_size, to_size):
    return reduce(min, map(lambda axis: _calc_scale(from_size, to_size, axis),
        range(len(from_size))))

def _scale_tuple(t, factor):
    return tuple([x * factor for x in t])

def _round_tuple(t):
    return tuple(map(lambda x: int(round(x)), t))

def _to_nonempty_tuple(t):
    return tuple(map(lambda x: x if x > 0 else 1, t))

# vim: expandtab:sw=4:ts=4

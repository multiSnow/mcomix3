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
    """ Returns a list with the i-th element set to True if and only the i-th
    element in a is less than the i-th element in b. """
    return map(operator.lt, a, b)

def _scale_image_size(size, scale):
    return _round_nonempty(_scale_tuple(size, scale))

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

def _round_nonempty(t):
    """ Conveniece method for _to_nonempty_tuple(_round_tuple(t)). """
    return _to_nonempty_tuple(_round_tuple(t))

def _volume(t):
    return reduce(operator.mul, t, 1)

def _relerr(approx, ideal):
    return abs((approx - ideal) / ideal)

def _scale_distributed(sizes, axis, max_size, allow_upscaling):
    """ Calculates scales for a list of boxes that are distributed along a given
    axis (without any gaps). If the resulting scales are applied to their
    respective boxes, their new total size along axis will be as close as
    possible to max_size. The current implementation ensures that equal box
    sizes are mapped to equal scales.
    @param sizes: A list of box sizes.
    @param axis: The axis along which those boxes are distributed.
    @param max_size: The maximum size the scaled boxes may have along axis.
    @param allow_upscaling: True if upscaling is allowed, False otherwise.
    @return: A tuple of scales where the i-th scale belongs to the i-th box size.
    If sizes is empty, the empty tuple is returned. If there are more boxes than
    max_size, an approximation is returned where all resulting scales will
    shrink their respective boxes to 1 along axis. In this case, the scaled
    total size might be greater than max_size. """
    n = len(sizes)
    # trivial cases first
    if n == 0:
        return ()
    if n >= max_size:
        # In this case, only one solution or only an approximation available.
        # if n > max_size, the result won't fit into max_size.
        return tuple(map(lambda x: 1.0 / float(x[axis]), sizes))
    total_axis_size = sum(map(lambda x:x[axis], sizes))
    if (total_axis_size <= max_size) and not allow_upscaling:
        # identity
        return (IDENTITY_ZOOM,) * n

    # non-trival case
    scale = float(max_size) / float(total_axis_size)
    scaling_data = [None] * n
    total_axis_size = 0
    # This loop collects some data we need for the actual computations later.
    for i in range(n):
        this_size = sizes[i]
        # Initial guess: The current scale works for all tuples.
        ideal = _scale_tuple(this_size, scale)
        ideal_vol = _volume(ideal)
        # Let's use a dummy to compute the actual (rounded) size along axis so
        # we can rescale the rounded tuple with a better local_scale later.
        # This rescaling is necessary to ensure that the sizes in ALL dimensions
        # are monotonically scaled (with respect to local_scale). A nice side
        # effect of this is that it keeps the aspect ratio better.
        dummy_approx = _round_nonempty((ideal[axis],))[0]
        local_scale = float(dummy_approx) / float(this_size[axis])
        total_axis_size += dummy_approx
        can_be_downscaled = dummy_approx > 1
        if can_be_downscaled:
            forced_size = dummy_approx - 1
            forced_scale = float(forced_size) / float(this_size[axis])
            forced_approx = _scale_image_size(this_size, forced_scale)
            forced_vol_err = _relerr(_volume(forced_approx), ideal_vol)
        else:
            forced_scale = None
            forced_vol_err = None
        scaling_data[i] = [local_scale, ideal, can_be_downscaled, forced_scale,
            forced_vol_err]
    # Now we need to find at most total_axis_size - max_size occasions to scale
    # down some tuples so the whole thing would fit into max_size. If we are
    # lucky, there will be no gaps at the end (or at least fewer gaps than we
    # would have if we always rounded down).
    while total_axis_size > max_size:
        # This algorithm needs O(n*n) time. Let's hope that n is small enough.
        current_index = 0
        current_min = None
        for i in range(n):
            d = scaling_data[i]
            if not d[2]:
                # Ignore elements that cannot be made any smaller.
                continue
            if (current_min is None) or (d[4] < current_min[4]):
                # We are searching for the tuple where downscaling results in
                # the smallest relative volume error (compared to the respective
                # ideal volume).
                current_min = d
                current_index = i
        for i in range(current_index, n):
            # We must scale down ALL equal tuples. Otherwise, images that are of
            # equal size might appear to be of different size afterwards. The
            # downside of this approach is that it might introduce more gaps
            # than necessary.
            d = scaling_data[i]
            if (not d[2]) or (d[1] != current_min[1]):
                continue
            d[0] = d[3]
            d[2] = False # only once per tuple
            total_axis_size -= 1
    else:
        # If we are here and total_axis_size < max_size, we could try to upscale
        # some tuples similarily to the other loop (i.e. smallest relative
        # volume error first, equal boxes in conjunction with each other).
        # However, this is not as useful as the other loop, slightly more
        # complicated and it won't do anything if all tuples are equal.
        pass
    return tuple(map(lambda d: d[0], scaling_data))



# vim: expandtab:sw=4:ts=4

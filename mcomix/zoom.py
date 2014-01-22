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
        self._fitmode = constants.ZOOM_MODE_MANUAL
        self._scale_up = False

    def set_fit_mode(self, fitmode):
        if fitmode < constants.ZOOM_MODE_BEST or \
            fitmode > constants.ZOOM_MODE_SIZE:
            raise ValueError("No fit mode for id %d." % fitmode)
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
        preferred_scale = ZoomModel._get_preferred_scale(image_size,
            screen_size, self._fitmode)
        if (preferred_scale > IDENTITY_ZOOM and
            not self.get_scale_up() and
            any(_smaller(image_size, screen_size))):
            preferred_scale = IDENTITY_ZOOM

        return tuple(_scale_image_size(image_size,
            preferred_scale * 2 ** (self._user_zoom_log / USER_ZOOM_LOG_SCALE1)))

    @staticmethod
    def _get_preferred_scale(image_size, screen_size, fitmode):
        manual = fitmode == constants.ZOOM_MODE_MANUAL
        if (manual and all(_smaller(image_size, screen_size))) or \
            fitmode == constants.ZOOM_MODE_BEST:
            return reduce(min, map(
                lambda axis: _div(screen_size[axis], image_size[axis]),
                range(len(image_size))))
        if manual:
            return IDENTITY_ZOOM
        fixed = None
        if fitmode == constants.ZOOM_MODE_SIZE:
            fitmode = prefs['fit to size mode'] # reassigning fitmode
            fixed = int(prefs['fit to size px'])
        if fitmode == constants.ZOOM_MODE_WIDTH:
            axis = constants.WIDTH_AXIS
        elif fitmode == constants.ZOOM_MODE_HEIGHT:
            axis = constants.HEIGHT_AXIS
        else:
            assert False, 'Cannot map fitmode to axis'
        return _div((fixed if fixed is not None else screen_size[axis]),
            image_size[axis])

    @staticmethod
    def _scale_distributed(sizes, axis, max_size, allow_upscaling):
        """ Calculates scales for a list of boxes that are distributed along a
        given axis (without any gaps). If the resulting scales are applied to
        their respective boxes, their new total size along axis will be as close
        as possible to max_size. The current implementation ensures that equal
        box sizes are mapped to equal scales.
        @param sizes: A list of box sizes.
        @param axis: The axis along which those boxes are distributed.
        @param max_size: The maximum size the scaled boxes may have along axis.
        @param allow_upscaling: True if upscaling is allowed, False otherwise.
        @return: A list of scales where the i-th scale belongs to the i-th box
        size. If sizes is empty, the empty list is returned. If there are more
        boxes than max_size, an approximation is returned where all resulting
        scales will shrink their respective boxes to 1 along axis. In this case,
        the scaled total size might be greater than max_size. """
        n = len(sizes)
        # trivial cases first
        if n == 0:
            return []
        if n >= max_size:
            # In this case, only one solution or only an approximation available.
            # if n > max_size, the result won't fit into max_size.
            return map(lambda x: _div(1, x[axis]), sizes)
        total_axis_size = sum(map(lambda x: x[axis], sizes))
        if (total_axis_size <= max_size) and not allow_upscaling:
            # identity
            return [IDENTITY_ZOOM] * n

        # non-trival case
        scale = _div(max_size, total_axis_size)
        scaling_data = [None] * n
        total_axis_size = 0
        # This loop collects some data we need for the actual computations later.
        for i in range(n):
            this_size = sizes[i]
            # Initial guess: The current scale works for all tuples.
            ideal = _scale_tuple(this_size, scale)
            ideal_vol = _volume(ideal)
            # Let's use a dummy to compute the actual (rounded) size along axis
            # so we can rescale the rounded tuple with a better local_scale
            # later. This rescaling is necessary to ensure that the sizes in ALL
            # dimensions are monotonically scaled (with respect to local_scale).
            # A nice side effect of this is that it keeps the aspect ratio better.
            dummy_approx = _round_nonempty((ideal[axis],))[0]
            local_scale = _div(dummy_approx, this_size[axis])
            total_axis_size += dummy_approx
            can_be_downscaled = dummy_approx > 1
            if can_be_downscaled:
                forced_size = dummy_approx - 1
                forced_scale = _div(forced_size, this_size[axis])
                forced_approx = _scale_image_size(this_size, forced_scale)
                forced_vol_err = _relerr(_volume(forced_approx), ideal_vol)
            else:
                forced_scale = None
                forced_vol_err = None
            scaling_data[i] = [local_scale, ideal, can_be_downscaled,
                forced_scale, forced_vol_err]
        # Now we need to find at most total_axis_size - max_size occasions to
        # scale down some tuples so the whole thing would fit into max_size. If
        # we are lucky, there will be no gaps at the end (or at least fewer gaps
        # than we would have if we always rounded down).
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
                    # We are searching for the tuple where downscaling results
                    # in the smallest relative volume error (compared to the
                    # respective ideal volume).
                    current_min = d
                    current_index = i
            for i in range(current_index, n):
                # We must scale down ALL equal tuples. Otherwise, images that
                # are of equal size might appear to be of different size
                # afterwards. The downside of this approach is that it might
                # introduce more gaps than necessary.
                d = scaling_data[i]
                if (not d[2]) or (d[1] != current_min[1]):
                    continue
                d[0] = d[3]
                d[2] = False # only once per tuple
                total_axis_size -= 1
        else:
            # If we are here and total_axis_size < max_size, we could try to
            # upscale some tuples similarily to the other loop (i.e. smallest
            # relative volume error first, equal boxes in conjunction with each
            # other). However, this is not as useful as the other loop, slightly
            # more complicated and it won't do anything if all tuples are equal.
            pass
        return map(lambda d: d[0], scaling_data)

def _smaller(a, b):
    """ Returns a list with the i-th element set to True if and only the i-th
    element in a is less than the i-th element in b. """
    return map(operator.lt, a, b)

def _scale_image_size(size, scale):
    return _round_nonempty(_scale_tuple(size, scale))

def _scale_tuple(t, factor):
    return [x * factor for x in t]

def _round_nonempty(t):
    result = [0] * len(t)
    for i in range(len(t)):
        x = int(round(t[i]))
        result[i] = x if x > 0 else 1
    return result

def _volume(t):
    return reduce(operator.mul, t, 1)

def _div(a, b):
    return float(a) / float(b)

def _relerr(approx, ideal):
    return abs((approx - ideal) / ideal)

# vim: expandtab:sw=4:ts=4

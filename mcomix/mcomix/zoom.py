''' Handles zoom and fit of images in the main display area. '''

from functools import reduce

from mcomix import constants
from mcomix.preferences import prefs
from mcomix import tools

IDENTITY_ZOOM = 1.0
IDENTITY_ZOOM_LOG = 0
USER_ZOOM_LOG_SCALE1 = 4.0
MIN_USER_ZOOM_LOG = -20
MAX_USER_ZOOM_LOG = 12

class ZoomModel(object):
    ''' Handles zoom and fit modes. '''

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
            raise ValueError('No fit mode for id %d.' % fitmode)
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

    def get_zoomed_size(self, image_sizes, screen_size, distribution_axis, do_not_transform):
        scale_up = self._scale_up
        fitted_image_sizes=_fix_page_sizes(image_sizes, distribution_axis)
        union_size = _union_size(fitted_image_sizes, distribution_axis)
        limits = ZoomModel._calc_limits(union_size, screen_size, self._fitmode, scale_up)
        prefscale = ZoomModel._preferred_scale(union_size, limits, distribution_axis)
        preferred_scales = [(IDENTITY_ZOOM if dnt else prefscale) for dnt in do_not_transform]
        prescaled = [tuple(_scale_image_size(size, scale))
                     for size, scale in zip(fitted_image_sizes, preferred_scales)]
        prescaled_union_size = _union_size(prescaled, distribution_axis)
        def _other_preferences(limits, distribution_axis):
            for i in range(len(limits)):
                if i == distribution_axis:
                    continue
                if limits[i] is not None:
                    return True
            return False
        other_preferences = _other_preferences(limits, distribution_axis)
        if limits[distribution_axis] is not None and \
            (prescaled_union_size[distribution_axis] > screen_size[distribution_axis]
            or not other_preferences):
            distributed_scales = ZoomModel._scale_distributed(fitted_image_sizes,
                distribution_axis, limits[distribution_axis], scale_up, do_not_transform)
            if other_preferences:
                preferred_scales = map(min, preferred_scales, distributed_scales)
            else:
                preferred_scales = distributed_scales
        if not scale_up:
            preferred_scales = map(lambda x: min(x, IDENTITY_ZOOM), preferred_scales)
        preferred_scales = list(preferred_scales)
        user_scale = 2 ** (self._user_zoom_log / USER_ZOOM_LOG_SCALE1)
        res_scales = [preferred_scales[i] * (user_scale if not do_not_transform[i] else IDENTITY_ZOOM)
                      for i in range(len(preferred_scales))]
        return [tuple(_scale_image_size(size, scale))
                for size, scale in zip(fitted_image_sizes, res_scales)]

    @staticmethod
    def _preferred_scale(image_size, limits, distribution_axis):
        ''' Returns scale that makes an image of size image_size respect the
        limits imposed by limits. If no proper value can be determined,
        IDENTITY_ZOOM is returned. '''
        min_scale = None
        for i in range(len(limits)):
            if i == distribution_axis:
                continue
            l = limits[i]
            if l is None:
                continue
            s = tools.div(l, image_size[i])
            if min_scale is None or s < min_scale:
                min_scale = s
        if min_scale is None:
            min_scale = IDENTITY_ZOOM
        return min_scale

    @staticmethod
    def _calc_limits(union_size, screen_size, fitmode, allow_upscaling):
        ''' Returns a list or a tuple with the i-th element set to int x if
        fitmode limits the size at the i-th axis to x, or None if fitmode has no
        preference for this axis. '''
        manual = fitmode == constants.ZOOM_MODE_MANUAL
        if fitmode == constants.ZOOM_MODE_BEST or \
            (manual and allow_upscaling and all(tools.smaller(union_size, screen_size))):
            return screen_size
        result = [None] * len(screen_size)
        if not manual:
            fixed_size = None
            if fitmode == constants.ZOOM_MODE_SIZE:
                fitmode = prefs['fit to size mode'] # reassigning fitmode
                fixed_size = int(prefs['fit to size px'])
            if fitmode == constants.ZOOM_MODE_WIDTH:
                axis = constants.WIDTH_AXIS
            elif fitmode == constants.ZOOM_MODE_HEIGHT:
                axis = constants.HEIGHT_AXIS
            else:
                assert False, 'Cannot map fitmode to axis'
            result[axis] = fixed_size if fixed_size is not None else screen_size[axis]
        return result

    @staticmethod
    def _scale_distributed(sizes, axis, max_size, allow_upscaling,
        do_not_transform):
        ''' Calculates scales for a list of boxes that are distributed along a
        given axis (without any gaps). If the resulting scales are applied to
        their respective boxes, their new total size along axis will be as close
        as possible to max_size. The current implementation ensures that equal
        box sizes are mapped to equal scales.
        @param sizes: A list of box sizes.
        @param axis: The axis along which those boxes are distributed.
        @param max_size: The maximum size the scaled boxes may have along axis.
        @param allow_upscaling: True if upscaling is allowed, False otherwise.
        @param do_not_transform: True if the resulting scale must be 1, False
        otherwise.
        @return: A list of scales where the i-th scale belongs to the i-th box
        size. If sizes is empty, the empty list is returned. If there are more
        boxes than max_size, an approximation is returned where all resulting
        scales will shrink their respective boxes to 1 along axis. In this case,
        the scaled total size might be greater than max_size. '''
        n = len(sizes)
        # trivial cases first
        if n == 0:
            return []
        if n >= max_size:
            # In this case, only one solution or only an approximation is available.
            # if n > max_size, the result won't fit into max_size.
            return map(lambda x: tools.div(1, x[axis]), sizes) # FIXME ignores do_not_transform
        total_axis_size = sum(map(lambda x: x[axis], sizes))
        if (total_axis_size <= max_size) and not allow_upscaling:
            # identity
            return [IDENTITY_ZOOM] * n

        # non-trival case
        scale = tools.div(max_size, total_axis_size) # FIXME initial guess should take unscalable images into account
        scaling_data = [None] * n
        total_axis_size = 0
        # This loop collects some data we need for the actual computations later.
        for i in range(n):
            this_size = sizes[i]
            # Shortcut: If the size cannot be changed, accept the original size.
            if do_not_transform[i]:
                total_axis_size += this_size[axis]
                scaling_data[i] = [IDENTITY_ZOOM, IDENTITY_ZOOM, False,
                    IDENTITY_ZOOM, 0.0]
                continue
            # Initial guess: The current scale works for all tuples.
            ideal = tools.scale(this_size, scale)
            ideal_vol = tools.volume(ideal)
            # Let's use a dummy to compute the actual (rounded) size along axis
            # so we can rescale the rounded tuple with a better local_scale
            # later. This rescaling is necessary to ensure that the sizes in ALL
            # dimensions are monotonically scaled (with respect to local_scale).
            # A nice side effect of this is that it keeps the aspect ratio better.
            dummy_approx = _round_nonempty((ideal[axis],))[0]
            local_scale = tools.div(dummy_approx, this_size[axis])
            total_axis_size += dummy_approx
            can_be_downscaled = dummy_approx > 1
            if can_be_downscaled:
                forced_size = dummy_approx - 1
                forced_scale = tools.div(forced_size, this_size[axis])
                forced_approx = _scale_image_size(this_size, forced_scale)
                forced_vol_err = tools.relerr(tools.volume(forced_approx), ideal_vol)
            else:
                forced_scale = None
                forced_vol_err = None
            scaling_data[i] = [local_scale, ideal, can_be_downscaled,
                forced_scale, forced_vol_err]
        # Now we need to find at most total_axis_size - max_size occasions to
        # scale down some tuples so the whole thing would fit into max_size. If
        # we are lucky, there will be no gaps at the end (or at least fewer gaps
        # than we would have if we always rounded down).
        dirty=True # This flag prevents infinite loops if nothing can be made any smaller.
        while dirty and (total_axis_size > max_size):
            # This algorithm needs O(n*n) time. Let's hope that n is small enough.
            dirty=False
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
                dirty=True
        else:
            # If we are here and total_axis_size < max_size, we could try to
            # upscale some tuples similarily to the other loop (i.e. smallest
            # relative volume error first, equal boxes in conjunction with each
            # other). However, this is not as useful as the other loop, slightly
            # more complicated and it won't do anything if all tuples are equal.
            pass
        return map(lambda d: d[0], scaling_data)

def _scale_image_size(size, scale):
    return _round_nonempty(tools.scale(size, scale))

def _round_nonempty(t):
    result = [0] * len(t)
    for i in range(len(t)):
        x = int(round(t[i]))
        result[i] = x if x > 0 else 1
    return result

def _fix_page_sizes(image_sizes, distribution_axis):
    if len(image_sizes)<2:
        return image_sizes.copy()
    # in double page mode, resize the smaller image to fit the bigger one
    new_sizes=[]
    sizes=list(zip(*image_sizes)) # [(x1,x2,...),(y1,y2,...)]
    axis_sizes=sizes[int(not distribution_axis)] # use axis else of distribution_axis
    max_size=max(axis_sizes) # max size of pages
    ratios=[max_size/s for s in axis_sizes] # scale ratio of every page
    for n,(x,y) in enumerate(image_sizes):
        new_sizes.append((int(x*ratios[n]),int(y*ratios[n]))) # scale every page
    return new_sizes

def _union_size(image_sizes, distribution_axis):
    if len(image_sizes) == 0:
        return []
    n = len(image_sizes[0])
    union_size = list(map(lambda i: reduce(max, map(lambda x: x[i], image_sizes)), range(n)))
    union_size[distribution_axis] = sum(tuple(map(lambda x: x[distribution_axis], image_sizes)))
    return union_size

# vim: expandtab:sw=4:ts=4

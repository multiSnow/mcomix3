""" Smart scrolling. """

from mcomix import tools
import math


WESTERN_FORWARDS_ORIENTATION = [1, 1]
WESTERN_BACKWARDS_ORIENTATION = [-1, -1]
MANGA_FORWARDS_ORIENTATION = [-1, 1]
MANGA_BACKWARDS_ORIENTATION = [1, -1]

SCROLL_TO_CENTER = -2

NORMAL_AXES = [0, 1]
SWAPPED_AXES = [1, 0]


class Scrolling(object):

    def __init__(self):
        self.clear_cache()


    def scroll_smartly(self, content_size, viewport_size, viewport_position,
        orientation, max_scroll, axis_map=None):
        """ Returns a new viewport_position when reading forwards using
        the given orientation. If there is no space left to go, the empty
        list is returned. Note that all params are lists of ints (except
        max_scroll which might also contain floats) where each index
        corresponds to one dimension. The lower the index, the faster the
        corresponding position changes when reading. If you need to override
        this behavior, use the optional axis_map.
        @param content_size: The size of the content to display.
        @param viewport_size: The size of the viewport we are looking through.
        @param viewport_position: The current position of the viewport,
        should be between 0 and content_size-viewport_size (inclusive).
        @param orientation: The orientation which shows where "forward"
        points to. Either 1 (towards greater values in this dimension when
        reading) or -1 (towards lesser values in this dimension when reading).
        Note that you can emulate "reading backwards" by flipping the sign
        of this argument.
        @param max_scroll: The maximum number of pixels to scroll in one step.
        (Floats allowed.)
        @param axis_map: The index of the dimension to modify.
        @return: A new viewport_position if you can read further or the
        empty list if there is nothing left to read. """

        # Axis remapping is implemented here only for convenience.
        # Callers can always remap the axes themselves by simply applying
        # the remapping beforehand and applying the inverse to the result
        # afterwards.
        if axis_map is not None:
            content_size, viewport_size, viewport_position, orientation, \
                max_scroll = Scrolling._map_remap_axes([content_size,
                viewport_size, viewport_position, orientation, max_scroll],
                axis_map)

        # This code is somewhat similar to a simple ripple-carry adder.
        result = list(viewport_position)
        carry = True
        for i in range(len(content_size)):
            vs = viewport_size[i]
            invisible_size = content_size[i] - vs

            if invisible_size <= 0:
                # There is nothing to do in this dimension. Fast forward.
                continue

            o = orientation[i]
            ms = min(max_scroll[i], invisible_size)

            # Let's calculate the grid we want to snap to.
            if ms != 0:
                steps_to_take = int(math.ceil(float(invisible_size) / ms))
            if ms == 0 or steps_to_take >= invisible_size:
                # special case: We MUST go forward by at least 1 pixel.
                if o >= 0:
                    result[i] += 1
                    carry = result[i] > invisible_size
                    if carry:
                        result[i] = 0
                        continue
                else:
                    result[i] -= 1
                    carry = result[i] < 0
                    if carry:
                        result[i] = invisible_size
                        continue
                break
            positions = self._cached_bs(invisible_size, steps_to_take)

            # Where are we now (according to the grid)?
            index = tools.bin_search(positions, viewport_position[i])

            if index < 0:
                # We're somewhere between two valid grid points, so
                # let's go to the next one.
                index = ~index
                if o >= 0:
                    # index tends to be greater, so we need to go back
                    # manually, if needed.
                    index -= 1
            # Let's go to where we're headed for.
            index += o

            carry = index < 0 or index >= len(positions)
            if carry:
                # There is no space left in this dimension, so let's go
                # back in this one and one step forward in the next one.
                result[i] = 0 if o > 0 else invisible_size
            else:
                # We found a valid grid point in this dimension, so let's
                # stop here.
                result[i] = positions[index]
                break
        if carry:
            # No space left.
            return []

        # Undo axis remapping, if any
        if axis_map is not None:
            result = Scrolling._remap_axes(result,
                Scrolling._inverse_axis_map(axis_map))

        return result


    def scroll_to_predefined(self, content_size, viewport_size, viewport_position,
        destination):
        """ Returns a new viewport_position when scrolling towards a
        predefined destination. Note that all params are lists of integers
        where each index corresponds to one dimension.
        @param content_size: The size of the content to display.
        @param viewport_size: The size of the viewport we are looking through.
        @param viewport_position: The current position of the viewport,
        should be between 0 and content_size-viewport_size (inclusive).
        @param destination: An integer representing a predefined destination.
        Either 1 (towards the greatest possible values in this dimension),
        -1 (towards the smallest value in this dimension), 0 (keep position)
        or SCROLL_TO_CENTER (scroll to the center of the content in this
        dimension).
        @return: A new viewport_position as specified above. """

        result = list(viewport_position)
        for i in range(len(content_size)):
            d = destination[i]
            if d == 0:
                continue
            if d < SCROLL_TO_CENTER or d > 1:
                raise ValueError("invalid destination " + d + " at index "+ i);
            invisible_size = content_size[i] - viewport_size[i]
            result[i] = (invisible_size / 2 if d == SCROLL_TO_CENTER
                    else invisible_size if d == 1
                    else 0) # if d == -1
        return result


    def _cached_bs(self, num, denom):
        """ A simple (and ugly) caching mechanism used to avoid
        recomputations. The current implementation offers a cache with
        only two entries so it's only useful for the two "fastest"
        dimensions. """
        if self._cache0[0] != num or self._cache0[1] != denom:
            self._cache0, self._cache1 = self._cache1, self._cache0
        if self._cache0[0] != num or self._cache0[1] != denom:
            self._cache0 = (num, denom, Scrolling._bresenham_sums(num, denom))
        return self._cache0[2]


    def clear_cache(self):
        """ Clears all caches that are used internally. """
        self._cache0 = (0, 0, [])
        self._cache1 = (0, 0, [])


    @staticmethod
    def _bresenham_sums(num, denom):
        """ This algorithm is derived from Bresenham's line algorithm in
        order to distribute the remainder of num/denom equally. See
        https://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm for details.
        """
        if num < 0:
            raise ValueError("num < 0");
        if denom < 1:
            raise ValueError("denom < 1");
        quotient = num // denom;
        remainder = num % denom;
        error = denom >> 1;
        result = [0]
        partial_sum = 0
        for i in range(denom):
            error -= remainder
            if error < 0:
                error += denom
                partial_sum += quotient + 1
            else:
                partial_sum += quotient
            result.append(partial_sum)
        return result


    @staticmethod
    def _remap_axes(vector, order):
        return [vector[i] for i in order]


    @staticmethod
    def _map_remap_axes(vectors, order):
        return map(lambda v: Scrolling._remap_axes(v, order), vectors)


    @staticmethod
    def _inverse_axis_map(order):
        identity = range(len(order))
        return [identity[order[i]] for i in identity]


# vim: expandtab:sw=4:ts=4

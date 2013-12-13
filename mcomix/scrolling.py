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
        points to. Either 1 (towards larger values in this dimension when
        reading) or -1 (towards smaller values in this dimension when reading).
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
            # If orientation is -1, we need to round half up instead of
            # half down.
            positions = self._cached_bs(invisible_size, steps_to_take, o == -1)

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
        orientation, destination):
        """ Returns a new viewport_position when scrolling towards a
        predefined destination. Note that all params are lists of integers
        where each index corresponds to one dimension.
        @param content_size: The size of the content to display.
        @param viewport_size: The size of the viewport we are looking through.
        @param viewport_position: The current position of the viewport,
        should be between 0 and content_size-viewport_size (inclusive).
        @param orientation: The orientation which shows where "forward"
        points to. Either 1 (towards larger values in this dimension when
        reading) or -1 (towards smaller values in this dimension when reading).
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
            c = content_size[i]
            v = viewport_size[i]
            invisible_size = c - v
            result[i] = (Box._box_to_center_offset_1d(v - c, orientation[i])
                if d == SCROLL_TO_CENTER
                else invisible_size if d == 1
                else 0) # if d == -1
        return result


    def _cached_bs(self, num, denom, half_up):
        """ A simple (and ugly) caching mechanism used to avoid
        recomputations. The current implementation offers a cache with
        only two entries so it's only useful for the two "fastest"
        dimensions. """
        if (self._cache0[0] != num or
            self._cache0[1] != denom or
            self._cache0[2] != half_up):
            self._cache0, self._cache1 = self._cache1, self._cache0
        if (self._cache0[0] != num or
            self._cache0[1] != denom or
            self._cache0[2] != half_up):
            self._cache0 = (num, denom, half_up,
                Scrolling._bresenham_sums(num, denom, half_up))
        return self._cache0[3]


    def clear_cache(self):
        """ Clears all caches that are used internally. """
        self._cache0 = (0, 0, False, [])
        self._cache1 = (0, 0, False, [])


    @staticmethod
    def _bresenham_sums(num, denom, half_up):
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
        needs_up = half_up and (remainder != 0) and ((denom & 1) == 0)
        up_flag = False
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

            # round half up, if necessary
            if up_flag:
                partial_sum -= 1;
                up_flag = False;
            elif needs_up and error == 0:
                partial_sum += 1;
                up_flag = True;

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



class Box(object):

    def __init__(self, position, size, content=None):
        """ A box is always axis-aligned.
        Each component of size should be positive (i.e. non-zero). """
        self.position = tuple(position)
        self.size = tuple(size)
        self.content = content


    def get_size(self):
        return self.size

    def get_position(self):
        return self.position

    def get_content(self):
        return self.content

    def distance_point_squared(self, point):
        """ Returns the square of the Euclidean distance between this box and a
        point. If the point lies within the box, this box is said to have a
        distance of zero. Otherwise, the square of the Euclidean distance
        between point and the closest point of the box is returned.
        @param point: The point of interest.
        @return The distance between the point and the box as specified above. """

        result = 0
        for i in range(len(point)):
            p = point[i]
            bs = self.position[i]
            be = self.size[i] + bs
            if p < bs:
                r = bs - p
            elif p >= be:
                r = p - be + 1
            else:
                continue
            result += r * r
        return result


    @staticmethod
    def closest_boxes(point, boxes, orientation=None):
        """ Returns the indices of the boxes that are closest to the specified
        point. First, the Euclidean distance between point and the closest point
        of the respective box is used to determine which of these boxes are the
        closest ones. If two boxes have the same distance, the box that is
        closer to the origin as defined by orientation is said to have a shorter
        distance.
        @param point: The point of interest.
        @param boxes: A list of boxes.
        @param orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading). If
        orientation is set to None, it will be ignored.
        @return The indices of the closest boxes as specified above. """

        result = []
        mindist = -1
        for i in range(len(boxes)):
            # 0 --> keep
            # 1 --> append
            # 2 --> replace
            keep_append_replace = 0
            b = boxes[i]
            dist = b.distance_point_squared(point)
            if (result == []) or (dist < mindist):
                keep_append_replace = 2
            elif dist == mindist:
                if orientation is not None:
                # Take orientation into account.
                # If result is small, a simple iteration shouldn't be a
                # performance issue.
                    for ri in range(len(result)):
                        c = Box._compare_distance_to_origin(b,
                            boxes[result[ri]], orientation)
                        if c < 0:
                            keep_append_replace = 2
                            break
                        if c == 0:
                            keep_append_replace = 1
                else:
                    keep_append_replace = 1

            if keep_append_replace == 1:
                result.append(i)
            if keep_append_replace == 2:
                mindist = dist
                result = [i]
        return result


    @staticmethod
    def _compare_distance_to_origin(box1, box2, orientation):
        """ Returns an integer that is less than, equal to or greater than zero
        if the distance between box1 and the origin is less than, equal to or
        greater than the distance between box2 and the origin, respectively.
        The origin is implied by orientation.
        @param box1: The first box.
        @param box2: The second box.
        @param orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading).
        @return An integer as specified above. """
        for i in range(len(orientation)):
            o = orientation[i]
            if o == 0:
                continue
            box1edge = box1.get_position()[i]
            box2edge = box2.get_position()[i]
            if o < 0:
                box1edge = box1.get_size()[i] - box1edge
                box2edge = box2.get_size()[i] - box2edge
            d = box1edge - box2edge
            if d != 0:
                return d
        return 0


    @staticmethod
    def box_center(box, orientation):
        """ Returns the center of a box. If the exact value is not equal to an
        integer, the integer that is closer to the origin (as implied by
        orientation) is chosen.
        @param box: The box.
        @orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading).
        @return The center of box as specified above. """
        result = []
        bp = box.get_position()
        bs = box.get_size()
        for i in range(len(orientation)):
            result.append(Box._box_to_center_offset_1d(bs[i] - 1,
                orientation[i]) + bp[i])
        return result


    @staticmethod
    def _box_to_center_offset_1d(box_size_delta, orientation):
        t = box_size_delta >> 1
        if ((box_size_delta & 1) == 1) and (orientation == -1):
            t += 1
        return t


    @staticmethod
    def current_box(viewport_box, orientation, boxes):
        return Box.closest_boxes(Box.box_center(viewport_box, orientation),
            boxes, orientation)[0]


# vim: expandtab:sw=4:ts=4

""" Smart scrolling. """

from mcomix import tools
import math


WESTERN_ORIENTATION = (1, 1) # 2D only
MANGA_ORIENTATION = (-1, 1) # 2D only

SCROLL_TO_CENTER = -2

NORMAL_AXES = (0, 1) # 2D only
SWAPPED_AXES = (1, 0) # 2D only



class Scrolling(object):

    def __init__(self):
        self.clear_cache()


    def scroll_smartly(self, content_box, viewport_box, orientation, max_scroll,
        axis_map=None):
        """ Returns a new viewport position when reading forwards using
        the given orientation. If there is no space left to go, the empty
        list is returned. Note that all params are lists of ints (except
        max_scroll which might also contain floats) where each index
        corresponds to one dimension. The lower the index, the faster the
        corresponding position changes when reading. If you need to override
        this behavior, use the optional axis_map.
        @param content_box: The Box of the content to display.
        @param viewport_box: The viewport Box we are looking through.
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
        # Translate content and viewport so that content position equals origin
        offset = content_box.get_position()
        content_size = content_box.get_size()
        content_position = [0] * len(offset)
        viewport_position = Box._vector_sub(viewport_box.get_position(), offset)
        viewport_size = viewport_box.get_size()
        # Remap axes
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

        return Box._vector_add(result, offset)


    def scroll_to_predefined(self, content_box, viewport_box, orientation,
        destination):
        """ Returns a new viewport position when scrolling towards a
        predefined destination. Note that all params are lists of integers
        where each index corresponds to one dimension.
        @param content_box: The Box of the content to display.
        @param viewport_box: The viewport Box we are looking through.
        @param orientation: The orientation which shows where "forward"
        points to. Either 1 (towards larger values in this dimension when
        reading) or -1 (towards smaller values in this dimension when reading).
        @param destination: An integer representing a predefined destination.
        Either 1 (towards the greatest possible values in this dimension),
        -1 (towards the smallest value in this dimension), 0 (keep position)
        or SCROLL_TO_CENTER (scroll to the center of the content in this
        dimension).
        @return: A new viewport position as specified above. """
        content_position = content_box.get_position()
        content_size = content_box.get_size()
        viewport_size = viewport_box.get_size()
        result = list(viewport_box.get_position())
        for i in range(len(content_size)):
            d = destination[i]
            if d == 0:
                continue
            if d < SCROLL_TO_CENTER or d > 1:
                raise ValueError("invalid destination " + d + " at index "+ i)
            c = content_size[i]
            v = viewport_size[i]
            invisible_size = c - v
            result[i] = content_position[i] + (Box._box_to_center_offset_1d(
                invisible_size, orientation[i]) if d == SCROLL_TO_CENTER
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

    def __init__(self, position, size):
        """ A Box is immutable and always axis-aligned.
        Each component of size should be positive (i.e. non-zero).
        Both position and size must have equal number of dimensions.
        @param position: The position of this Box.
        @param size: The size of this Box."""
        self.position = tuple(position)
        self.size = tuple(size)
        if len(self.position) != len(self.size):
            raise ValueError("different number of dimensions: " +
                str(len(self.position)) + " != " + str(len(self.size)))


    def __str__(self):
        """ Returns a string representation of this Box. """
        return "{" + str(self.get_position()) + ":" + str(self.get_size()) + "}"


    def __eq__(self, other):
        """ Two Boxes are said to be equal if and only if the number of
        dimensions, the positions and the sizes of the two Boxes are equal,
        respectively. """
        return (self.get_position() == other.get_position()) and \
            (self.get_size() == self.get_size())


    def __len__(self):
        """ Returns the number of dimensions of this Box. """
        return len(self.position)


    def get_size(self):
        """ Returns the size of this Box.
        @return: The size of this Box. """
        return self.size


    def get_position(self):
        """ Returns the position of this Box.
        @return: The position of this Box. """
        return self.position


    def set_position(self, position):
        """ Returns a new Box that has the same size as this Box and the
        specified position.
        @return: A new Box as specified above. """
        return Box(position, self.get_size())


    def set_size(self, size):
        """ Returns a new Box that has the same position as this Box and the
        specified size.
        @return: A new Box as specified above. """
        return Box(self.get_position(), size)


    def distance_point_squared(self, point):
        """ Returns the square of the Euclidean distance between this Box and a
        point. If the point lies within the Box, this Box is said to have a
        distance of zero. Otherwise, the square of the Euclidean distance
        between point and the closest point of the Box is returned.
        @param point: The point of interest.
        @return The distance between the point and the Box as specified above.
        """
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


    def translate(self, delta):
        """ Returns a new Box that has the same size as this Box and a
        translated position as specified by delta.
        @param delta: The distance to the position of this Box.
        @return: A new Box as specified above. """
        return Box(Box._vector_add(self.get_position(), delta),
            self.get_size())


    def translate_opposite(self, delta):
        """ Returns a new Box that has the same size as this Box and a
        oppositely translated position as specified by delta.
        @param delta: The distance to the position of this Box, with opposite
        direction.
        @return: A new Box as specified above. """
        return Box(Box._vector_sub(self.get_position(), delta),
            self.get_size())


    @staticmethod
    def closest_boxes(point, boxes, orientation=None):
        """ Returns the indices of the Boxes that are closest to the specified
        point. First, the Euclidean distance between point and the closest point
        of the respective Box is used to determine which of these Boxes are the
        closest ones. If two Boxes have the same distance, the Box that is
        closer to the origin as defined by orientation is said to have a shorter
        distance.
        @param point: The point of interest.
        @param boxes: A list of Boxes.
        @param orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading). If
        orientation is set to None, it will be ignored.
        @return The indices of the closest Boxes as specified above. """
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
        @param box1: The first Box.
        @param box2: The second Box.
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


    def get_center(self, orientation):
        """ Returns the center of this Box. If the exact value is not equal to
        an integer, the integer that is closer to the origin (as implied by
        orientation) is chosen.
        @orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading).
        @return The center of this Box as specified above. """
        result = [0] * len(orientation)
        bp = self.get_position()
        bs = self.get_size()
        for i in range(len(orientation)):
            result[i] = Box._box_to_center_offset_1d(bs[i] - 1,
                orientation[i]) + bp[i]
        return result


    @staticmethod
    def _box_to_center_offset_1d(box_size_delta, orientation):
        if orientation == -1:
            box_size_delta += 1
        return box_size_delta >> 1


    def current_box_index(self, orientation, boxes):
        """ Calculates the index of the Box that is closest to the center of
        this Box.
        @param orientation: The orientation to use.
        @param boxes: The Boxes to examine.
        @return: The index as specified above. """
        return Box.closest_boxes(self.get_center(orientation), boxes,
            orientation)[0]


    @staticmethod
    def align_center(boxes, axis, fix, orientation):
        """ Aligns Boxes so that the center of each Box appears on the same
        line.
        @param axis: the axis to center.
        @param fix: the index of the Box that should not move.
        @param orientation: The orientation to use.
        @return: A list of new Boxes with accordingly translated positions. """
        if len(boxes) == 0:
            return []
        centerBox = boxes[fix]
        cs = centerBox.get_size()[axis]
        cp = centerBox.get_position()[axis]
        result = []
        for b in boxes:
            s = b.get_size()
            p = list(b.get_position())
            p[axis] = cp + Box._box_to_center_offset_1d(cs - s[axis],
                orientation)
            result.append(Box(p, s))
        return result


    @staticmethod
    def distribute(boxes, axis, fix, spacing=0):
        """ Ensures that the Boxes do not overlap. For this purpose, the Boxes
        are distributed according to the index of the respective Box.
        @param axis: the axis along which the Boxes are distributed.
        @param fix: the index of the Box that should not move.
        @param spacing: the number of additional pixels between Boxes.
        @return: A new list with new Boxes that are accordingly translated. """
        if len(boxes) == 0:
            return []
        result = [None] * len(boxes)
        initialSum = boxes[fix].get_position()[axis]
        partial_sum = initialSum
        for bi in range(fix, len(boxes)):
            b = boxes[bi]
            s = b.get_size()
            p = list(b.get_position())
            p[axis] = partial_sum
            result[bi] = Box(p, s)
            partial_sum += s[axis] + spacing
        partial_sum = initialSum;
        for bi in range(fix - 1, -1, -1):
            b = boxes[bi]
            s = b.get_size()
            p = list(b.get_position())
            partial_sum -= s[axis] + spacing
            p[axis] = partial_sum
            result[bi] = Box(p, s)
        return result


    def wrapper_box(self, viewport_size, orientation):
        """ Returns a Box that covers the same area that is covered by a
        scrollable viewport showing this Box.
        @param viewport_size: The size of the viewport.
        @param orientation: The orientation to use.
        @return: A Box as specified above. """
        size = self.get_size()
        position = self.get_position()
        result_size = [0] * len(size)
        result_position = [0] * len(size)
        for i in range(len(size)):
            c = size[i]
            v = viewport_size[i]
            result_size[i] = max(c, v)
            result_position[i] = Box._box_to_center_offset_1d(c - result_size[i],
                orientation[i]) + position[i]
        return Box(result_position, result_size)


    @staticmethod
    def bounding_box(boxes):
        """ Returns the union of all specified Boxes (that is, the smallest Box
        that contains all specified Boxes).
        @param boxes: The Boxes to calculate the union from.
        @return: A Box as specified above. """
        if len(boxes) == 0:
            return Box([], [])
        mins = [None] * len(boxes[0].get_size())
        maxes = [None] * len(mins)
        for b in boxes:
            s = b.get_size()
            p = b.get_position()
            for i in range(len(mins)):
                if (mins[i] is None) or (p[i] < mins[i]):
                    mins[i] = p[i]
                ps = p[i] + s[i]
                if (maxes[i] is None) or (ps > maxes[i]):
                    maxes[i] = ps
        return Box(mins, Box._vector_sub(maxes, mins))


    @staticmethod
    def _vector_sub(a, b):
        """ Subtracts vector b from vector a. """
        result = [0] * len(a)
        for i in range(len(a)):
            result[i] = a[i] - b[i]
        return result


    @staticmethod
    def _vector_add(a, b):
        """ Adds vector a to vector b. """
        result = [0] * len(a)
        for i in range(len(a)):
            result[i] = a[i] + b[i]
        return result


    @staticmethod
    def _vector_opposite(a):
        """ Returns the opposite vector -a. """
        result = [0] * len(a)
        for i in range(len(a)):
            result[i] = -a[i]
        return result


    @staticmethod
    def intersect(boxA, boxB): # TODO test! docs!
        aPos = boxA.get_position()
        bPos = boxB.get_position()
        aSize = boxA.get_size()
        bSize = boxB.get_size()
        resPos = [0] * len(aPos)
        resSize = [0] * len(aSize)
        for i in range(len(aPos)):
            ax1 = aPos[i]
            bx1 = bPos[i]
            ax2 = ax1
            ax2 += aSize[i]
            bx2 = bx1
            bx2 += bSize[i]
            if ax1 < bx1:
                ax1 = bx1
            if ax2 > bx2:
                ax2 = bx2
            ax2 -= ax1
            resPos[i] = ax1
            resSize[i] = ax2
        return Box(resPos, resSize)



_DISTRIBUTION_AXIS = 0 # 2D only
_ALIGNMENT_AXIS = 1 # 2D only

class FiniteLayout(object): # 2D only

    def __init__(self, content_boxes, viewport_size, orientation, spacing):
        """ Lays out a finite number of Boxes along the first axis.
        @param content_boxes: The Boxes to lay out.
        @param viewport_size: The size of the viewport.
        @param orientation: The orientation to use.
        @param spacing: Number of additional pixels between Boxes. """
        self.scroller = Scrolling()
        self.current_index = -1
        self._reset(content_boxes, viewport_size, orientation, spacing)


    def set_viewport_position(self, viewport_position):
        """ Moves the viewport to the specified position.
        @param viewport_position: The new viewport position. """
        self.viewport_box = self.viewport_box.set_position(viewport_position)
        self.dirty_current_index = True


    def scroll_smartly(self, max_scroll, backwards=False, swapped_axes=False,
        index=None):
        """ Applies a "smart scrolling" step to the current viewport position.
        If there are not enough Boxes to scroll to, the viewport is not moved
        and an appropriate value is returned.
        @param max_scroll: The maximum numbers of pixels to scroll in one step.
        @param backwards: True for backwards scrolling, False otherwise.
        @param swapped_axes: True for swapped axes, False otherwise.
        @param index: The index of the Box the scrolling step is related to,
        or None to use the index of the current Box.
        @return: The index of the current Box after scrolling, or -1 if there
        were not enough Boxes to scroll backwards, or the number of Boxes if
        there were not enough Boxes to scroll forwards. """
        # TODO reconsider interface
        if index == None:
            index = self.get_current_index()
        current_box = self.wrapper_boxes[index]
        o = Box._vector_opposite(self.orientation) if backwards \
            else self.orientation
        axis_map = SWAPPED_AXES if swapped_axes else NORMAL_AXES
        new_pos = self.scroller.scroll_smartly(current_box, self.viewport_box,
            o, max_scroll, axis_map)
        if new_pos == []:
            index += -1 if backwards else 1
            n = len(self.get_content_boxes())
            if (index < n) and (index >= 0):
                self.scroll_to_predefined(Box._vector_opposite(o), index)
            return index
        self.set_viewport_position(new_pos)
        return index


    def scroll_to_predefined(self, destination, index=None):
        """ Scrolls the viewport to a predefined destination.
        @param destination: An integer representing a predefined destination.
        Either 1 (towards the greatest possible values in this dimension),
        -1 (towards the smallest value in this dimension), 0 (keep position)
        or SCROLL_TO_CENTER (scroll to the center of the content in this
        dimension).
        @param index: The index of the Box the scrolling is related to,
        or None to use the index of the current Box. """
        if index == None:
            index = self.get_current_index()
        current_box = self.wrapper_boxes[index]
        self.set_viewport_position(self.scroller.scroll_to_predefined(
            current_box, self.viewport_box, self.orientation, destination))


    def get_content_boxes(self):
        """ Returns the Boxes as they are arranged in this layout. 
        @return: The Boxes as they are arranged in this layout. """
        return self.content_boxes


    def get_wrapper_boxes(self):
        """ Returns the wrapper Boxes as they are arranged in this layout.
        @return: The wrapper Boxes as they are arranged in this layout. """
        return self.wrapper_boxes


    def get_union_box(self):
        """ Returns the union Box for this layout.
        @return: The union Box for this layout. """
        return self.union_box


    def get_current_index(self):
        """ Returns the index of the Box that is said to be the current Box.
        @return: The index of the Box that is said to be the current Box. """
        if self.dirty_current_index:
            self.current_index = self.viewport_box.current_box_index(
                self.orientation, self.content_boxes)
            self.dirty_current_index = False
        return self.current_index


    def get_viewport_box(self):
        """ Returns the current viewport Box.
        @return: The current viewport Box. """
        return self.viewport_box


    def get_orientation(self):
        """ Returns the orientation for this layout.
        @return: The orientation for this layout. """
        return self.orientation


    def _reset(self, content_boxes, viewport_size, orientation, spacing):
        # reverse order if necessary
        if orientation[_DISTRIBUTION_AXIS] == -1:
            content_boxes = tuple(reversed(content_boxes))
        # align to center
        temp_cb_list = Box.align_center(content_boxes, _ALIGNMENT_AXIS, 0,
            orientation[_ALIGNMENT_AXIS])
        # distribute
        temp_cb_list = Box.distribute(temp_cb_list, _DISTRIBUTION_AXIS, 0,
            spacing)
        # calculate (potentially oversized) wrapper Boxes
        temp_wb_list = [None] * len(temp_cb_list)
        for i in range(len(temp_cb_list)):
            temp_wb_list[i] = temp_cb_list[i].wrapper_box(viewport_size,
                orientation)
        # calculate bounding Box
        temp_bb = Box.bounding_box(temp_wb_list)
        # move to global origin
        bbp = temp_bb.get_position()
        for i in range(len(temp_cb_list)):
            temp_cb_list[i] = temp_cb_list[i].translate_opposite(bbp)
        for i in range(len(temp_wb_list)):
            temp_wb_list[i] = temp_wb_list[i].translate_opposite(bbp)
        temp_bb = temp_bb.translate_opposite(bbp)
        # reverse order again, if necessary
        if orientation[_DISTRIBUTION_AXIS] == -1:
            temp_cb_list = tuple(reversed(temp_cb_list))
            temp_wb_list = tuple(reversed(temp_wb_list))
        # done
        self.content_boxes = temp_cb_list
        self.wrapper_boxes = temp_wb_list
        self.union_box = temp_bb
        self.viewport_box = Box((0,) * len(viewport_size), viewport_size)
        self.orientation = orientation
        self.dirty_current_index = True


# vim: expandtab:sw=4:ts=4

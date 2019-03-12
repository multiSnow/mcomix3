''' Hyperrectangles. '''

from mcomix import tools


class Box(object):

    def __init__(self, position, size=None):
        ''' A Box is immutable and always axis-aligned.
        Each component of size should be positive (i.e. non-zero).
        Both position and size must have equal number of dimensions.
        If there is only one argument, it must be the size. In this case, the
        position is set to origin (i.e. all coordinates are 0) by definition.
        @param position: The position of this Box.
        @param size: The size of this Box.'''
        if size is None:
            self.position = (0,) * len(position)
            self.size = tuple(position)
        else:
            self.position = tuple(position)
            self.size = tuple(size)
        if len(self.position) != len(self.size):
            raise ValueError('different number of dimensions: ' +
                             str(len(self.position)) + ' != ' + str(len(self.size)))


    def __str__(self):
        ''' Returns a string representation of this Box. '''
        return '{' + str(self.get_position()) + ':' + str(self.get_size()) + '}'


    def __eq__(self, other):
        ''' Two Boxes are said to be equal if and only if the number of
        dimensions, the positions and the sizes of the two Boxes are equal,
        respectively. '''
        return (self.get_position() == other.get_position()) and \
            (self.get_size() == other.get_size())


    def __len__(self):
        ''' Returns the number of dimensions of this Box. '''
        return len(self.position)


    def get_size(self):
        ''' Returns the size of this Box.
        @return: The size of this Box. '''
        return self.size


    def get_position(self):
        ''' Returns the position of this Box.
        @return: The position of this Box. '''
        return self.position


    def set_position(self, position):
        ''' Returns a new Box that has the same size as this Box and the
        specified position.
        @return: A new Box as specified above. '''
        return Box(position, self.get_size())


    def set_size(self, size):
        ''' Returns a new Box that has the same position as this Box and the
        specified size.
        @return: A new Box as specified above. '''
        return Box(self.get_position(), size)


    def distance_point_squared(self, point):
        ''' Returns the square of the Euclidean distance between this Box and a
        point. If the point lies within the Box, this Box is said to have a
        distance of zero. Otherwise, the square of the Euclidean distance
        between point and the closest point of the Box is returned.
        @param point: The point of interest.
        @return The distance between the point and the Box as specified above.
        '''
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
        ''' Returns a new Box that has the same size as this Box and a
        translated position as specified by delta.
        @param delta: The distance to the position of this Box.
        @return: A new Box as specified above. '''
        return Box(tools.vector_add(self.get_position(), delta),
                   self.get_size())


    def translate_opposite(self, delta):
        ''' Returns a new Box that has the same size as this Box and a
        oppositely translated position as specified by delta.
        @param delta: The distance to the position of this Box, with opposite
        direction.
        @return: A new Box as specified above. '''
        return Box(tools.vector_sub(self.get_position(), delta),
                   self.get_size())


    @staticmethod
    def closest_boxes(point, boxes, orientation=None):
        ''' Returns the indices of the Boxes that are closest to the specified
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
        @return The indices of the closest Boxes as specified above. '''
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
        ''' Returns an integer that is less than, equal to or greater than zero
        if the distance between box1 and the origin is less than, equal to or
        greater than the distance between box2 and the origin, respectively.
        The origin is implied by orientation.
        @param box1: The first Box.
        @param box2: The second Box.
        @param orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading).
        @return An integer as specified above. '''
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
        ''' Returns the center of this Box. If the exact value is not equal to
        an integer, the integer that is closer to the origin (as implied by
        orientation) is chosen.
        @orientation: The orientation which shows where "forward" points
        to. Either 1 (towards larger values in this dimension when reading) or
        -1 (towards smaller values in this dimension when reading).
        @return The center of this Box as specified above. '''
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
        ''' Calculates the index of the Box that is closest to the center of
        this Box.
        @param orientation: The orientation to use.
        @param boxes: The Boxes to examine.
        @return: The index as specified above. '''
        return Box.closest_boxes(self.get_center(orientation), boxes,
            orientation)[0]


    @staticmethod
    def align_center(boxes, axis, fix, orientation):
        ''' Aligns Boxes so that the center of each Box appears on the same
        line.
        @param axis: the axis to center.
        @param fix: the index of the Box that should not move.
        @param orientation: The orientation to use.
        @return: A list of new Boxes with accordingly translated positions. '''
        if len(boxes) == 0:
            return []
        center_box = boxes[fix]
        cs = center_box.get_size()[axis]
        if cs % 2 != 0:
            cs +=1
        cp = center_box.get_position()[axis]
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
        ''' Ensures that the Boxes do not overlap. For this purpose, the Boxes
        are distributed according to the index of the respective Box.
        @param axis: the axis along which the Boxes are distributed.
        @param fix: the index of the Box that should not move.
        @param spacing: the number of additional pixels between Boxes.
        @return: A new list with new Boxes that are accordingly translated. '''
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
        partial_sum = initialSum
        for bi in range(fix - 1, -1, -1):
            b = boxes[bi]
            s = b.get_size()
            p = list(b.get_position())
            partial_sum -= s[axis] + spacing
            p[axis] = partial_sum
            result[bi] = Box(p, s)
        return result


    def wrapper_box(self, viewport_size, orientation):
        ''' Returns a Box that covers the same area that is covered by a
        scrollable viewport showing this Box.
        @param viewport_size: The size of the viewport.
        @param orientation: The orientation to use.
        @return: A Box as specified above. '''
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
        ''' Returns the union of all specified Boxes (that is, the smallest Box
        that contains all specified Boxes).
        @param boxes: The Boxes to calculate the union from.
        @return: A Box as specified above. '''
        if len(boxes) == 0:
            return Box((), ())
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
        return Box(mins, tools.vector_sub(maxes, mins))


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


# vim: expandtab:sw=4:ts=4

""" Smart scrolling. """

from mcomix import tools
import math


WESTERN_FORWARDS_ORIENTATION = [1, 1]
WESTERN_BACKWARDS_ORIENTATION = [-1, -1]
MANGA_FORWARDS_ORIENTATION = [-1, 1]
MANGA_BACKWARDS_ORIENTATION = [1, -1]

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



class SmartScrolling(object):

    def __init__(self, max_scroll):
        self.set_max_scroll(max_scroll)

    def set_max_scroll(self, max_scroll):
        """ Sets the portion of the viewport to scroll in one step.
        @param max_scroll: the portion of the viewport to scroll in one
        step. Must be a fraction greater than 0 and is usually not greater
        than 1. Note that this is actually a list of numbers similar to the
        params of the scroll function. """
        # Actually, this might go to the scroll function as well,
        # eliminating any fields and making scroll purely functional.
        self._max_scroll = max_scroll

    def scroll(self, content_size, viewport_size, viewport_position, orientation):
        """ Returns a new viewport_position when reading forwards using
        the given orientation. If there is no space left to go, the empty
        list is returned. Note that all params are lists of integers
        where each index corresponds to one dimension. The lower the index,
        the faster the corresponding position changes when reading.
        @param content_size: The size of the content to display.
        @param viewport_size: The size of the viewport we are looking through.
        @param viewport_position: The current position of the viewport,
        should be between 0 and content_size-viewport_size (inclusive).
        @param orientation: The orientation which shows where "forward"
        points to. Either 1 (towards greater values in this dimension when
        reading) or -1 (towards lesser values in this dimension when reading).
        Note that you can emulate "reading backwards" by flipping the sign
        of this argument.
        @return: A new viewport_position if you can read further or the
        empty list if there is nothing left to read. """

        # This code is somewhat similar to a simple ripple-carry adder.
        result = list(viewport_position)
        carry = True
        for i in range(len(content_size)):
            vs = viewport_size[i]
            invisible_size = content_size[i] - vs

            if invisible_size <= 0:
                # There is nothing to do in this dimension. Fast forward.
                continue

            # Let's calculate the grid we want to snap to.
            actual_increment = int(round(vs * self._max_scroll[i]))
            steps_to_take = invisible_size // actual_increment
            if invisible_size % actual_increment != 0:
                steps_to_take += 1
            positions = _bresenham_sums(invisible_size, steps_to_take) # TODO cache!

            o = orientation[i]
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
                result[i] = positions[0 if o > 0 else -1]
            else:
                # We found a valid grid point in this dimension, so let's
                # stop here.
                result[i] = positions[index]
                break
        if carry:
            # No space left.
            return []
        return result


# vim: expandtab:sw=4:ts=4

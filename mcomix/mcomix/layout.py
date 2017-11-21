""" Layout. """

from mcomix import constants
from mcomix import scrolling
from mcomix import tools
from mcomix import box


class FiniteLayout(object): # 2D only

    def __init__(self, content_sizes, viewport_size, orientation, spacing,
        wrap_individually, distribution_axis, alignment_axis):
        """ Lays out a finite number of Boxes along the first axis.
        @param content_sizes: The sizes of the Boxes to lay out.
        @param viewport_size: The size of the viewport.
        @param orientation: The orientation to use.
        @param spacing: Number of additional pixels between Boxes.
        @param wrap_individually: True if each content box should get its own
        wrapper box, False if the only wrapper box should be the union of all
        content boxes.
        @param distribution_axis: the axis along which the Boxes are distributed.
        @param alignment_axis: the axis to center. """
        self.scroller = scrolling.Scrolling()
        self.current_index = -1
        self.wrap_individually = wrap_individually
        self._reset(content_sizes, viewport_size, orientation, spacing,
            wrap_individually, distribution_axis, alignment_axis)


    def set_viewport_position(self, viewport_position):
        """ Moves the viewport to the specified position.
        @param viewport_position: The new viewport position. """
        self.viewport_box = self.viewport_box.set_position(viewport_position)
        self.dirty_current_index = True


    def scroll_smartly(self, max_scroll, backwards, axis_map, index=None):
        """ Applies a "smart scrolling" step to the current viewport position.
        If there are not enough Boxes to scroll to, the viewport is not moved
        and an appropriate value is returned.
        @param max_scroll: The maximum numbers of pixels to scroll in one step.
        @param backwards: True for backwards scrolling, False otherwise.
        @param axis_map: The index of the dimension to modify.
        @param index: The index of the Box the scrolling step is related to,
        or None to use the index of the current Box.
        @return: The index of the current Box after scrolling, or -1 if there
        were not enough Boxes to scroll backwards, or the number of Boxes if
        there were not enough Boxes to scroll forwards. """
        # TODO reconsider interface
        if (index == None) or (not self.wrap_individually):
            index = self.get_current_index()
        if not self.wrap_individually:
            wrapper_index = 0
        else:
            wrapper_index = index
        o = tools.vector_opposite(self.orientation) if backwards \
            else self.orientation
        new_pos = self.scroller.scroll_smartly(self.wrapper_boxes[wrapper_index],
            self.viewport_box, o, max_scroll, axis_map)
        if new_pos == []:
            if self.wrap_individually:
                index += -1 if backwards else 1
                n = len(self.get_content_boxes())
                if (index < n) and (index >= 0):
                    self.scroll_to_predefined(tools.vector_opposite(o), index)
                return index
            else:
                index = -1 if backwards else len(self.get_content_boxes())
                return index
        self.set_viewport_position(new_pos)
        return index


    def scroll_to_predefined(self, destination, index=None):
        """ Scrolls the viewport to a predefined destination.
        @param destination: An integer representing a predefined destination.
        Either 1 (towards the greatest possible values in this dimension),
        -1 (towards the smallest value in this dimension), 0 (keep position),
        SCROLL_TO_CENTER (scroll to the center of the content in this
        dimension), SCROLL_TO_START (scroll to where the content starts in this
        dimension) or SCROLL_TO_END (scroll to where the content ends in this
        dimension).
        @param index: The index of the Box the scrolling is related to, None to
        use the index of the current Box, or UNION_INDEX to use the union box
        instead. Note that the current implementation always uses the union box
        if self.wrap_individually is False. """
        if index == None:
            index = self.get_current_index()
        if not self.wrap_individually:
            index = constants.UNION_INDEX
        if index == constants.UNION_INDEX:
            current_box = self.union_box
        else:
            if index == constants.LAST_INDEX:
                index = len(self.content_boxes) - 1
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


    def set_orientation(self, orientation):
        self.orientation = orientation


    def _reset(self, content_sizes, viewport_size, orientation, spacing,
        wrap_individually, distribution_axis, alignment_axis):
        # reverse order if necessary
        if orientation[distribution_axis] == -1:
            content_sizes = tuple(reversed(content_sizes))
        temp_cb_list = tuple(map(box.Box, content_sizes))
        # align to center
        temp_cb_list = box.Box.align_center(temp_cb_list, alignment_axis, 0,
            orientation[alignment_axis])
        # distribute
        temp_cb_list = box.Box.distribute(temp_cb_list, distribution_axis, 0,
            spacing)
        if wrap_individually:
            temp_wb_list, temp_bb = FiniteLayout._wrap_individually(temp_cb_list,
                viewport_size, orientation)
        else:
            temp_wb_list, temp_bb = FiniteLayout._wrap_union(temp_cb_list,
                viewport_size, orientation)
        # move to global origin
        bbp = temp_bb.get_position()
        for i in range(len(temp_cb_list)):
            temp_cb_list[i] = temp_cb_list[i].translate_opposite(bbp)
        for i in range(len(temp_wb_list)):
            temp_wb_list[i] = temp_wb_list[i].translate_opposite(bbp)
        temp_bb = temp_bb.translate_opposite(bbp)
        # reverse order again, if necessary
        if orientation[distribution_axis] == -1:
            temp_cb_list = tuple(reversed(temp_cb_list))
            temp_wb_list = tuple(reversed(temp_wb_list))
        # done
        self.content_boxes = temp_cb_list
        self.wrapper_boxes = temp_wb_list
        self.union_box = temp_bb
        self.viewport_box = box.Box(viewport_size)
        self.orientation = orientation
        self.dirty_current_index = True


    @staticmethod
    def _wrap_individually(temp_cb_list, viewport_size, orientation):
        # calculate (potentially oversized) wrapper Boxes
        temp_wb_list = [None] * len(temp_cb_list)
        for i in range(len(temp_cb_list)):
            temp_wb_list[i] = temp_cb_list[i].wrapper_box(viewport_size,
                orientation)
        # calculate bounding Box
        temp_bb = box.Box.bounding_box(temp_wb_list)
        return (temp_wb_list, temp_bb)


    @staticmethod
    def _wrap_union(temp_cb_list, viewport_size, orientation):
        # calculate bounding Box
        temp_wb_list = [box.Box.bounding_box(temp_cb_list).wrapper_box(
            viewport_size, orientation)]
        return (temp_wb_list, temp_wb_list[0])


# vim: expandtab:sw=4:ts=4

# -*- coding: utf-8 -*-

""" Configuration tree view for the preferences dialog to edit keybindings. """

import gtk

from mcomix import keybindings


class KeybindingEditorWindow(gtk.ScrolledWindow):

    def __init__(self, keymanager):
        """ @param keymanager: KeybindingManager instance. """
        gtk.ScrolledWindow.__init__(self)
        self.set_border_width(5)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.keymanager = keymanager

        accel_column_num = max([
            len(self.keymanager.get_bindings_for_action(action))
            for action in keybindings.BINDING_INFO.keys()
        ])
        accel_column_num = self.accel_column_num = max([3, accel_column_num])

        # Human name, action name, true value, shortcut 1, shortcut 2, ...
        model = [str, str, 'gboolean']
        model.extend( [str, ] * accel_column_num)

        treestore = self.treestore = gtk.TreeStore(*model)

        section_order = list(set(d['group'] for d in keybindings.BINDING_INFO.values()))
        section_order.sort()
        section_parent_map = {}
        for section_name in section_order:
            row = [section_name, None, False]
            row.extend( [None,]*accel_column_num)
            section_parent_map[section_name] =  treestore.append(
                None, row
            )

        action_treeiter_map = self.action_treeiter_map = {}
        # Sort actions by action name
        actions = sorted(keybindings.BINDING_INFO.items(),
                key=lambda item: item[1]['title'])
        for action_name, action_data in actions:
            title = action_data['title']
            group_name = action_data['group']
            old_bindings = self.keymanager.get_bindings_for_action(action_name)
            acc_list =  ["", ] * accel_column_num
            for idx in range(0, accel_column_num):
                if len(old_bindings) > idx:
                    acc_list[idx] = gtk.accelerator_name(*old_bindings[idx])

            row = [title, action_name, True]
            row.extend(acc_list)
            treeiter = treestore.append(
                section_parent_map[group_name],
                row
            )
            action_treeiter_map[action_name] = treeiter
        
        treeview = gtk.TreeView(treestore)

        tvcol1 = gtk.TreeViewColumn(_("Name"))
        treeview.append_column(tvcol1)
        cell1 = gtk.CellRendererText()
        tvcol1.pack_start(cell1, True)
        tvcol1.set_attributes(cell1, text=0, editable=2)

        for idx in range(0, accel_column_num):
            tvc = gtk.TreeViewColumn(_("Key %d") % (idx +1))
            treeview.append_column(tvc)
            accel_cell = gtk.CellRendererAccel()
            accel_cell.connect("accel-edited", self.get_on_accel_edited(idx))
            accel_cell.connect("accel-cleared", self.get_on_accel_cleared(idx))
            tvc.pack_start(accel_cell, True)
            tvc.add_attribute(accel_cell, "text", 3 + idx)
            tvc.add_attribute(accel_cell, "editable", 2)

        # Allow sorting on the column
        tvcol1.set_sort_column_id(0)

        self.add_with_viewport(treeview)

    def get_on_accel_edited(self, column):
        def on_accel_edited(renderer, path, accel_key, accel_mods, hardware_keycode):
            iter = self.treestore.get_iter(path)
            col = column + 3  # accel cells start from 3 position
            old_accel = self.treestore.get(iter, col)[0]
            new_accel = gtk.accelerator_name(accel_key, accel_mods)
            self.treestore.set_value(iter, col, new_accel)
            action_name = self.treestore.get_value(iter, 1)
            affected_action = self.keymanager.edit_accel(action_name, new_accel, old_accel)

            # Find affected row and cell
            if affected_action == action_name:
                for idx in range(0, self.accel_column_num):
                    if idx != column and self.treestore.get(iter, idx + 3)[0] == new_accel:
                        self.treestore.set_value(iter, idx + 3, "")
            elif affected_action is not None:
                titer = self.action_treeiter_map[affected_action]
                for idx in range(0, self.accel_column_num):
                    if self.treestore.get(titer, idx + 3)[0] == new_accel:
                        self.treestore.set_value(titer, idx + 3, "")

            # updating gtk accelerator for label in menu
            if self.keymanager.get_bindings_for_action(action_name)[0] == (accel_key, accel_mods):
                gtk.accel_map_change_entry('<Actions>/mcomix-main/%s' % action_name,
                        accel_key, accel_mods, True)

        return on_accel_edited

    def get_on_accel_cleared(self, column):
        def on_accel_cleared(renderer, path, *args):
            iter = self.treestore.get_iter(path)
            col = column + 3
            accel = self.treestore.get(iter, col)[0]
            action_name = self.treestore.get_value(iter, 1)
            if accel != "":
                self.keymanager.clear_accel(action_name, accel)

                # updating gtk accelerator for label in menu
                if len(self.keymanager.get_bindings_for_action(action_name)) == 0:
                    gtk.accel_map_change_entry('<Actions>/mcomix-main/%s' % action_name, 0, 0, True)
                else:
                    key, mods  = self.keymanager.get_bindings_for_action(action_name)[0]
                    gtk.accel_map_change_entry('<Actions>/mcomix-main/%s' % action_name, key, mods, True)

            self.treestore.set_value(iter, col, "")
        return on_accel_cleared



# vim: expandtab:sw=4:ts=4

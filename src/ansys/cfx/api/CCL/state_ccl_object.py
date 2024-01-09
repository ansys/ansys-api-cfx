# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from . import ccl_utils


class StateCCLObject:
    """Class represents a CUE state CCL object."""

    def __init__(self, type: str, name: str, parent):
        self.parent: StateCCLObject = parent
        self.type: str = type
        self.name: str = name
        self.children: list[StateCCLObject] = []
        self.param_map: dict[str, str] = {}

    def exists(self) -> bool:
        return True

    def get_full_path(self) -> str:
        all_nodes = [self]
        parent = self.parent
        while parent and parent.exists():
            all_nodes.append(parent)
            parent = parent.parent

        all_nodes.reverse()

        type_name_list = []
        for node in all_nodes:
            type_name_list.append(ccl_utils.get_type_and_name_str(node.type, node.name))
        full_path = "/" + "/".join(type_name_list)

        return full_path

    def __str__(self) -> str:  # pragma: no cover
        indent_level = -1
        parent: StateCCLObject = self.parent
        while parent:
            indent_level += 1
            parent = parent.parent

        indent = "  " * indent_level
        type_name = ccl_utils.get_type_and_name_str(self.type, self.name)
        desc = indent + type_name + "\n"

        for p, v in self.param_map.items():
            desc += indent + "  " + p + " = " + v + "\n"

        for c in self.children:
            desc += str(c)

        desc += indent + "END\n"

        return desc

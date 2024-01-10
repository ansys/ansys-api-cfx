# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from io import StringIO
import re
from typing import Dict, List, NewType

from . import ccl_constants as ccl
from . import ccl_utils

CCLRulesObject = NewType("CCLRulesObject", None)  # type:ignore


class CCLRulesObject:
    """CCL Rules object representation.

    A CCL Rules object is defined in the following format

    PARAMETER: Parameter_Name
      Attribute = attribute_value
      ...
    END

    CONTEXT: Context_Name
      Attribute = attribute_value
      PARAMETER: ...
        ...
      END
      ...
    END

    OBJECT: Object_Type_Name
      Parameter_Name = parameter_value
      ...
      PARAMETER: ...
        ...
      END
      CONTEXT: ...
        ...
      END
      OBJECT: ...
        ...
      END
    END

    SINGLETON: Object_Type_Name
      Parameter_Name = parameter_value
      ...
    END

    OBJECT and SINGLETON type of CCL Rules objects can be nested
    and can contain context rules related to option parameter values.
    """

    child_contexts: List[CCLRulesObject]
    child_params: List[CCLRulesObject]
    children: List[CCLRulesObject]
    name: str
    parent: CCLRulesObject
    param_map: Dict[str, List[str]]
    type: str

    def __init__(self, type: str, name: str, parent):
        """Initialize the CCL Rules object."""
        self.type = type
        self.name = name
        self.parent = parent
        self.children = []
        self.child_contexts = []
        self.child_params = []
        self.param_map = {}

    def __str__(self) -> str:  # pragma: no cover
        """Return a printable form of the object."""
        indent_level = 0
        parent = self.parent
        while parent:
            indent_level += 1
            parent = parent.parent

        indent = "  " * indent_level
        type_name = ccl_utils.get_type_and_name_str(self.type, self.name)
        desc = indent + type_name + "\n"

        for p, v in self.param_map.items():
            desc += indent + "  " + p + " = " + ", ".join(v) + "\n"

        for c in self.children:
            desc += str(c)

        desc += indent + "END\n"

        return desc


class CCLRulesParser:
    """This class is for processing the CCL rules data.

    It parses CCL rules from the engine and generates a CCL rules object
    representation/template for all the defined CCL objects.
    """

    def __init__(self, ccl_rules: str):
        """Initialize the rules parser."""
        self.process(ccl_rules)

    def _reset(self, ccl_rules: str):
        self.ccl_source = StringIO(ccl_rules)
        self.root: CCLRulesObject = None
        self.current_node: CCLRulesObject = None

    def is_initialized(self) -> bool:
        """Return True if the object is initialized."""
        return self.root is not None

    def _readline(self) -> str:
        line = self.ccl_source.readline()
        if line and not ccl.RE_OBJECT_DEF_LINE_CONT.search(line):
            if comment_match := ccl.RE_LINE_WITH_TRAILING_COMMENT.match(line):
                line = comment_match.group(1).strip()
        return line

    def get_object_types_by_category(self, category: str) -> List[str]:
        """Return a list of all CCL object types by the given category defined in CCL Rules."""
        obj_list: list[str] = []

        nodes: list[CCLRulesObject] = [self.root]
        while nodes:
            node: CCLRulesObject = nodes.pop(0)
            if ccl.CATEGORY in node.param_map and category in node.param_map[ccl.CATEGORY]:
                obj_list.append(node.name)
            nodes = node.children + nodes

        return obj_list

    def get_object_type_list(self) -> List[str]:
        """Return a list of all CCL object types defined in CCL Rules."""
        if not self.is_initialized():
            return []

        obj_list: list[str] = []

        nodes: list[CCLRulesObject] = [self.root]
        while nodes:
            node: CCLRulesObject = nodes.pop(0)
            if node.type not in ("RULES", "PARAMETER", "CONTEXT"):
                obj_list.append(node.name)
            nodes = node.children + nodes

        return obj_list

    def get_object_definition(self, name: str) -> Dict[str, dict]:
        """Return a CCL Rules object definition."""
        if not self.is_initialized():
            return {}

        # internal params that that user can't change
        object_definition_param_list = [
            ccl.ALLOWED_OPTION_LIST,
            ccl.ALLOWED_PARENT_LIST,
            ccl.CATEGORY,
            ccl.CONTEXT_RULE,
            ccl.DESCRIPTION,
            ccl.ESSENTIAL_PARAMETER_LIST,
            ccl.INTERNAL_PARAMETER_LIST,
            ccl.OPTIONAL_PARAMETER_LIST,
        ]

        # params that may be overwritten by user
        object_data_param_list = [
            ccl.ESSENTIAL_PARAMETER_LIST,
            ccl.OPTIONAL_PARAMETER_LIST,
        ]

        object_definition_map: Dict[str, dict] = {}
        nodes: list[CCLRulesObject] = [self.root]
        while nodes:
            node = nodes.pop(0)
            if node.name == name:
                definition_map = {}
                for p in object_definition_param_list:
                    if p in node.param_map:
                        definition_map[p] = node.param_map[p]
                object_definition_map["definition_map"] = definition_map

                value_param_list = []
                for p in object_data_param_list:
                    if p in node.param_map:
                        value_param_list += node.param_map[p]

                # We also need to collect any parameter specified in the
                # context objects
                for child_context in node.child_contexts:
                    for p in object_data_param_list:
                        if p in child_context.param_map:
                            value_param_list += child_context.param_map[p]

                value_param_list = list(set(value_param_list))

                param_map = {}
                for i in value_param_list:
                    # take root object param definition first
                    for c in self.root.child_params:
                        if i == c.name:
                            param_map[i] = c.param_map
                            break

                    # overwrite param value with local default if available
                    for c in node.child_params:
                        if i == c.name:
                            if i in param_map:
                                param_map[i].update(c.param_map)
                            else:
                                param_map[i] = c.param_map
                            break

                object_definition_map["param_map"] = param_map

                context_map = {}
                for context in node.child_contexts:
                    context_map[context.name] = context.param_map
                    param_definition_map = {}
                    for context_child in context.children:
                        if context_child.type == "PARAMETER":
                            param_definition_map[context_child.name] = context_child.param_map
                    if param_definition_map:
                        context.param_map["_param_objects"] = param_definition_map

                object_definition_map["context_map"] = context_map

                break

            nodes = node.children + nodes

        return object_definition_map

    def process(self, ccl_rules: str) -> bool:
        """Process CCL rules to obtain all object definition info."""
        self._reset(ccl_rules)

        if not self.ccl_source.readable():
            return False

        while line := self._readline():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            line_match = ccl.RE_OBJECT_START_RULES.match(line)
            if line_match:
                obj_type = line_match.group(1).strip()
                obj_name = line_match.group(2)

                if obj_name:
                    obj_name = obj_name.strip()
                curr_obj = CCLRulesObject(obj_type, obj_name, self.current_node)

                if self.root is None:
                    self.root = curr_obj
                else:
                    self.current_node.children.append(curr_obj)

                if self.current_node:
                    if obj_type == "PARAMETER":
                        self.current_node.child_params.append(curr_obj)
                    elif obj_type == "CONTEXT":
                        self.current_node.child_contexts.append(curr_obj)

                self.current_node = curr_obj
                continue

            line_match = ccl.RE_OBJECT_END.match(line)
            if line_match:
                if self.current_node.parent is None:
                    return True

                self.current_node = self.current_node.parent
                continue

            line_match = ccl.RE_OBJECT_PARAM_DEF.match(line)
            if line_match:
                param_name = line_match.group(1).strip()
                param_value_str = line_match.group(2).strip()
                param_value_list = []

                while line_match := ccl.RE_OBJECT_DEF_LINE_CONT.search(param_value_str):
                    # Add values from each continuing line marked by
                    # a slash at the end of the line
                    param_value_str = line_match.group(1).strip()
                    param_value_list.append(param_value_str)
                    param_value_str = self._readline()
                else:
                    param_value_list.append(param_value_str.strip())

                param_value = re.split(r"\s*,\s*", " ".join(param_value_list))
                self.current_node.param_map[param_name] = param_value
                continue

        return False

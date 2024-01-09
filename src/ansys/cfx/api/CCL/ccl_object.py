# Copyright (c) 2024 ANSYS, Inc. All rights reserved
import re
from typing import Dict, List, NewType, Optional

from . import ccl_constants as ccl
from . import ccl_utils
from .object_db_service_interface import IObjectDBService
from .remote_engine_interface import IRemoteEngineInterface

_ccl_parameter_value_regex = re.compile(r"(.*?)(\[.*\])?\s*$")


class CCLParameter:
    """Object representing a CCL parameter definition."""

    name: str
    param_map: Dict[str, List[str]]

    def __init__(self, name: str, param_map: Dict[str, List[str]]):
        self.name = name
        self.param_map = param_map

    def get_value_as_list(self) -> List[str]:
        if ccl.DEFAULT in self.param_map:
            return self.param_map[ccl.DEFAULT]
        return []

    def get_value(self) -> Optional[str]:
        value_list = self.get_value_as_list()
        if value_list:
            return ", ".join(value_list)
        return None

    def __str__(self) -> str:
        desc = ccl.CCL_INDENT + "PARAMETER:" + self.name + "\n"
        for param_name, param_value in self.param_map.items():
            desc += ccl.CCL_INDENT * 2 + param_name + " = " + ", ".join(param_value) + "\n"
        desc += ccl.CCL_INDENT + "END\n"

        return desc


class CCLContext:
    """Object representing a CCL context definition."""

    def __init__(self, name: str, param_map):
        param_object_map = param_map.pop("_param_objects", None)

        self.name = name
        self.param_map = param_map
        self.param_object_map = {}

        if param_object_map:
            for param_name, param_def_map in param_object_map.items():
                self.param_object_map[param_name] = CCLParameter(param_name, param_def_map)

    def __str__(self) -> str:
        desc = ccl.CCL_INDENT + "CONTEXT:" + self.name + "\n"
        for param_name, param_value in self.param_map.items():
            desc += ccl.CCL_INDENT * 2 + param_name + " = " + ", ".join(param_value) + "\n"
        for param_object in self.param_object_map.values():
            param_desc = str(param_object).split("\n")
            for line in param_desc:
                desc += ccl.CCL_INDENT + line + "\n"
        desc += ccl.CCL_INDENT + "END\n"

        return desc


CCLObject = NewType("CCLObject", None)  # type:ignore


class CCLObject:
    """A class for querying and updating all objects that have a CCL
    representation. A CCLObject contains the name, the type, the
    parameters of the object and internal rules that govern object
    parameter settings.
    """

    _check_parameter_remote_type: bool
    _children: List[CCLObject]
    _context_map: Dict[str, CCLContext]
    _default_param_map: Dict[str, CCLParameter]
    _definition_map: Dict[str, dict]
    _engine_interface: IRemoteEngineInterface
    _is_valid: bool
    _name: str
    _object_db_access: Optional[IObjectDBService]
    _parents: List[str]
    _is_sub_object: bool
    _type: str
    _user_param_map: Dict[str, str]
    _user_param_map_local: Dict[str, str]

    def __init__(
        self,
        type: str,
        name: str,
        engine_interface: IRemoteEngineInterface,
        rule_object_definition_map: Dict[str, dict],
        state_object_param_map: Dict[str, str] = {},
        parents: List[str] = [],
        children: List[CCLObject] = [],
        is_sub_object: bool = False,
    ):
        self._setattr("_type", type)
        self._setattr("_name", name)
        self._setattr("_engine_interface", engine_interface)
        self._setattr("_object_db_access", None)
        self._setattr("_definition_map", rule_object_definition_map["definition_map"])
        self._setattr("_context_map", {})
        self._setattr("_default_param_map", {})
        self._setattr("_user_param_map", state_object_param_map)
        self._setattr("_parents", parents)
        self._setattr("_children", children)
        self._setattr("_is_sub_object", is_sub_object)
        # TODO: Default value must be set by the remote engine app
        self._setattr("_check_parameter_remote_type", True)
        self._setattr("_user_param_map_local", {})
        self._setattr("_is_valid", True)

        default_param_map = rule_object_definition_map["param_map"]
        for param_name, param_param_map in default_param_map.items():
            self._default_param_map[param_name] = CCLParameter(param_name, param_param_map)

        context_map = rule_object_definition_map["context_map"]
        for context_name, context_param_map in context_map.items():
            self._context_map[context_name] = CCLContext(context_name, context_param_map)

    def get_type(self) -> str:
        """Returns the type of the object."""
        return self._type

    def get_name(self) -> str:
        """Returns the name of the object."""
        return self._name

    def is_valid(self) -> bool:
        """Returns True if this object reference is valid, False otherwise."""
        return self._is_valid

    def get_parent_path(self) -> str:
        """Returns the path of the object's parent."""
        return "/" + "/".join(self._parents) if self._parents else ""

    def get_path(self) -> str:
        """Returns the path of the object."""
        type_name = ccl_utils.get_type_and_name_str(self._type, self._name)
        return self.get_parent_path() + "/" + type_name

    def get_child_objects(self) -> List[CCLObject]:
        """Returns the list of all child objects."""
        return self._children

    def is_a(self, category: str) -> bool:
        """Returns true if an object belongs to a specific category."""
        return category in self._definition_map["Category"]

    def _get_parameter_value_under_context(self, name: str) -> List[str]:
        """Returns parameter value as a list under current context option."""

        option = self.get_value(self.get_option_name())
        if option in self._context_map:
            context = self._context_map[option]
            if name in context.param_map:
                return context.param_map[name]
            if name in context.param_object_map:
                value_list = context.param_object_map[name].get_value_as_list()
                if value_list:
                    return value_list

        if name in self._definition_map:
            return self._definition_map[name]

        return []

    def get_optional_parameter_list(self) -> List[str]:
        """Returns optional parameter list under current context option."""
        return self._get_parameter_value_under_context(ccl.OPTIONAL_PARAMETER_LIST)

    def get_essential_parameter_list(self) -> List[str]:
        """Returns essential parameter list under current context option."""
        return self._get_parameter_value_under_context(ccl.ESSENTIAL_PARAMETER_LIST)

    def get_value(self, name: str) -> Optional[str]:
        """Returns the value of the parameter as a string."""

        if name in self._user_param_map_local:
            return self._user_param_map_local[name]

        if self._object_db_access:
            self._object_db_access.ensure_db_is_up_to_date()

        if name in self._user_param_map:
            return self._user_param_map[name]

        # Get default for the context if it is defined
        if name != self.get_option_name():
            context_defaut = self._get_parameter_value_under_context(name)
            if context_defaut:
                return ",".join(context_defaut)

        if name in self._default_param_map:
            return self._default_param_map[name].get_value()

        # Value does note exist. Note that parameter can have empty value
        return None

    def get_bool_value(self, name: str) -> bool:
        """Returns the value of the parameter as a boolean."""

        if not self.has_param(name):
            raise RuntimeError(f"Parameter '{name}' is not defined on the object.")

        param_type = self.get_param_type(name)
        if param_type != ccl.PARAMETER_TYPE_LOGICAL:
            raise RuntimeError(f"Parameter {name} (of type {param_type}) does not have bool value.")
        value = self.get_value(name).lower()

        if value in ccl.CCL_TRUE_VALUE_LIST:
            return True
        elif value in ccl.CCL_FALSE_VALUE_LIST:
            return False

        raise RuntimeError(f"Parameter {name} (of type boolean) cannot have value '{value}'.")

    def get_option_name(self) -> str:
        """Returns context option name for the object."""
        option_name = ccl.OPTION
        if ccl.CONTEXT_RULE in self._definition_map:
            context_option = self._definition_map[ccl.CONTEXT_RULE][0]
            if context_option:
                option_name = context_option
        return option_name

    def get_param_type(self, name: str) -> str:
        """Returns the type of the given parameter."""

        if not self.has_param(name):
            raise RuntimeError(f"Parameter '{name}' is not defined on the object.")

        # By the rules, parameter type is String if not specified.
        param_type = ccl.PARAMETER_TYPE_STRING
        if ccl.PARAMETER_TYPE in self._default_param_map[name].param_map:
            param_type = self._default_param_map[name].param_map[ccl.PARAMETER_TYPE][0]
        return param_type

    def reset(self):
        """Revert all local changes."""
        self._user_param_map_local.clear()

    def _set_value(self, name: str, value: str):
        self._user_param_map_local[name] = value

    def set_value(self, name: str, value: str):
        """Sets a given parameter to a given value."""

        if name == self.get_option_name():
            if value not in self.get_option_list():
                raise RuntimeError(f"Option '{value}' is not allowed.")
            self._set_value(name, value)
            return

        if not self.has_param(name):
            raise RuntimeError(f"Parameter '{name}' is not defined on the object.")

        if name in self._definition_map[ccl.INTERNAL_PARAMETER_LIST]:
            raise RuntimeError(f"Parameter '{name}' is internal. Modification is not allowed.")

        param_type = self.get_param_type(name)

        if not value or param_type == ccl.PARAMETER_TYPE_STRING:
            # Allow empty value and String type parameter pass
            self._set_value(name, value)
            return

        if param_type == ccl.PARAMETER_TYPE_LOGICAL:
            if value.lower() in (ccl.CCL_TRUE_VALUE_LIST + ccl.CCL_FALSE_VALUE_LIST):
                self._set_value(name, value)
                return
            else:
                raise RuntimeError(f"Parameter '{name}' must have value type '{param_type}'.")

        # Sanity check the given value if possible
        check_quantity = False
        if self._check_parameter_remote_type:
            check_quantity = True
            if ccl.REMOTE_TYPE in self._default_param_map[name].param_map:
                if (
                    self._default_param_map[name].param_map[ccl.REMOTE_TYPE][0]
                    == ccl.REMOTE_TYPE_EXPRESSION
                ):
                    check_quantity = False

        if check_quantity:
            # TODO: Do we have to check for integer parameter ?
            type_check_list = (ccl.PARAMETER_TYPE_REAL, ccl.PARAMETER_TYPE_INTEGER)
            if any(param_type.startswith(x) for x in type_check_list):
                for v in value.split(","):
                    v_numeric = v
                    value_unit_match = _ccl_parameter_value_regex.search(v)
                    if value_unit_match:
                        v_numeric = value_unit_match.group(1).strip()
                        try:
                            if ccl.PARAMETER_TYPE_REAL in param_type:
                                float(v_numeric)
                            elif ccl.PARAMETER_TYPE_INTEGER in param_type:
                                int(v_numeric)
                        except:
                            raise RuntimeError(
                                f"Parameter '{name}' must have value type '{param_type}'."
                            )

        self._set_value(name, value)

    def get_option_list(self) -> List[str]:
        """Returns a list of all options."""
        if ccl.ALLOWED_OPTION_LIST in self._definition_map:
            return self._definition_map[ccl.ALLOWED_OPTION_LIST]
        return []

    def set_option(self, value: str):
        """Selects a given option."""
        self.set_value(self.get_option_name(), value)

    def has_param(self, name: str) -> bool:
        """Returns true if the object has the specified parameter,
        false otherwise."""
        return bool(name in self._default_param_map)

    def get_param_names(self) -> List[str]:
        """Gets all parameter names of the object."""
        return self._default_param_map.keys()

    def get_state(self) -> str:
        """Returns the state of the object in CCL syntax."""
        indent_level = 0
        desc: str = ""
        for p in self._parents:
            if not self._is_sub_object:
                if ":" not in p:
                    p += ":"
                desc += ccl.CCL_INDENT * indent_level + p + "\n"
            indent_level += 1

        type_name = ccl_utils.get_type_and_name_str(self._type, self._name)
        if ":" not in type_name:
            type_name += ":"
        desc += ccl.CCL_INDENT * indent_level + type_name + "\n"
        indent_level += 1

        # _user_param_map_local - Parameters that are redefined by the client
        for param_name, param_value in self._user_param_map_local.items():
            desc += ccl.CCL_INDENT * indent_level + param_name + " = " + param_value + "\n"

        # _user_param_map - Parameters that have not been changed by the client
        for param_name, param_value in self._user_param_map.items():
            if param_name not in self._user_param_map_local:
                desc += ccl.CCL_INDENT * indent_level + param_name + " = " + param_value + "\n"

        # _default_param_map - Parameters that are missing from  both _user_param_map
        # and _user_param_map_local will take the default value defined by rules
        for param_name, param_object in self._default_param_map.items():
            if (
                param_name not in self._user_param_map
                and param_name not in self._user_param_map_local
            ):
                param_value = param_object.get_value()
                if param_value:
                    desc += ccl.CCL_INDENT * indent_level + param_name + " = " + param_value + "\n"

        for child in self._children:
            desc += str(child)

        indent_level -= 1
        if self._is_sub_object:
            desc += ccl.CCL_INDENT * indent_level + "END\n"
        else:
            while indent_level >= 0:
                desc += ccl.CCL_INDENT * indent_level + "END\n"
                indent_level -= 1

        return desc

    def get_rule_definition(self) -> str:
        """Returns the object definition by the rules in CCL syntax."""

        rule_type = "OBJECT"
        if not self.name or self._type == self.name:
            rule_type = "SINGLETON"
        type_name = ccl_utils.get_type_and_name_str(rule_type, self._type)
        desc = type_name + "\n"

        # _definition_map - Parameters related to internal object definitions,
        # i.e., Category
        for param_name, param_value_list in self._definition_map.items():
            desc += ccl.CCL_INDENT + param_name + " = " + ", ".join(param_value_list) + "\n"
        # _context_map - Table of context objects defined for this object
        for context_object in self._context_map.values():
            desc += "\n" + str(context_object)
        # _default_param_map - Table of parameter objects defined in this object
        for param_name, param_object in self._default_param_map.items():
            desc += "\n" + str(param_object)

        desc += "END\n"

        return desc

    def apply_state(self):
        """Applies object state to the Engine."""

        if not self.is_valid():
            raise RuntimeError(
                f"CCLObject::apply_state: This object is no longer valid and may have been deleted "
                "from the engine."
            )

        for p in self.get_essential_parameter_list():
            if not self.get_value(p):
                raise RuntimeError(
                    f"CCLObject::apply_state: Essential parameter '{p}' must be set."
                )

        if self._object_db_access:
            self._object_db_access.ensure_db_is_up_to_date()
        self._engine_interface.send_ccl(self.get_state())

        self._user_param_map_local.clear()

    def __setattr__(self, name, value):
        # Allow object content swapping to work - ref ccl_object_db
        if name == "__dict__":
            super().__setattr__(name, value)
            return
        raise AttributeError(name)

    # __setattr__ is overridden to prevent creation of new attributes or
    # overriding existing ones. _setattr is the backdoor to set attributes
    def _setattr(self, name, value):
        super().__setattr__(name, value)

    def __getattr__(self, name: str):
        """Allow controlled object attribute access."""
        PUBLIC_GET_ATTRIBUTE_LIST = ("_type", "_name")
        attr_name = "_" + name
        if attr_name in PUBLIC_GET_ATTRIBUTE_LIST:
            if hasattr(self, attr_name):
                return getattr(self, attr_name)
        raise AttributeError(name)

    def __call__(self) -> str:
        return self.get_state()

    def __str__(self) -> str:
        return self.get_state()

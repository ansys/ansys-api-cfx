# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from io import StringIO
import json
from types import SimpleNamespace
from typing import Dict, List, Optional
import weakref

from . import ccl_constants as ccl
from . import ccl_utils
from .ccl_change_observer_interface import ICCLChangeObserver
from .ccl_object import CCLObject
from .ccl_object_factory import CCLObjectFactory
from .object_db_service_interface import IObjectDBService
from .remote_engine_interface import IRemoteEngineInterface
from .state_ccl_object import StateCCLObject

_ccl_db = SimpleNamespace(
    CHANGED_OBJECTS="Changed Objects",
    DELETED_OBJECTS="Deleted Objects",
    NEW_OBJECTS="New Objects",
)


class ODBCCLObjectRoot(StateCCLObject):
    """
    This class serves as the root of CCL state tree.
    It allows us to take advantage of the recursive nature of
    the tree structure in ccl state parsing.
    """

    def __init__(self):
        super().__init__("_ROOT", "", None)

    def exists(self) -> bool:
        return False

    def __str__(self) -> str:
        desc = ""
        for c in self.children:
            desc += str(c)
        return desc


class CCLObjectDB(ICCLChangeObserver, IObjectDBService):
    """Database for managing CCL object for python client."""

    cached_objects: Dict[str, "weakref.ReferenceType[CCLObject]"]
    ccl_source: StringIO
    current_node: StateCCLObject
    engine_interface: IRemoteEngineInterface
    object_factory: CCLObjectFactory
    root: StateCCLObject
    ccl_change_record: Dict[str, set]
    db_is_up_to_date: bool

    def __init__(self, engine_interface: IRemoteEngineInterface):
        self.engine_interface = engine_interface
        self.cached_objects = weakref.WeakValueDictionary()
        self.object_factory = CCLObjectFactory(engine_interface)
        self.db_is_up_to_date = False
        self.engine_interface.register_ccl_change_observer(self)
        self.ccl_change_record = {}

    def _reset(self, ccl_state: str):
        self.ccl_source = StringIO(ccl_state)
        self.root = ODBCCLObjectRoot()
        self.current_node = self.root

    def _get_node_tree(self) -> List[StateCCLObject]:
        self.ensure_db_is_up_to_date()
        return [self.root]

    def ensure_db_is_up_to_date(self):
        if not self.db_is_up_to_date:
            self._sync_with_engine()

    def _sync_with_engine(self) -> bool:
        """Update database data including all existing user object data
        with new data from the Engine server."""

        if not self.update():
            return False

        # Update all cached objects with new data from the Engine
        for obj_path, obj_ref in self.cached_objects.items():
            node = self._get_object_node_by_path(obj_path)
            if node is None:
                continue

            new_obj = self.object_factory.create_object_with_user_state(node)
            new_obj._setattr("_object_db_access", self)
            if obj_ref._user_param_map_local:
                new_obj._setattr("_user_param_map_local", obj_ref._user_param_map_local)
            new_obj.__dict__, obj_ref.__dict__ = obj_ref.__dict__, new_obj.__dict__

        self.ccl_change_record = {}

        return True

    def _readline(self) -> str:
        line = self.ccl_source.readline()
        if line and not ccl.RE_OBJECT_DEF_LINE_CONT.search(line):
            if comment_match := ccl.RE_LINE_WITH_TRAILING_COMMENT.match(line):
                line = comment_match.group(1).strip()
        return line

    def has_object(self, path: str) -> bool:
        """Returns True if the given object path exists, otherwise False."""
        return self._get_object_node_by_path(path) is not None

    def generate_new_object_name(self, type: str, parent_path_or_name: Optional[str] = None) -> str:
        """Return a unique object name based on the given object type. For example, 'Plane 1'."""
        id: int = 0
        name_base = type.title()
        while True:
            id += 1
            name = name_base + " " + str(id)
            node = self._get_object_node_by_type_and_name(type, name, parent_path_or_name)
            if node is None:
                return name

    def create_new_object(self, type: str, name: str, parent_path: str) -> CCLObject:
        """Creates a new CCL object with default state. Throw if object of
        the given name and parent path already exists."""
        if self._get_object_node_by_type_and_name(type, name, parent_path):
            raise RuntimeError(
                f"Object already exists: type = {type}, name = {name}, parent = {parent_path}."
            )

        ccl_object = self.object_factory.create_object_with_default_state(type, name, parent_path)
        self._process_new_ccl_object(ccl_object)
        return ccl_object

    def get_objects_by_category(self, category: str) -> List[CCLObject]:
        """Returns a list of all objects by the given category."""
        obj_list = []
        nodes: List[StateCCLObject] = self._get_node_tree()
        object_types = self.object_factory.get_object_types_by_category(category)
        while nodes:
            node = nodes.pop(0)
            if node.exists():
                if node.type in object_types:
                    ccl_object = self._get_ccl_object(node)
                    obj_list.append(ccl_object)
            nodes = node.children + nodes

        return obj_list

    def get_objects_by_type(self, type: str) -> List[CCLObject]:
        """Returns a list of all objects by the given type."""
        obj_list = []
        nodes: List[StateCCLObject] = self._get_node_tree()
        while nodes:
            node = nodes.pop(0)
            if node.exists():
                if node.type == type:
                    ccl_object = self._get_ccl_object(node)
                    obj_list.append(ccl_object)
            nodes = node.children + nodes
        return obj_list

    def get_objects_by_name(self, name: str) -> List[CCLObject]:
        """Returns a list of all objects by the given name."""
        obj_list = []
        nodes: List[StateCCLObject] = self._get_node_tree()
        while nodes:
            node = nodes.pop(0)
            if node.exists():
                if node.name == name:
                    ccl_object = self._get_ccl_object(node)
                    obj_list.append(ccl_object)
            nodes = node.children + nodes

        return obj_list

    def get_object_by_path(self, path: str) -> Optional[CCLObject]:
        """Returns a CCLObject by the given path."""
        node = self._get_object_node_by_path(path)
        if node:
            return self._get_ccl_object(node)
        return None

    def get_object_by_path_and_name(
        self, parent_path_or_name: str, name: str
    ) -> Optional[CCLObject]:
        """Returns a CCLObject by the given parent path and name."""
        node = self._get_object_node_by_type_and_name(None, name, parent_path_or_name)
        if node:
            return self._get_ccl_object(node)
        return None

    def get_object_by_type_and_name(
        self, type: str, name: str, parent_path_or_name: Optional[str] = None
    ) -> Optional[CCLObject]:
        """Returns a CCLObject by the given type and name."""
        node = self._get_object_node_by_type_and_name(type, name, parent_path_or_name)
        if node:
            return self._get_ccl_object(node)
        return None

    def get_object_path_list(self) -> List[str]:
        """Returns a list of all object paths."""
        obj_list = []
        nodes: List[StateCCLObject] = self._get_node_tree()
        while nodes:
            node = nodes.pop(0)
            if node.exists():
                obj_list.append(node.get_full_path())
            nodes = node.children + nodes
        return obj_list

    def get_object_name_list(self) -> List[str]:
        """Returns a list of all objects in type:name pairs."""
        obj_list = []
        nodes: List[StateCCLObject] = self._get_node_tree()
        while nodes:
            node = nodes.pop(0)
            if node.exists():
                obj_type_name = ccl_utils.get_type_and_name_str(node.type, node.name)
                obj_list.append(obj_type_name)
            nodes = node.children + nodes

        return obj_list

    def _process_new_ccl_object(self, obj: CCLObject):
        obj._setattr("_object_db_access", self)
        self.cached_objects[obj.get_path()] = obj

    def _get_ccl_object(self, node: StateCCLObject) -> CCLObject:
        """Internal method for creating db ccl object."""
        full_path = node.get_full_path()
        if full_path in self.cached_objects:
            return self.cached_objects[full_path]
        else:
            ccl_object = self.object_factory.create_object_with_user_state(node)
            self._process_new_ccl_object(ccl_object)
            return ccl_object

    def _get_object_node_by_path(self, path: str) -> Optional[StateCCLObject]:
        nodes: List[StateCCLObject] = self._get_node_tree()
        while nodes:
            node = nodes.pop(0)
            if node.exists() and path == node.get_full_path():
                return node
            nodes = node.children + nodes

        return None

    def _get_object_node_by_type_and_name(
        self, type: Optional[str], name: str, parent_path: Optional[str]
    ) -> Optional[StateCCLObject]:
        """Internal method to find a tree node based on object type, name and parent."""

        nodes: List[StateCCLObject] = self._get_node_tree()
        while nodes:
            node = nodes.pop(0)
            if node.exists():
                check_type_name = True
                if parent_path and node.parent and node.parent.exists():
                    if "/" in parent_path:
                        if not parent_path == node.parent.get_full_path():
                            check_type_name = False
                    else:
                        if not (
                            parent_path == node.parent.name
                            or parent_path
                            == ccl_utils.get_type_and_name_str(node.parent.type, node.parent.name)
                        ):
                            check_type_name = False

                if check_type_name:
                    if type is None or type == node.type:
                        if node.name == name:
                            return node
            nodes = node.children + nodes

        return None

    def notify_ccl_changes(self, ccl_changes: str):
        """Processes CCL change notification from Engine."""
        data_map = json.loads(ccl_changes)
        for change_type, change_list in data_map.items():
            if change_type not in self.ccl_change_record:
                self.ccl_change_record[change_type] = set()
            for i in change_list:
                self.ccl_change_record[change_type].add(i)

        if _ccl_db.DELETED_OBJECTS in self.ccl_change_record:
            for obj_path, obj in self.cached_objects.items():
                if not obj:
                    continue
                if obj_path in self.ccl_change_record[_ccl_db.DELETED_OBJECTS]:
                    # Mark all deleted object invalid
                    obj._setattr("_is_valid", False)
            self.db_is_up_to_date = False
            return

        if not self.db_is_up_to_date:
            return

        if _ccl_db.NEW_OBJECTS in self.ccl_change_record:
            self.db_is_up_to_date = False
            return

        if _ccl_db.CHANGED_OBJECTS in self.ccl_change_record:
            for obj_path in self.cached_objects.keys():
                if obj_path in self.ccl_change_record[_ccl_db.CHANGED_OBJECTS]:
                    self.db_is_up_to_date = False
                    break

        return

    def update(self) -> bool:
        """Refreshes the database info with the current state of the Engine."""

        ccl_state = self.engine_interface.get_state()

        self._reset(ccl_state)

        if not self.ccl_source.readable():
            return False

        while line := self._readline():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            line_match = ccl.RE_OBJECT_START_STATE.search(line)
            if line_match:
                obj_type = line_match.group(1).strip()
                obj_name = line_match.group(2)

                if obj_name:
                    obj_name = obj_name.strip()
                curr_obj = StateCCLObject(obj_type, obj_name, self.current_node)

                self.current_node.children.append(curr_obj)
                self.current_node = curr_obj
                continue

            line_match = ccl.RE_OBJECT_END.search(line)
            if line_match:
                if self.current_node.parent is None:
                    return True

                self.current_node = self.current_node.parent
                continue

            line_match = ccl.RE_OBJECT_PARAM_DEF.search(line)
            if line_match:
                param_name = line_match.group(1).strip()
                param_value_str = line_match.group(2).strip()
                param_value_list = []

                while line_match := ccl.RE_OBJECT_DEF_LINE_CONT.match(param_value_str):
                    # Add values from each continuing line marked by
                    # a slash at the end of the line
                    param_value_str = line_match.group(1)
                    param_value_list.append(param_value_str)
                    param_value_str = self._readline()
                else:
                    param_value_list.append(param_value_str.strip())

                self.current_node.param_map[param_name] = "".join(param_value_list)
                continue

        # As the root node is virtual and contains no 'END' statement
        # We will check here to verify that we are back at the virtual root node
        # and has collected all children as expected
        self.db_is_up_to_date = (not self.current_node.exists()) and bool(
            self.current_node.children
        )

        return self.db_is_up_to_date

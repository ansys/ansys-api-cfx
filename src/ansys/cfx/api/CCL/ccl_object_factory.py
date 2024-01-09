# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from typing import List

from . import ccl_utils
from .ccl_object import CCLObject
from .ccl_rules_parser import CCLRulesParser
from .remote_engine_interface import IRemoteEngineInterface
from .state_ccl_object import StateCCLObject


class CCLObjectFactory:
    """Factory for generating python CCL object based on CCL rules and CUE engine state."""

    engine_interface: IRemoteEngineInterface
    object_list: List[str]
    rules_parser: CCLRulesParser

    def __init__(self, engine_interface: IRemoteEngineInterface):
        self._initialized = True
        self.engine_interface = engine_interface
        ccl_rules = self.engine_interface.get_rules()
        self.rules_parser = CCLRulesParser(ccl_rules)
        self.object_list: List[str] = []

    def get_object_type_list(self) -> List[str]:
        if not self.object_list:
            self.object_list = self.rules_parser.get_object_type_list()
        return self.object_list

    def get_object_types_by_category(self, category: str) -> List[str]:
        return self.rules_parser.get_object_types_by_category(category)

    def create_object_with_user_state(
        self, user_state: StateCCLObject, is_sub_object: bool = False
    ) -> CCLObject:
        """Create a new CCL object based on Rules and user state."""
        type = user_state.type
        name = user_state.name

        if type not in self.get_object_type_list():
            return None

        children: List[CCLObject] = []
        for c in user_state.children:
            child = self.create_object_with_user_state(c, True)
            if child:
                children.append(child)

        parents: List[str] = []

        parent = user_state.parent

        while parent is not None and parent.exists():
            type_name = ccl_utils.get_type_and_name_str(parent.type, parent.name)
            parents.append(type_name)
            parent = parent.parent

        parents.reverse()

        return CCLObject(
            type,
            name,
            self.engine_interface,
            self.rules_parser.get_object_definition(type),
            user_state.param_map,
            parents,
            children,
            is_sub_object,
        )

    def create_object_with_default_state(self, type: str, name: str, parent_path: str) -> CCLObject:
        """Create a new CCL object based on Rules with default settings."""
        if type not in self.get_object_type_list():
            return None

        parents = [i.strip() for i in parent_path.split("/") if i.strip()]
        user_state = {}

        return CCLObject(
            type,
            name,
            self.engine_interface,
            self.rules_parser.get_object_definition(type),
            user_state,
            parents,
        )

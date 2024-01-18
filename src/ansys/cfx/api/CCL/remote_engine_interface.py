# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""This module defines an interface for interacting with a CUE engine process."""

from abc import ABC, abstractmethod

from .ccl_change_observer_interface import ICCLChangeObserver


class IRemoteEngineInterface(ABC):
    """A pure interface for a CUE python client backend."""

    @abstractmethod
    def get_rules(self) -> str:
        """Get the CCL rules from the engine."""
        ...

    @abstractmethod
    def get_state(self) -> str:
        """Get the current CCL state from the engine."""
        ...

    @abstractmethod
    def register_ccl_change_observer(self, observer: ICCLChangeObserver):
        """Register an observer for CCL changes."""
        ...

    @abstractmethod
    def send_ccl(self, ccl: str) -> bool:
        """Send the CCL to the engine."""
        ...

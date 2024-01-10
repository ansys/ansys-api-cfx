# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from abc import ABC, abstractmethod


class ICCLChangeObserver(ABC):
    """Pure observer interface for CUE Engine server CCL changes."""

    @abstractmethod
    def notify_ccl_changes(self, ccl_changes: str):
        """Notify the class of any CCL changes."""
        ...

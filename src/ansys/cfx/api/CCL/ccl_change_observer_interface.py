# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from abc import ABC, abstractmethod


class ICCLChangeObserver(ABC):
    """Pure observer interface for CUE Engine server CCL Changes"""

    @abstractmethod
    def notify_ccl_changes(self, ccl_changes: str):
        ...

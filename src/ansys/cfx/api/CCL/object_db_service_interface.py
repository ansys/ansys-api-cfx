# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from abc import ABC, abstractmethod


class IObjectDBService(ABC):
    """Pure interface for accessing object database services."""

    @abstractmethod
    def ensure_db_is_up_to_date(self):
        """Ensure that the database is up-to-date."""
        ...

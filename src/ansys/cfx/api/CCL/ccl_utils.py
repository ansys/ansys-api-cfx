# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""This module contains some CCL handling utilities."""

from typing import Optional


def get_type_and_name_str(type: str, name: Optional[str]) -> str:
    """Combine the type and name of a CCL object into single string."""
    type_name = type
    if name:
        type_name += ":" + name
    return type_name

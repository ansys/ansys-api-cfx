# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from typing import Optional


def get_type_and_name_str(type: str, name: Optional[str]) -> str:
    type_name = type
    if name:
        type_name += ":" + name
    return type_name

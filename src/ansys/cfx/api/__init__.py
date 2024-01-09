# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""Provides a Python wrapper for the Ansys CFX API."""
import os
import pathlib

__all__ = ["__version__"]

with open(pathlib.Path(__file__).parent / "VERSION", encoding="utf-8") as f:
    __version__ = f.read().strip()

try:
    if os.getenv("PYCFX_DOC_ENGINE_CONNECTION_PRE") or os.getenv(
        "PYCFX_DOC_ENGINE_CONNECTION_POST"
    ):
        from ansys.cfx.api.help_utils import add_engine_functions_for_doc

        add_engine_functions_for_doc()
except Exception:
    pass

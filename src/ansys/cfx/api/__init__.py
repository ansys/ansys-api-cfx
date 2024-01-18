# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""Provides a Python wrapper for the Ansys CFX API."""

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__version__ = importlib_metadata.version(__name__.replace(".", "-"))

try:
    import os

    if os.getenv("PYCFX_DOC_ENGINE_CONNECTION_PRE") or os.getenv(
        "PYCFX_DOC_ENGINE_CONNECTION_POST"
    ):
        from ansys.cfx.api.help_utils import add_engine_functions_for_doc

        add_engine_functions_for_doc()
except Exception:
    pass

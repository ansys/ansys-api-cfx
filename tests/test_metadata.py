# Copyright (c) 2024 ANSYS, Inc. All rights reserved

from ansys.cfx.api import __version__


def test_pkg_version():
    assert __version__ == "0.1.dev0"

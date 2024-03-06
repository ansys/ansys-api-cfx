# Copyright (c) 2024 ANSYS, Inc. All rights reserved

import os
import socket
import time
from typing import Optional

import pytest

from ansys.cfx.api import pypost_core, pypre_core


def get_additional_args(debug_env: str) -> str:
    is_debug = os.getenv(debug_env)
    if is_debug == "1":
        additional_args = "-debug"
    else:
        additional_args = None
    return additional_args


def get_path_to_engine(
    app_versions: list,
    relative_path: str,
    app_name: str,
) -> str:
    path_to_engine: str = ""
    for version in app_versions:
        awp_root = os.environ.get("AWP_ROOT" + version)
        if awp_root:
            path_to_engine = os.path.join(awp_root, relative_path)
            break
    if not path_to_engine:
        raise RuntimeError(f"Path to {app_name} could not be determined")
    return path_to_engine


def get_additional_kw_args(local_root_env: str) -> Optional[dict]:
    local_root = os.getenv(local_root_env)
    if local_root:
        additional_kw_args = {"local-root": local_root}
    else:
        additional_kw_args = None
    return additional_kw_args


def get_str_value_from_env(env_var_name: str, default_value: str, required: bool = False) -> str:
    value = os.getenv(env_var_name)
    if not value:
        if required:
            print(os.environ)
            raise Exception(f"{env_var_name} must be defined in the environment.")
        else:
            value = default_value
    return value


def get_int_value_from_env(env_var_name: str, default_value: str, required: bool = False) -> int:
    str_val: str = get_str_value_from_env(env_var_name, default_value, required)
    int_val: int = int(str_val)
    return int_val


def get_enum_value_from_env(
    env_var_name: str, enum_type, default_value, valid_values_str: str, required: bool = False
):
    enum_value = get_str_value_from_env(env_var_name, default_value.name, required)
    try:
        enum_value = enum_type[enum_value]
    except KeyError:
        raise RuntimeError(
            f"Environment variable {env_var_name} was set to an invalid value '{enum_value}'. "
            "Valid values include {valid_values_str}."
        )
    return enum_value


def get_open_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # using '0' will tell the OS to pick a random port that is available.
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        # Shutdown is not needed because the socket is not connected.
        # Also, this will throw and error in windows
        # s.shutdown(socket.SHUT_RDWR)
        s.close()
    # Wait a second to let the OS do things
    time.sleep(1)
    return port


@pytest.fixture
def pypre() -> pypre_core.PyPre:
    pytest.socket_port = get_open_port()

    cfx_versions = ["242", "241"]
    try:
        path_to_cfx = get_path_to_engine(cfx_versions, "CFX/bin/cfx5pre", "cfx5pre")
    except RuntimeError:
        # PyPre and PyPost are not supported on 23.2 but PyTurboGrid is, so catch this one nicely.
        awp_root = os.environ.get("AWP_ROOT232")
        if awp_root:
            pytest.skip("Python access to CFX-Pre is not supported for Release 23.2")

    cfx_log_level = get_enum_value_from_env(
        "PYCFX_LOG_LEVEL",
        pypre_core.PyPre.ServerLogLevel,
        pypre_core.PyPre.ServerLogLevel.WARNING,
        "'DEBUG' and 'INFO'",
    )

    cfx_install_type = get_enum_value_from_env(
        "PYCFX_LOCATION_TYPE",
        pypre_core.PyPre.AppLocationType,
        pypre_core.PyPre.AppLocationType.APP_INSTALL,
        "'APP_INSTALL' and 'APP_RUNNING_CONTAINER'",
    )

    pypre = pypre_core.PyPre(
        socket_port=pytest.socket_port,
        server_location_type=cfx_install_type,
        cfxpre_location=path_to_cfx,
        log_level=cfx_log_level,
        additional_args_str=get_additional_args(debug_env="PYCFX_DEBUG"),
        additional_kw_args=get_additional_kw_args(local_root_env="PYCFX_CFX_LOCAL_ROOT"),
    )
    return pypre


@pytest.fixture
def pypost() -> pypost_core.PyPost:

    pytest.socket_port = get_open_port()

    cfx_versions = ["242", "241"]
    try:
        path_to_cfx = get_path_to_engine(cfx_versions, "CFX/bin/cfdpost", "cfdpost")
    except RuntimeError:
        # PyPre and PyPost are not supported on 23.2 but PyTurboGrid is, so catch this one nicely.
        awp_root = os.environ.get("AWP_ROOT232")
        if awp_root:
            pytest.skip("Python access to CFD-Post is not supported for Release 23.2")

    cfx_log_level = get_enum_value_from_env(
        "PYCFX_LOG_LEVEL",
        pypost_core.PyPost.ServerLogLevel,
        pypost_core.PyPost.ServerLogLevel.WARNING,
        "'DEBUG' and 'INFO'",
    )

    cfx_install_type = get_enum_value_from_env(
        "PYCFX_LOCATION_TYPE",
        pypost_core.PyPost.AppLocationType,
        pypost_core.PyPost.AppLocationType.APP_INSTALL,
        "'APP_INSTALL' and 'APP_RUNNING_CONTAINER'",
    )

    pypost = pypost_core.PyPost(
        socket_port=pytest.socket_port,
        server_location_type=cfx_install_type,
        cfdpost_location=path_to_cfx,
        log_level=cfx_log_level,
        additional_args_str=get_additional_args(debug_env="PYCFX_DEBUG"),
        additional_kw_args=get_additional_kw_args(local_root_env="PYCFX_CFX_LOCAL_ROOT"),
    )

    return pypost

# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""This module contains functionality for launching and communicating with CFD-Post."""

from enum import IntEnum
from typing import Optional

from ansys.cfx.api.cueengine_core import _CUEEngineInterface


class PyPost(_CUEEngineInterface):
    """This class controls of the launching, interactions and quitting of CFD-Post.

    Within the context of this object, it will be referred to as the 'client'.
    The CFD-Post session, and any peripherals of it, will be collectively called the 'server'.
    """

    class LocationType(IntEnum):
        """Specify how CFD-Post should be launched.

        Specify whether the PyPost class should launch CFD-Post from the given location, or
        connect to a running session of CFD-Post.
        :member-order: bysource
        """

        INSTALL = _CUEEngineInterface.AppLocationType.APP_INSTALL
        """ Launch CFD-Post from the given location."""
        RUNNING_CONTAINER = _CUEEngineInterface.AppLocationType.APP_RUNNING_CONTAINER
        """ Connect to a running session of CFD-Post using the given port."""
        ANSYS_LABS = _CUEEngineInterface.AppLocationType.APP_ANSYS_LABS
        """ Launch CFD-Post from within the Ansys Labs environment."""

    class LogLevel(IntEnum):
        """
        Controls which logging messages are reported.

        The higher values report the fewest messages.
        :member-order: bysource
        """

        CRITICAL = _CUEEngineInterface.ServerLogLevel.CRITICAL._value_
        """ Report critical errors only."""
        ERROR = _CUEEngineInterface.ServerLogLevel.ERROR._value_
        """ Report all errors."""
        WARNING = _CUEEngineInterface.ServerLogLevel.WARNING._value_
        """ Report all warnings and errors."""
        INFO = _CUEEngineInterface.ServerLogLevel.INFO._value_
        """ Report all information, warning and error messages."""
        NETWORK_DEBUG = _CUEEngineInterface.ServerLogLevel.NETWORK_DEBUG._value_
        """ Report extra information which should help with diagnosing connection errors."""
        DEBUG = _CUEEngineInterface.ServerLogLevel.DEBUG._value_
        """ Report the most detailed logging messages."""
        NOTSET = _CUEEngineInterface.ServerLogLevel.NOTSET._value_
        """ The log level has not been set; report all messages."""

    def __init__(
        self,
        socket_port: Optional[int],
        server_location_type: LocationType,
        cfdpost_location: str = "",
        additional_args_str: Optional[str] = None,
        additional_kw_args: Optional[dict] = None,
        log_level: LogLevel = LogLevel.INFO,
        host_ip: str = "127.0.0.1",
        pim_app_name: str = "",
        pim_app_ver: str = "241",
        log_filename_suffix: str = "",
    ):
        """Launch or connect to CFD-Post.

        Parameters
        ----------
        socket_port : int, default: ``None``
            Port for engine communications. The default is ``None``, in which case
            an available port is automatically selected.
        server_location_type : PyPost.LocationType
            Determines how CFD-Post will be accessed. Options are:
            - ``INSTALL``: Launch CFD-Post from the given location.
            - ``RUNNING_CONTAINER``: Connect to a running session of CFD-Post using the given port.
            - ``ANSYS_LABS``: Launch CFD-Post from within the Ansys Labs environment.
        cfdpost_location : str, default: ``""``
            Path to the ``cfdpost`` command for starting CFD-Post. Only used if the
            server_location_type is LocationType.INSTALL.
        additional_args_str : str, default: ``None``
            Additional arguments to send to CFD-Post.
        additional_kw_args : dict, default: ``None``
            Additional arguments to send to CFD-Post.
        log_level : PyPost.LogLevel, default: ``INFO``
            Level of logging information written to the terminal. The default is ``INFO``.
            Options are ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``, and ``DEBUG``.
            This setting does not affect the level of output that is written to the log files.
        host_ip: str, default: ``127.0.0.1``
            Host to connect to, for connecting to a running session of CFD-Post.
        pim_app_name: str, default: ``""``
            The application name needed for the Ansys Labs environment.
        pim_app_ver: str, default: ``241``,
            The application version needed for the Ansys Labs environment.
        log_filename_suffix: str, default: ``""``
            The suffix to use for the log files.
        """
        if server_location_type == self.LocationType.ANSYS_LABS:
            super().__init__(
                "CFD-Post",
                socket_port,
                _CUEEngineInterface.AppLocationType(int(server_location_type)),
                cfdpost_location,
                additional_args_str,
                additional_kw_args,
                _CUEEngineInterface.ServerLogLevel(int(log_level)),
                host_ip,
                pim_app_name,
                pim_app_ver,
                log_filename_suffix,
            )
        else:
            super().__init__(
                "CFD-Post",
                socket_port,
                _CUEEngineInterface.AppLocationType(int(server_location_type)),
                cfdpost_location,
                additional_args_str,
                additional_kw_args,
                _CUEEngineInterface.ServerLogLevel(int(log_level)),
                host_ip,
                "",
                "",
                log_filename_suffix,
            )

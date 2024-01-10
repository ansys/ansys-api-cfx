# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from enum import IntEnum
from typing import Optional

from ansys.cfx.api.cueengine_core import _CUEEngineInterface


class PyPre(_CUEEngineInterface):
    """This class controls of the launching, interactions and quitting of CFX-Pre.

    Within the context of this object, it will be referred to as the 'client'.
    The CFX-Pre session, and any peripherals of it, will be collectively called the 'server'.
    """

    class LocationType(IntEnum):
        """Specify how CFX-Pre should be launched.

        Specify whether the PyPre class should launch CFX-Pre from the given location, or
        connect to a running session of CFX-Pre.
        :member-order: bysource
        """

        INSTALL = _CUEEngineInterface.AppLocationType.APP_INSTALL
        """ Launch CFX-Pre from the given location."""
        RUNNING_CONTAINER = _CUEEngineInterface.AppLocationType.APP_RUNNING_CONTAINER
        """ Connect to a running session of CFX-Pre using the given port."""
        ANSYS_LABS = _CUEEngineInterface.AppLocationType.APP_ANSYS_LABS
        """ Launch CFX-Pre from within the Ansys Labs environment."""

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
        cfxpre_location: str = "",
        additional_args_str: Optional[str] = None,
        additional_kw_args: Optional[dict] = None,
        log_level: LogLevel = LogLevel.INFO,
        host_ip: str = "127.0.0.1",
        pim_app_name: str = "",
        pim_app_ver: str = "241",
        log_filename_suffix: str = "",
    ):
        """Launch or connect to CFX-Pre.

        Parameters
        ----------
        socket_port : int, default: ``None``
            Port for engine communications. The default is ``None``, in which case
            an available port is automatically selected.
        server_location_type : PyPre.LocationType
            Determines how CFX-Pre will be accessed. Options are:
            - ``INSTALL``: Launch CFX-Pre from the given location.
            - ``RUNNING_CONTAINER``: Connect to a running session of CFX-Pre using the given port.
            - ``ANSYS_LABS``: Launch CFX-Pre from within the Ansys Labs environment.
        cfxpre_location : str, default: ``""``
            Path to the ``cfx5pre`` command for starting CFX-Pre. Only used if the
            server_location_type is LocationType.INSTALL.
        additional_args_str : str, default: ``None``
            Additional arguments to send to CFX-Pre.
        additional_kw_args : dict, default: ``None``
            Additional arguments to send to CFX-Pre.
        log_level : PyPre.LogLevel, default: ``INFO``
            Level of logging information written to the terminal. The default is ``INFO``.
            Options are ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``, and ``DEBUG``.
            This setting does not affect the level of output that is written to the log files.
        host_ip: str, default: ``127.0.0.1``
            Host to connect to, for connecting to a running session of CFX-Pre.
        pim_app_name: str, default: ``""``
            The application name needed for the Ansys Labs environment.
        pim_app_ver: str, default: ``241``,
            The application version needed for the Ansys Labs environment.
        log_filename_suffix: str, default: ``""``
            The suffix to use for the log files.
        """
        if server_location_type == self.LocationType.ANSYS_LABS:
            super().__init__(
                "CFX-Pre",
                socket_port,
                _CUEEngineInterface.AppLocationType(int(server_location_type)),
                cfxpre_location,
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
                "CFX-Pre",
                socket_port,
                _CUEEngineInterface.AppLocationType(int(server_location_type)),
                cfxpre_location,
                additional_args_str,
                additional_kw_args,
                _CUEEngineInterface.ServerLogLevel(int(log_level)),
                host_ip,
                "",
                "",
                log_filename_suffix,
            )

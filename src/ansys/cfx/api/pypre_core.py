# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from typing import Optional

from ansys.cfx.api.cueengine_core import _CUEEngineInterface


class PyPre(_CUEEngineInterface):
    """
    This class controls of the launching, interactions and quitting of CFX-Pre.
    Within the context of this object, it will be referred to as the 'client'.
    The CFX-Pre session, and any peripherals of it, will be collectively called the 'server'.
    """

    def __init__(
        self,
        socket_port: Optional[int],
        server_location_type,
        cfxpre_location,
        additional_args_str: Optional[str],
        additional_kw_args: Optional[dict],
        log_level=_CUEEngineInterface.ServerLogLevel.INFO,
    ):
        super().__init__(
            "CFX-Pre",
            socket_port,
            _CUEEngineInterface.AppLocationType(int(server_location_type)),
            cfxpre_location,
            additional_args_str,
            additional_kw_args,
            _CUEEngineInterface.ServerLogLevel(int(log_level)),
        )

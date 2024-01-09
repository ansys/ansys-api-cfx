# Copyright (c) 2024 ANSYS, Inc. All rights reserved
from enum import IntEnum
import io
import os
import queue
import socket
import struct
import subprocess
import sys
import time
import types
from typing import Optional, Set
import weakref

from . import cueengine_read_messenger, cueengine_send_messenger
from .CCL.ccl_change_observer_interface import ICCLChangeObserver
from .CCL.remote_engine_interface import IRemoteEngineInterface


class _CUEEngineInterface(IRemoteEngineInterface):
    """
    This class controls the launching, interactions and quitting of TurboGrid, CFX-Pre or CFD-Post.
    """

    QUERY_ERROR_PREFIX = "ERROR:"  #: :meta private:

    class AppLocationType(IntEnum):
        """
        :meta private:
        """

        APP_INSTALL = 0
        APP_RUNNING_CONTAINER = 1
        APP_ANSYS_LABS = 2

    class ServerLogLevel(IntEnum):
        """
        :meta private:
        :member-order: bysource
        """

        CRITICAL = 50
        ERROR = 40
        WARNING = 30
        INFO = 20
        NETWORK_DEBUG = 15
        DEBUG = 10
        NOTSET = 0

    class DataDrivenUIStorage:
        """
        :meta private:
        """

        parentWR = None  #: :meta private:

        def __init__(self, parentWR):
            self.parentWR = parentWR

        def __del__(self):
            pass
            # print("DataDrivenUIStorage __del__")

        def queue_message(
            self,
            msg_type,
            msg,
        ):
            """
            :meta private:
            """
            self.parentWR().queue_message(msg_type, msg)

        def queue_message_with_response(
            self,
            msg_type,
            msg,
        ) -> str:
            """
            :meta private:
            """
            return self.parentWR().queue_message_with_response(msg_type, msg)

        def do_eval(self, result):
            """
            :meta private:
            """
            return self.parentWR().do_eval(result)

        def send_ccl(self, ccl):
            """
            :meta private:
            """
            self.parentWR().send_ccl(ccl)

    # The client-side socket object.
    client_socket: socket.socket = 0  #: :meta private:

    # The port to send to the server to connect to the client.
    proc_port: Optional[int] = None  #: :meta private:

    # Engine and its properties
    engine_proc: subprocess.Popen = 0  #: :meta private:

    # All of the engine console output will be written here
    console_log_file: io.TextIOWrapper = 0  #: :meta private:

    # All of the log messages for this clieant will be written here
    process_log_file: io.TextIOWrapper = 0  #: :meta private:

    # All of the communications going to the engine from this client will be written here
    outgoing_log_file: io.TextIOWrapper = 0  #: :meta private:

    # The log level to use for message reporting
    pyengine_log_level: ServerLogLevel = ServerLogLevel.INFO  #::meta private:

    log_filename_suffix: str = ""  #: :meta private:
    ##### Message Handling #####

    #: :meta private:
    read_message_process: cueengine_read_messenger.CUEEngineReadMessageService = 0

    run_read_message_process: bool = True  #: :meta private:
    engine_incoming_message_queue: queue = 0  #: :meta private: a queue of strings
    engine_incoming_error_queue: queue = 0  #: :meta private: a queue of strings

    #: :meta private:
    send_message_process: cueengine_send_messenger.CUEEngineSendMessageService = 0

    run_send_message_process: bool = True  #: :meta private:

    # A queue of string tuples (messageType, message)
    # engine_outgoing_message_queue: queue = 0  #: :meta private:

    engine_ready: bool = False  #: :meta private:
    engine_ccl_observers: Set[ICCLChangeObserver] = set()  #: :meta private:

    # This is currently a hidden parameter used to control blocking. As of now, it is for debug
    # purposes.
    block_each_message: bool = False  #: :meta private:

    # This can be modified away from 'localhost' in case a connection to another machine is desired.
    host_ip: str = "127.0.0.1"  #: :meta private:
    app_name = "App"  #: :meta private: Will be set by each application
    # This keeps track of the exit status, in case Python tries to lifetime manage
    # in a weird way.
    already_exited = False  #: :meta private:

    def __init__(
        self,
        app_name: str,
        socket_port: Optional[int],
        engine_location_type,
        app_location,
        additional_args_str: Optional[str],
        additional_kw_args: Optional[dict],
        log_level=ServerLogLevel.INFO,
        host_ip: str = "127.0.0.1",
        pim_app_name: str = None,
        pim_app_ver: str = None,
        log_filename_suffix: str = "",
    ):
        self.app_name = app_name
        self.host_ip = host_ip

        self.log_filename_suffix = log_filename_suffix

        self.pim_app_name = pim_app_name
        self.pim_app_ver = pim_app_ver

        if log_level:
            self.pyengine_log_level = log_level

        self.proc_port = socket_port
        self.init_connection_to_engine(
            engine_location_type,
            app_location,
            additional_args_str,
            additional_kw_args,
        )
        # Set up the read message process.
        # This process runs in a parallel thread and keeps track of whatever information the
        # engine is passing back.
        # For most commands, it will pass back a DONE, or an error descriptor.
        # Sending commands to the engine should wait for 'DONE' because if there is an error
        # returned instead, the next command may not be possible.
        self.engine_ready = False
        self.engine_incoming_message_queue = queue.Queue(1)  # a queue of strings
        self.engine_incoming_error_queue = queue.Queue()  # a queue of strings
        # self.engine_outgoing_message_queue = (
        #     queue.Queue()  # a queue of string tuples (messageType, message)
        # )
        self.read_message_process = cueengine_read_messenger.CUEEngineReadMessageService(
            weakref.ref(self)
        )
        self.read_message_process.daemon = True
        self.read_message_process.start()
        self.send_message_process = cueengine_send_messenger.CUEEngineSendMessageService(
            weakref.ref(self)
        )
        self.send_message_process.daemon = True
        self.send_message_process.start()

        # Finally, begin to self-program.
        # Store the data-driven methods in a sub-object so that Python's lifetime management works
        # as expected. If the methods are bound directly to this object, del, overwrite, and
        # quit (^z) do not work as expected.
        self.data_driven_storage = self.DataDrivenUIStorage(weakref.ref(self))
        self.query_functions()
        self.query_stubs()
        # We need to include some child members of 'self' to finalize to make sure these things
        # are not garbage collected ahead of time.
        weakref.finalize(
            self, _CUEEngineInterface.end_life, weakref.ref(self), self.data_driven_storage
        )

    @staticmethod
    def end_life(self_weak_ref, data_driven_storage):
        """
        :meta private:
        """
        # print(f"end_life {self_weak_ref=} {self_weak_ref()=}")
        # The weak ref will be 'None' if __del__ already ran.
        # Typically in scenarios where the object goes out of scope or gets deleted manually.
        # for terminal quit() scenarios, weak_ref will be valid.
        # print(
        #     f"end_life: {self_weak_ref()=} {self_weak_ref().already_exited=} "
        #     "{self_weak_ref().initialized=}"
        # )
        if self_weak_ref() == None:
            # Redundant end-of-life
            return

        if self_weak_ref().already_exited == False:
            connected: bool = False
            try:
                self_weak_ref().client_socket.getpeername()
                connected = True
            except socket.error as e:
                pass
            self_weak_ref().log_core(
                f"end_life {connected=}",
                self_weak_ref().ServerLogLevel.DEBUG,
            )
            if connected:
                self_weak_ref().quit()

            # Finally, clear out the data driven storage
            if data_driven_storage is not None:
                # Copy the item list because we can't delete items as we iterate
                # (RuntimeError: dictionary changed size during iteration)
                storage_items_copy = list(data_driven_storage.__dict__.items())
                for attr_name, attr_value in storage_items_copy:
                    if callable(attr_value) and attr_name not in dir(
                        _CUEEngineInterface.DataDrivenUIStorage
                    ):
                        delattr(data_driven_storage, attr_name)

    def __del__(self):
        # print(f"_CUEEngineInterface __del__")
        # Simply forward the call to the end_life method.
        if hasattr(self, "data_driven_storage"):
            _CUEEngineInterface.end_life(weakref.ref(self), self.data_driven_storage)
        else:
            _CUEEngineInterface.end_life(weakref.ref(self), None)

    # enter and exit are for when a context manager (with statement) is used
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass

    ####### INITIALIZATION ROUTINES #######
    def init_connection_to_engine(
        self,
        engine_location_type,
        app_location,
        additional_args_str,
        additional_kw_args,
    ):
        """
        :meta private:
        """
        self.process_log_file = open(
            self.app_name.replace("-", "")  # Remove any hyphen from the product name
            + "Log"
            + self.log_filename_suffix
            + ".txt",
            "w",
        )
        self.outgoing_log_file = open(
            f"PyClientOutgoing{self.log_filename_suffix}.txt",
            "w",
        )
        self.console_log_file = open(
            f"PyClientConsole{self.log_filename_suffix}.txt",
            "w",
        )
        self.log_core(
            f"Log file opened at {os.path.realpath(self.process_log_file.name)}",
            self.ServerLogLevel.DEBUG,
        )
        self.log_core(
            f"Log level set to {self.pyengine_log_level.name}",
            self.ServerLogLevel.NETWORK_DEBUG,
        )
        # Note that for a running container, self.proc_port must be specified
        if engine_location_type == _CUEEngineInterface.AppLocationType.APP_RUNNING_CONTAINER:
            if self.proc_port == None:
                raise self.ConnectionError(
                    "When connecting to a running container, the connection port must be specified."
                )
            self.ftp_ip = self.host_ip
            self.ftp_port = None  # In this scenario, the ftp port is contained somewhere else
        # When running in ansys labs mode, create the pim instance and get the host IP and port
        # from there. Also, in pim mode, we will have ftp_ip and ftp_host.
        # Note that the PIM product version is hardcoded for now.
        elif engine_location_type == _CUEEngineInterface.AppLocationType.APP_ANSYS_LABS:
            raise self.ConnectionError("The connection to Ansys Labs is not yet supported.")

        # Get a random open port if no port was specified
        if self.proc_port:
            try_port_number = self.proc_port
        else:
            try_port_number = self.get_open_port()

        if engine_location_type == _CUEEngineInterface.AppLocationType.APP_INSTALL:
            self.log_core(
                f"Launching: {app_location} on port {try_port_number}",
                self.ServerLogLevel.NETWORK_DEBUG,
            )
            args_list = []
            args_list.append(app_location)
            args_list.append("-py")
            args_list.append("-control-port")
            args_list.append(f"{try_port_number}")
            if additional_args_str:
                args_list.append(additional_args_str)
            if additional_kw_args:
                for key in additional_kw_args:
                    args_list.append(f"-{key}")
                    args_list.append(additional_kw_args[key])
            self.log_core(
                f"Launching: {app_location} with args {args_list}",
                self.ServerLogLevel.NETWORK_DEBUG,
            )
            self.engine_proc = subprocess.Popen(
                args_list,
                stdout=self.process_log_file,
                stderr=subprocess.STDOUT,
            )
            self.log_core(
                f"Finished launching",
                self.ServerLogLevel.NETWORK_DEBUG,
            )
        else:
            # In this scenario, the process has already been launched.
            # we do no process management here.
            self.log_core(
                f"-- {self.app_name} running container mode --",
                self.ServerLogLevel.NETWORK_DEBUG,
            )
            self.engine_proc = None

        self.client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.client_socket.setblocking(True)
        timeout_seconds = 5 * 1000
        # The entry for SO_RCVTIMEO is 8 or 16 bytes depending on the OS bit size.
        # If errors are thrown here because of bit mismatching, this may need to be extended.
        # We may want to limit this software for 64 bit python as the underlying software
        # would require a 64 bit OS to function.
        if sys.maxsize > 2**32:
            r_to = struct.pack(str("ll"), int(timeout_seconds), int(0))
        else:
            r_to = struct.pack(str("ii"), int(timeout_seconds), int(0))
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, r_to)
        self.log_core(
            f"Contacting {self.host_ip}",
            self.ServerLogLevel.NETWORK_DEBUG,
        )
        self.log_core(
            f"Waiting for {self.app_name} to accept...",
            self.ServerLogLevel.NETWORK_DEBUG,
        )
        wait_time_seconds = 5
        for i in range(wait_time_seconds):
            try:
                self.log_core(
                    f"Connection attempt {i} on port {try_port_number}",
                    self.ServerLogLevel.NETWORK_DEBUG,
                )
                self.client_socket.connect((self.host_ip, try_port_number))
                self.log_core(
                    f"Connection Succeeded on peer {self.client_socket.getpeername()}",
                    self.ServerLogLevel.NETWORK_DEBUG,
                )
                break
            except TimeoutError:
                if i < wait_time_seconds - 1:
                    self.log_core(
                        f"TimeoutError, Retrying after {i+1} attempts",
                        self.ServerLogLevel.NETWORK_DEBUG,
                    )
                    time.sleep(1)
                else:
                    self.log_core("Connection timeout.", self.ServerLogLevel.CRITICAL)
                    quit(100)
            except ConnectionRefusedError:
                if i < wait_time_seconds - 1:
                    self.log_core(
                        f"ConnectionRefusedError, Retrying after {i+1} attempts",
                        self.ServerLogLevel.NETWORK_DEBUG,
                    )
                    time.sleep(1)
                else:
                    self.log_core("Connection refused.", self.ServerLogLevel.CRITICAL)
                    quit(101)
                pass
            except ConnectionResetError:
                if i < wait_time_seconds - 1:
                    self.log_core(
                        f"ConnectionResetError, Retrying after {i+1} attempts",
                        self.ServerLogLevel.NETWORK_DEBUG,
                    )
                    time.sleep(1)
                else:
                    self.log_core("Connection refused.", self.ServerLogLevel.CRITICAL)
                    quit(102)
                pass
            except Exception as e:
                self.log_core(f"unidentified Error {e}", self.ServerLogLevel.CRITICAL)
                quit(103)

        self.log_core(
            f"connection established as client in port: {try_port_number}",
            self.ServerLogLevel.NETWORK_DEBUG,
        )

    def get_open_port(self):
        """
        :meta private:
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # using '0' will tell the OS to pick a random port that is available.
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port

    def get_hotfix_functions_dict(self):
        """
        :meta private:
        """
        return dict()

    ######## BASIC CLIENT FUNCTIONALITY #######
    def log_core(self, message, log_level):
        """
        :meta private:
        """
        if log_level.value >= self.pyengine_log_level.value:
            # print(message)
            self.console_log_file.write(message + "\n")
            self.console_log_file.flush()

    def set_log_level(self, log_level):
        """
        :meta private:
        """
        self.pyengine_log_level = log_level

    def wait_engine_ready(
        self,
    ):
        """
        :meta private:
        """
        self.log_core(
            f"wait_engine_ready with {self.app_name} status: {self.engine_ready}",
            self.ServerLogLevel.DEBUG,
        )
        while self.engine_ready == False:
            continue
        self.log_core(
            f"end of wait_engine_ready with {self.app_name} status: {self.engine_ready}",
            self.ServerLogLevel.DEBUG,
        )

    def wait_no_send_queue(
        self,
    ):
        """
        :meta private:
        """
        self.log_core(
            f"wait_no_send_queue with Q size: "
            "{self.send_message_process.engine_outgoing_message_queue.qsize()}",
            self.ServerLogLevel.DEBUG,
        )
        for elem in list(self.send_message_process.engine_outgoing_message_queue.queue):
            self.log_core(
                f"   {elem}",
                self.ServerLogLevel.DEBUG,
            )
        while self.send_message_process.engine_outgoing_message_queue.empty() == False:
            continue
        self.log_core(
            f"end of wait_no_send_queue with Q size: "
            "{self.send_message_process.engine_outgoing_message_queue.qsize()}",
            self.ServerLogLevel.DEBUG,
        )

    def queue_message(
        self,
        msg_type,
        msg,
    ):
        """
        :meta private:
        """
        if self.block_each_message:
            self.wait_no_send_queue()
            self.wait_engine_ready()
        self.send_message_process.engine_outgoing_message_queue.put(
            (
                msg_type,
                msg,
            )
        )
        if self.block_each_message:
            self.wait_no_send_queue()
            self.wait_engine_ready()

    # Certain messages (like QURY) come with responses.
    # This method will return the response string.
    # This method blocks so as to be sure not to read another response in the stream.
    def queue_message_with_response(
        self,
        msg_type,
        msg,
    ) -> str:
        """
        :meta private:
        """
        self.wait_no_send_queue()
        self.wait_engine_ready()
        self.send_message_process.engine_outgoing_message_queue.put(
            (
                msg_type,
                msg,
            )
        )
        response = (
            # get will block until a message is pushed here.
            self.engine_incoming_message_queue.get()
        )
        if self.block_each_message:
            self.wait_engine_ready()
            self.wait_no_send_queue()
        return response

    def query_functions(
        self,
    ) -> dict:
        """
        :meta private:
        """
        self.queue_message(
            "QURY",
            "Python Functions",
        )
        ######## set the attributes directly to the CUEEngineInterface class. ########
        #    MonkeyPatching is not a great design paradigm, but is effective for
        #    data-driven classes.
        #    Note: MethodType binds the function to the class
        #          so that 'self' is always passed in.
        # TODO: timeout and graceful exit if no response.
        backend_functions_dict = (
            # get will block until a message is pushed here.
            self.engine_incoming_message_queue.get()
        )

        functions_dict = eval(backend_functions_dict)

        for (
            key,
            value,
        ) in functions_dict.items():
            setattr(
                self.data_driven_storage,
                key,
                types.MethodType(
                    value,
                    self.data_driven_storage,
                ),
            )
            # Create a pointer of sorts to the storage method
            # This allows familiar syntax to be used but does not affect the reference count
            setattr(self, key, getattr(self.data_driven_storage, key))

        # Add all the hotfix functions. Some may overwrite the server's functions.
        command_file_version = self.get_version()
        self.log_core(
            f"command_file_version: {command_file_version}",
            self.ServerLogLevel.INFO,
        )

        hotfix_functions_dict = self.get_hotfix_functions_dict()
        if command_file_version in hotfix_functions_dict:
            self.log_core(
                f"Applying functionality patch: "
                "{command_file_version}:\n{hotfix_functions_dict[command_file_version]}",
                self.ServerLogLevel.DEBUG,
            )
            hotfix_dict = eval(hotfix_functions_dict[command_file_version])
            functions_dict.update(hotfix_dict)
            for (
                key,
                value,
            ) in hotfix_dict.items():
                setattr(
                    self,
                    key,
                    types.MethodType(
                        value,
                        self,
                    ),
                )
        else:
            self.log_core(
                f"No functionality patch available for version: {command_file_version}",
                self.ServerLogLevel.DEBUG,
            )

        return functions_dict

    def query_stubs(
        self,
    ):
        """
        :meta private:
        """
        self.queue_message(
            "QURY",
            "Python Stubs",
        )
        backend_stubs_list = (
            # get will block until a message is pushed here.
            self.engine_incoming_message_queue.get()
        )
        self.log_core(
            "backend_stubs_list:",
            self.ServerLogLevel.DEBUG,
        )
        for x in eval(backend_stubs_list):
            self.log_core(
                f"  stub: {x}",
                self.ServerLogLevel.DEBUG,
            )

    def query_doc_strings(
        self,
    ):
        """
        :meta private:
        """
        self.queue_message(
            "QURY",
            "Python Doc Strings",
        )
        doc_strings_str = (
            # get will block until a message is pushed here.
            self.engine_incoming_message_queue.get()
        )
        self.log_core(
            "doc_strings_str:",
            self.ServerLogLevel.DEBUG,
        )
        doc_strings_dict = eval(doc_strings_str)
        for key in doc_strings_dict.keys():
            value = doc_strings_dict[key]
            value = value.replace("<br>", "\n")
            value = value.replace("&apos;", '"')
            doc_strings_dict[key] = value
            self.log_core(
                f"  doc string: {key} ::: {value}",
                self.ServerLogLevel.DEBUG,
            )
        return doc_strings_dict

    def query_doc_annotations(
        self,
    ):
        """
        :meta private:
        """
        self.queue_message(
            "QURY",
            "Python Doc Annotations",
        )
        doc_strings_str = (
            # get will block until a message is pushed here.
            self.engine_incoming_message_queue.get()
        )
        self.log_core(
            "doc_strings_str:",
            self.ServerLogLevel.DEBUG,
        )
        return eval(doc_strings_str)

    def query_doc_defaults(
        self,
    ):
        """
        :meta private:
        """
        self.queue_message(
            "QURY",
            "Python Doc Defaults",
        )
        doc_strings_str = (
            # get will block until a message is pushed here.
            self.engine_incoming_message_queue.get()
        )
        self.log_core(
            "doc_strings_str:",
            self.ServerLogLevel.DEBUG,
        )
        return eval(doc_strings_str)

    def get_rules(self) -> str:
        """
        :meta private:
        """
        self.queue_message("QURY", "Engine Rules")
        return self.engine_incoming_message_queue.get()

    def get_state(self) -> str:
        """
        :meta private:
        """
        self.queue_message("QURY", "Engine State")
        return self.engine_incoming_message_queue.get()

    def get_app_version(self) -> str:
        """
        :meta private:
        """
        return ""

    def get_version(self) -> str:
        """
        Get the version of the application which is being run in the current session.

        Returns
        -------
        The application version e.g. '24.1'.
        """
        self.queue_message("QURY", "Engine Version")
        version = self.engine_incoming_message_queue.get()
        if not version.startswith(self.QUERY_ERROR_PREFIX):
            return version
        # Could be a version that doesn't support this query
        return self.get_app_version()

    def send_ccl(self, ccl: str) -> bool:
        """
        Send the provided CCL to the application.

        Parameters
        ----------
        ccl : str
            The CCL to send.
        """
        self.queue_message("PTSK", ccl)
        self.wait_no_send_queue()
        self.wait_engine_ready()
        return True

    def register_ccl_change_observer(self, observer: ICCLChangeObserver):
        """
        :meta private:
        """
        self.engine_ccl_observers.add(observer)

    def notify_ccl_changes(self, ccl_changes: str):
        """
        :meta private:
        """
        for observer in self.engine_ccl_observers:
            observer.notify_ccl_changes(ccl_changes)

    def quit(
        self,
    ):
        """
        Quit the application instance.
        """
        # print(
        #     f"quit: {self=} {self.already_exited=} {self.initialized=} {id(self.already_exited)=}"
        # )
        # Sometimes, we may call quit twice on the same object,
        # and there are weird scenarios with pytest as well.
        if self.already_exited:
            return
        # Before we can begin the shutdown sequence,
        # we queue a quit command and wait for the outgoing
        # queue to be empty, and for the engine to finish doing
        # whatever it's doing.
        # TODO: define more types of quit behaviors
        # We instruct the engine to quit nicely
        self.already_exited = True
        self.log_core(
            "QUITTING",
            self.ServerLogLevel.DEBUG,
        )
        self.queue_message(
            "QUIT",
            "",
        )
        self.wait_no_send_queue()
        # The engine will report a final ready before exiting
        self.wait_engine_ready()
        self.log_core(
            "QUITTING-> joining read message service",
            self.ServerLogLevel.DEBUG,
        )
        self.run_read_message_process = False
        self.read_message_process.join()
        self.log_core(
            "QUITTING-> joining send message service",
            self.ServerLogLevel.DEBUG,
        )
        self.run_send_message_process = False
        self.send_message_process.join()
        self.log_core(
            "QUITTING-> connection closed",
            self.ServerLogLevel.DEBUG,
        )
        self.log_core(
            "QUITTING-> waiting for process to terminate",
            self.ServerLogLevel.DEBUG,
        )
        if self.engine_proc != None:
            self.log_core(
                "QUITTING-> waiting for process to terminate",
                self.ServerLogLevel.DEBUG,
            )
            waitReturn = self.engine_proc.wait()
            self.log_core(
                f"  QUITTING-> waitReturn: {waitReturn}",
                self.ServerLogLevel.DEBUG,
            )
        self.log_core(
            f"{self.app_name} has shut down.",
            self.ServerLogLevel.INFO,
        )
        self.process_log_file.close()
        self.outgoing_log_file.close()
        self.console_log_file.close()
        self.client_socket.shutdown(socket.SHUT_RDWR)
        self.client_socket.close()

    class InvalidQuery(Exception):
        """
        :meta private:
        """

        def __init__(self, query, app_name):
            message = f'The "{query}" function is not available in this version of {app_name}.'
            super().__init__(message)

    class BadQueryResult(Exception):
        """
        :meta private:
        """

        def __init__(self, message):
            super().__init__(message)

    class ConnectionError(Exception):
        """
        :meta private:
        """

        def __init__(self, message):
            super().__init__(message)

    def handle_query_error(self, result):
        """
        :meta private:
        """
        if result.startswith(self.QUERY_ERROR_PREFIX):
            msg = result[len(self.QUERY_ERROR_PREFIX) :]
            raise self.BadQueryResult(msg)
        return result

    def do_eval(self, result):
        """
        :meta private:
        """
        result = self.handle_query_error(result)
        return eval(result)

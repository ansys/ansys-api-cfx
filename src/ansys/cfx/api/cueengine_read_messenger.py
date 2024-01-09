# Copyright (c) 2024 ANSYS, Inc. All rights reserved
import re
import socket
import sys
import threading


class CUEEngineReadMessageService(threading.Thread):
    cue_engine = 0

    def __init__(self, parent_object):
        # calling parent class constructor
        super().__init__()
        self.cue_engine = parent_object

    def __del__(self):
        pass
        # print(f"__del__ CUEEngineReadMessageService ")

    def log_read(self, message, log_level):
        self.cue_engine().log_core(message, log_level)

    def run(self):
        self.log_read(
            "read_message_process: read_message_process running...",
            self.cue_engine().ServerLogLevel.DEBUG,
        )
        # This service is (nicely) shut down by setting run_read_message_process to False and then
        # processing a message. The thread can be join()ed as well if need be.
        while self.cue_engine().run_read_message_process:
            # read command code and number of bytes.
            # The command code won't be used, but we could check it for validity.
            # self.log_read(
            #     f"read_message_process: Waiting on {self.cue_engine().app_name} for a message",
            #     self.cue_engine().ServerLogLevel.INFO,
            # )
            try:
                message_command_code: str = self.cue_engine().client_socket.recv(
                    10, socket.MSG_WAITALL
                )
                # This should never happen unless we have a blocking issue.
                # This is seen on github runners when the engine does not start up (for example,
                # a license problem) or when the engine crashes in some scenarios.
                # If a socket returns 0 bytes in this way, the other point will never send more
                # information back.
                if not message_command_code:
                    # Fatal Error
                    self.log_read(
                        f"read_message_process: FATAL: message_command_code should have read 10 "
                        "bytes but instead read {len(message_command_code)}",
                        self.cue_engine().ServerLogLevel.NETWORK_DEBUG,
                    )
                    # kill this thread process. Depending on the order of operations,
                    # the read messenger may quit this way. If the process leash is off,
                    # it is a normal exit.
                    if self.cue_engine().run_read_message_process == False:
                        self.log_read(
                            "Read Message Process Completed", self.cue_engine().ServerLogLevel.DEBUG
                        )
                    else:
                        self.log_read(
                            "Read Message Process Completed Abornmally!",
                            self.cue_engine().ServerLogLevel.DEBUG,
                        )
                    return

                # Process the message
                self.read_message_process(message_command_code)

            except socket.timeout as e:
                # self.log_read(
                #     f"read_message_process: socket timeout, sleeping",
                #     self.cue_engine().ServerLogLevel.INFO,
                # )
                pass
            # Before python 3.10, timeout errors on windows are raised as OSErrors with errno 10060
            except OSError as e:
                if e.errno == 10060:
                    # self.log_read(
                    #     f"read_message_process: socket timeout, sleeping",
                    #     self.cue_engine().ServerLogLevel.INFO,
                    # )
                    pass
                else:
                    raise

        # End of while loop, read_message_process thread is done.
        self.log_read("Read Message Process Completed", self.cue_engine().ServerLogLevel.DEBUG)

    def read_message_process(self, message_command_code):
        # we can check for t_message_pr
        #  code 'cueDataKey'
        message_header = self.cue_engine().client_socket.recv(4).decode("utf-8")
        self.log_read(
            f"read_message_process: Message Header: {message_header}",
            self.cue_engine().ServerLogLevel.DEBUG,
        )
        message_number_of_bytes = int.from_bytes(
            self.cue_engine().client_socket.recv(4, socket.MSG_WAITALL), byteorder="big"
        )
        self.log_read(
            f"read_message_process: Message NBytes: {message_number_of_bytes}",
            self.cue_engine().ServerLogLevel.DEBUG,
        )
        if message_header == "DONE":
            self.log_read(
                f"read_message_process: {self.cue_engine().app_name} Ready for the next command",
                self.cue_engine().ServerLogLevel.DEBUG,
            )
            if getattr(sys, "ps1", sys.flags.interactive):  # Interactive only
                self.log_read(
                    f"{self.cue_engine().app_name} is waiting for the next command",
                    self.cue_engine().ServerLogLevel.INFO,
                )
            self.cue_engine().engine_ready = True
        elif message_header == "ERRR":
            incoming_message = (
                self.cue_engine()
                .client_socket.recv(message_number_of_bytes, socket.MSG_WAITALL)
                .decode("utf-8")
            )
            self.cue_engine().engine_incoming_error_queue.put(incoming_message)
            self.log_read(
                f"read_message_process: {self.cue_engine().app_name} "
                "ERROR Response: {incoming_message}",
                self.cue_engine().ServerLogLevel.DEBUG,
            )
            self.log_read(
                f"{self.cue_engine().app_name} Error: {self.extract_error(incoming_message)}",
                self.cue_engine().ServerLogLevel.WARNING,
            )
            # For now, allow continuation of processing, because we don't have a way to pause other
            # operations to handle errors.
            # self.cue_engine.engine_ready = True
        elif message_header == "DBCH":
            # ObjectDB change notification from the engine
            incoming_message = (
                self.cue_engine()
                .client_socket.recv(message_number_of_bytes, socket.MSG_WAITALL)
                .decode("utf-8")
            )
            self.cue_engine().notify_ccl_changes(incoming_message)
            self.log_read(
                f"read_message_process: Engine CCL Change Notification: {incoming_message}",
                self.cue_engine().ServerLogLevel.DEBUG,
            )
            # self.cue_engine().engine_ready = True
        elif message_header == "RPLY":
            # Either wait for an empty buffer, or implement a thread-safe queue.
            incoming_message = (
                self.cue_engine()
                .client_socket.recv(message_number_of_bytes, socket.MSG_WAITALL)
                .decode("utf-8")
            )
            self.cue_engine().engine_incoming_message_queue.put(incoming_message)
            self.log_read(
                f"read_message_process: {self.cue_engine().app_name} "
                "Query Response: {incoming_message}",
                self.cue_engine().ServerLogLevel.DEBUG,
            )
        else:
            message_body = (
                self.cue_engine()
                .client_socket.recv(message_number_of_bytes, socket.MSG_WAITALL)
                .decode("utf-8")
            )

            self.log_read(
                f"read_message_process: {self.cue_engine().app_name} Not Ready. "
                "Reports: {message_body}",
                self.cue_engine().ServerLogLevel.DEBUG,
            )
        return

    def extract_error(self, message):
        # Engine sends errors in the form:
        # {  ClassMethod = <class>:<method>,  Message = <msg>,}
        # The <msg> string could contain newlines.
        pattern = r".*Message =\s+(?P<msg>.*),}"
        match = re.search(pattern, message, re.DOTALL)
        if match:
            return match.group("msg")
        return message

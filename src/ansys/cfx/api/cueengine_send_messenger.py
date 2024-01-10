# Copyright (c) 2024 ANSYS, Inc. All rights reserved
import queue
import threading


class CUEEngineSendMessageService(threading.Thread):
    """Class to handle sending messages from a CUE Engine."""

    cue_engine = 0
    engine_outgoing_message_queue: queue = 0  # a queue of string tuples (messageType, message)

    def __init__(self, parent_object):
        """Initialize the service."""
        # calling parent class constructor
        self.engine_outgoing_message_queue = (
            queue.Queue()  # a queue of string tuples (messageType, message)
        )
        super().__init__()
        self.cue_engine = parent_object

    def __del__(self):
        """Class destructor."""
        pass
        # print(f"__del__ CUEEngineSendMessageService ")

    def log_send(self, message, log_level):
        """Log the message to the log file if the log_level is high enough."""
        self.cue_engine().log_core(message, log_level)

    def run(self):
        """Run the service."""
        self.log_send(
            "send_message_process: send_message_process running...",
            self.cue_engine().ServerLogLevel.NETWORK_DEBUG,
        )
        # This service is (nicely) shut down by setting run_send_message_process to False and then
        # processing a message. The thread can be join()ed as well if need be.
        while self.cue_engine().run_send_message_process:
            # if self.cue_engine().engine_outgoing_message_queue.empty() == False:
            # wait for ENGINE to be ready. If there's an error instead, we cannot proceed.
            # self.cue_engine().wait_engine_ready()
            # TODO: Check status of ENGINE to continue
            try:
                # self.log_send(
                #     f"send_message_process: engine_outgoing_message_queue.get",
                #     self.cue_engine().ServerLogLevel.INFO,
                # )
                message = self.engine_outgoing_message_queue.get(timeout=5)
                self.log_send(
                    f"send_message_process: {message[0]} {message[1]}",
                    self.cue_engine().ServerLogLevel.DEBUG,
                )
                self.send_message(message[0], message[1])
            # except queue.Empty as e:
            except queue.Empty as e:
                # self.log_send(
                #     f"send_message_process: Queue empty, sleeping: {e=}",
                #     self.cue_engine().ServerLogLevel.INFO,
                # )
                pass
        # End of while loop, sendMessageProcess thread is done.
        self.log_send("Send Message Process Completed", self.cue_engine().ServerLogLevel.DEBUG)

    def send_message(self, message_type, message):
        """Send a message to the engine."""
        self.cue_engine().engine_ready = False
        cue_data_key = "cueDataKey"
        if message_type == "PTSK":
            message_body = "Parse CCL," + message
            outgoing_message_type = "PTSK"
        elif message_type == "QURY":
            message_body = message
            outgoing_message_type = "QURY"
        elif message_type == "QUIT":
            message_body = ""
            outgoing_message_type = "QUIT"
        else:
            message_body = ""
            outgoing_message_type = ""
        message_header = cue_data_key + outgoing_message_type
        self.log_send(
            f"Sending Message Type: {outgoing_message_type}",
            self.cue_engine().ServerLogLevel.DEBUG,
        )
        self.log_send(
            f"Sending Message Header: {message_header}", self.cue_engine().ServerLogLevel.DEBUG
        )
        self.log_send(
            f"Sending Message Body: {message_body}", self.cue_engine().ServerLogLevel.DEBUG
        )
        # every outgoing command is registered for replay in ENGINE's pysession mode.
        self.cue_engine().outgoing_log_file.write(outgoing_message_type + " " + message_body + "\n")
        self.cue_engine().outgoing_log_file.flush()
        self.cue_engine().client_socket.send(
            bytes(message_header, "utf-8")
            + len(message_body).to_bytes(4, byteorder="big")
            + bytes(message_body, "utf-8")
        )

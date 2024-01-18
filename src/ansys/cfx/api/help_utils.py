# Copyright (c) 2024 ANSYS, Inc. All rights reserved
"""This module contains utilities relating to documentation builds."""

from ansys.cfx.api import pypost_core, pypre_core


def add_engine_functions_for_doc():
    """Patch the PyPre and/or PyPost classes with function definitions from the related engine.

    Only intended for use during a documentation build under the GitHub workflows.
    """
    try:
        import os

        import sphinx

        sphinx_build = hasattr(sphinx, "application")
        if not sphinx_build:
            return

        pre_socket_port = os.getenv("PYCFX_DOC_ENGINE_CONNECTION_PRE")
        if pre_socket_port is not None:
            pre_socket_port = int(pre_socket_port)

            print(f"Connecting to CFX-Pre to get engine function documentation")

            pre = pypre_core.PyPre(
                socket_port=pre_socket_port,
                server_location_type=pypre_core.PyPre.AppLocationType.APP_RUNNING_CONTAINER,
                cfxpre_location="",
                log_level=pypre_core.PyPre.ServerLogLevel.DEBUG,
                additional_args_str="",
                additional_kw_args={},
            )

            functions = pre.query_functions()
            doc_strings = pre.query_doc_strings()
            doc_annotations = pre.query_doc_annotations()
            doc_defaults = pre.query_doc_defaults()

            pre.quit()

            for key, value in functions.items():
                tmp_func = value
                if key in doc_strings:
                    tmp_func.__doc__ = doc_strings[key]
                else:
                    continue
                if key in doc_annotations:
                    tmp_func.__annotations__ = doc_annotations[key]
                if key in doc_defaults:
                    tmp_func.__defaults__ = doc_defaults[key]
                setattr(pypre_core.PyPre, key, tmp_func)

        post_socket_port = os.getenv("PYCFX_DOC_ENGINE_CONNECTION_POST")
        if post_socket_port is not None:
            post_socket_port = int(post_socket_port)

            print(f"Connecting to CFD-Post to get engine function documentation")

            post = pypost_core.PyPost(
                socket_port=post_socket_port,
                server_location_type=pypost_core.PyPost.AppLocationType.APP_RUNNING_CONTAINER,
                cfdpost_location="",
                log_level=pypost_core.Pypost.ServerLogLevel.DEBUG,
                additional_args_str="",
                additional_kw_args={},
            )

            functions = post.query_functions()
            doc_strings = post.query_doc_strings()
            doc_annotations = post.query_doc_annotations()
            doc_defaults = post.query_doc_defaults()

            post.quit()

            for key, value in functions.items():
                tmp_func = value
                if key in doc_strings:
                    tmp_func.__doc__ = doc_strings[key]
                else:
                    continue
                if key in doc_annotations:
                    tmp_func.__annotations__ = doc_annotations[key]
                if key in doc_defaults:
                    tmp_func.__defaults__ = doc_defaults[key]
                setattr(pypost_core.PyPost, key, tmp_func)

    except Exception as e:
        pass

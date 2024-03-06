# Copyright (c) 2024 ANSYS, Inc. All rights reserved
# To run these tests, navigate your terminal to the root of this project (ansys-api-turbogrid)
# and use the command pytest -v. -s can be added as well to see all of the console output.

import os
from pathlib import Path

from ansys.cfx.api import pypost_core
from ansys.cfx.api.CCL.ccl_object import CCLObject
from ansys.cfx.api.CCL.ccl_object_db import CCLObjectDB
from ansys.cfx.api.CCL.ccl_object_factory import CCLObjectFactory


def test_post_client_startup(pypost: pypost_core.PyPost):
    # Just shut down, we are only testing if the connection can be established.
    pypost.quit()


def test_post_basic(pypost: pypost_core.PyPost):
    pypost.block_each_message = True

    pypost.read_case(filename="tests/data/StaticMixer.def")

    ccl_str = """POINT: Point 1
                   Option = XYZ
                   Point = 0 [m], 0 [m], 0 [m]
                 END"""
    pypost.send_ccl(ccl_str)

    session_file = "StaticMixerPostTest.cse"
    pypost.start_session(filename=session_file)

    # This won't do anything but it tests that the function exists with an appropriate argument
    pypost.change_timestep(-1)

    pypost.hide_objects("/POINT:Point 1")
    pypost.show_objects("/POINT:Point 1")

    image_file = "StaticMixerPostTest.png"
    pypost.save_image(filename=image_file, format="png")
    path = Path(image_file)
    assert path.is_file()
    os.remove(path)

    pypost.end_session()
    path = Path(session_file)
    assert path.is_file()
    os.remove(path)

    pypost.quit()


def test_post_state_and_ccl(pypost: pypost_core.PyPost):
    pypost.block_each_message = True

    pypost.read_state(filename="tests/data/StaticMixer.cst", load_results=True)

    object_db = CCLObjectDB(pypost)
    obj_list = object_db.get_objects_by_type("BOUNDARY")
    assert len(obj_list) == 4

    boundary1: CCLObject = object_db.get_object_by_path(
        "/DATA READER/CASE:Case StaticMixer/BOUNDARY:in1"
    )
    assert boundary1 is not None

    object_factory = CCLObjectFactory(pypost)
    point1 = object_factory.create_object_with_default_state("POINT", "Origin Point", "/")
    point1.set_option("XYZ")
    point1.set_value("Point", "0.1,0.2,1")
    point1.apply_state()

    ccl_str = """EXPORT:
                   CSV Type = CSV
                   Case Name = Case StaticMixer
                   Export File = StaticMixerPostTest.csv
                   Export Geometry = On
                   Export Type = Generic
                   Include File Information = Off
                   Include Header = On
                   Location = in1, /POINT:Origin Point
                   Location List = in1, /POINT:Origin Point
                   Overwrite = On
                   Variable List = X, Y, Z
                 END"""
    pypost.send_ccl(ccl_str)

    pypost.perform_action(task="export", arg_string="")
    path = Path("StaticMixerPostTest.csv")
    assert path.is_file()
    os.remove(path)

    pypost.quit()


def test_post_session(pypost: pypost_core.PyPost):
    pypost.block_each_message = True

    pypost.read_session(filename="tests/data/StaticMixer.cse")
    exported_file = "StaticMixerPostTest2.csv"
    path = Path(exported_file)
    assert path.is_file()
    os.remove(path)

    state_file = "StaticMixerPostTest.cst"
    pypost.save_state(filename=state_file)
    path = Path(state_file)
    assert path.is_file()
    os.remove(path)

    pypost.quit()

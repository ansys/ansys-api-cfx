# Copyright (c) 2024 ANSYS, Inc. All rights reserved
# To run these tests, navigate your terminal to the root of this project (ansys-api-turbogrid)
# and use the command pytest -v. -s can be added as well to see all of the console output.


from ansys.cfx.api import pypre_core
import os
from pathlib import Path
import shutil


def test_pre_client_startup(pypre: pypre_core.PyPre):
    # Just shut down, we are only testing if the connection can be established.
    pypre.quit()


def test_pre_basic(pypre: pypre_core.PyPre):

    pypre.block_each_message = True

    pypre.read_case(filename="tests/data/StaticMixer.cfx")

    ccl_str = """FLOW: Flow Analysis 1
                   DOMAIN: Default Domain
                     BOUNDARY: in1
                       BOUNDARY CONDITIONS:
                         MASS AND MOMENTUM:
                           Normal Speed = 22 [m s^-1]
                         END
                       END
                     END
                   END
                 END"""
    pypre.send_ccl(ccl_str)

    case_file = "StaticMixerPreTest.cfx"
    pypre.save_case(filename=case_file)
    path = Path(case_file)
    assert path.is_file()
    os.remove(path)

    state_file = "StaticMixerPreTest.ccl"
    pypre.save_state(filename=state_file)
    path = Path(state_file)
    assert path.is_file()
    os.remove(path)

    solver_file = "StaticMixerPreTest.def"
    pypre.write_solver_file(solver_file)
    path = Path(solver_file)
    assert path.is_file()
    os.remove(path)

    pypre.quit()


def test_pre_state(pypre: pypre_core.PyPre):

    pypre.block_each_message = True

    pypre.new_case()

    pypre.import_mesh(filename="tests/data/StaticMixer.def")

    pypre.read_state(filename="tests/data/StaticMixerPre.ccl")

    image_file = "StaticMixerPreTest.png"
    pypre.save_image(filename=image_file, format="png")
    path = Path(image_file)
    assert path.is_file()
    os.remove(path)

    pypre.quit()


def test_pre_session(pypre: pypre_core.PyPre):

    pypre.block_each_message = True

    pypre.read_session(filename="tests/data/StaticMixer.pre")
    mdef_file = "StaticMixerPreTest.mdef"
    path = Path(mdef_file)
    assert path.is_file()
    os.remove(path)
    mdef_dir = "StaticMixerPreTest"
    path = Path(mdef_dir)
    assert path.is_dir()
    shutil.rmtree(mdef_dir)

    session_file = "StaticMixerTest.pre"
    pypre.start_session(filename=session_file)
    pypre.close_case()
    pypre.end_session()
    path = Path(session_file)
    assert path.is_file()
    os.remove(path)

    pypre.quit()

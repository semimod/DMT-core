""" Tests all known cases for clean_names

"""
import os
import logging

from DMT.exceptions import UnknownColumnError
from DMT.core.dut_type import DutType
from DMT.core.naming import get_nodes

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s - %(message)s",
    filename=os.path.join("logs", "test_get_nodes.log"),
    filemode="w",
)


def test_get_nodes_teledyne():

    nodes_tlm = DutType.tlm.get_nodes()
    fallback_tlm = {"L": "L", "S": "R", "M": "M", "LI": "", "SI": "", "C": ""}
    # vli             vc              vm              vl              vs              il              ic              is
    cols_tlm = ["V_LI", "V_C", "V_M", "V_L", "V_S", "I_L", "I_C", "I_S"]
    cols_dmt_tlm = ["V_LI", "V_C", "V_M", "V_L", "V_R", "I_L", "I_C", "I_R"]
    call_get_nodes(cols_tlm, nodes_tlm, fallback_tlm, cols_dmt_tlm)

    nodes_tetrode = DutType.tetrode.get_nodes()
    fallback_tetrode = {"B1_": "B1", "B2_": "B2", "C_": "C", "E_": "E"}
    # ve              ib1_            vb1_            ib2_            vb2_            ic_             ie_
    cols_tetrode = ["V_E", "I_B1_", "V_B1_", "I_B2_", "V_B2_", "I_C_", "I_E_"]
    cols_dmt_tetrode = ["V_E", "I_B1", "V_B1", "I_B2", "V_B2", "I_C", "I_E"]
    call_get_nodes(cols_tetrode, nodes_tetrode, fallback_tetrode, cols_dmt_tetrode)

    nodes_bjt = DutType.bjt.get_nodes()
    fallback_bjt = {}
    # vb              vc              ic              ib
    # ICCAP_VAR vs         0              ICCAP_VAR ve         0              ICCAP_VAR vc         0.35           ICCAP_VAR vb         0.6
    cols_bjt = ["V_B", "V_C", "I_C", "I_B", "V_S", "V_E", "V_C", "V_B"]
    cols_dmt_bjt = ["V_B", "V_C", "I_C", "I_B", "V_S", "V_E", "V_C", "V_B"]
    call_get_nodes(cols_bjt, nodes_bjt, fallback_bjt, cols_dmt_bjt)

    # oder : ICCAP_VAR ve         0              ICCAP_VAR vs         0              ICCAP_VAR vbe        0.8            ICCAP_VAR vc         0.8
    cols_bjt = ["V_E", "V_S", "V_BE", "V_C"]
    cols_dmt_bjt = ["V_E", "V_S", "V_BE", "V_C"]
    call_get_nodes(cols_bjt, nodes_bjt, fallback_bjt, cols_dmt_bjt)


def test_get_nodes_DotSeven():

    nodes_tlm = DutType.tlm.get_nodes()
    fallback_tlm = {"S1": "L", "S3": "R", "S2": "M", "F": "", "FORCE": "L", "GND": "R"}
    # VF              VS1             VS2             VS3             IForce          IGnd
    # ICCAP_VAR IS2        0              ICCAP_VAR IS1        0              ICCAP_VAR IS3        0              ICCAP_VAR GND        0
    cols_tlm = ["V_F", "V_S1", "V_S2", "V_S3", "I_FORCE", "I_GND", "I_S2", "I_S1", "I_S3", "GND"]
    cols_dmt_tlm = ["V_F", "V_L", "V_M", "V_R", "I_L", "I_R", "I_M", "I_L", "I_R", "GND"]
    call_get_nodes(cols_tlm, nodes_tlm, fallback_tlm, cols_dmt_tlm)

    nodes_tetrode = DutType.tetrode.get_nodes()
    fallback_tetrode = {"BF1": "", "BF2": ""}
    # VE              VB1             VB2             IB1             IB2             IE              IC
    # ICCAP_VAR VBf1       -0.01          ICCAP_VAR VC         0              ICCAP_VAR VBf2       0.01
    cols_tetrode = ["V_E", "V_B1", "V_B2", "I_B1", "I_B2", "I_E", "I_C", "V_BF1", "V_C", "V_BF2"]
    cols_dmt_tetrode = [
        "V_E",
        "V_B1",
        "V_B2",
        "I_B1",
        "I_B2",
        "I_E",
        "I_C",
        "V_BF1",
        "V_C",
        "V_BF2",
    ]
    call_get_nodes(cols_tetrode, nodes_tetrode, fallback_tetrode, cols_dmt_tetrode)

    nodes_bjt = DutType.bjt.get_nodes()
    fallback_bjt = {}
    # vb              vc              ic              ib
    #  USER_VAR  vbc        0.5            ICCAP_VAR ve         0              ICCAP_VAR vs         0
    cols_bjt = ["V_B", "V_C", "I_C", "I_B", "V_BC", "V_E", "V_S"]
    cols_dmt_bjt = ["V_B", "V_C", "I_C", "I_B", "V_BC", "V_E", "V_S"]
    call_get_nodes(cols_bjt, nodes_bjt, fallback_bjt, cols_dmt_bjt)


def call_get_nodes(cols, nodes, fallback, cols_dmt):
    for i_col, col in enumerate(cols):
        if col[0] not in "VIC":
            # only rename the names of values which can be identified
            pass
        else:
            nodes_in_col = get_nodes(col, nodes, fallback=fallback)
            if nodes_in_col:
                col = col[0] + r"_" + "".join(nodes_in_col)
            else:
                raise UnknownColumnError(
                    "The column "
                    + col
                    + " is unknown to this DuT as the nodes can not be extracted! Either a fallback behavior or different DuT nodes for this column are needed."
                )

        assert col == cols_dmt[i_col]


if __name__ == "__main__":
    test_get_nodes_teledyne()
    test_get_nodes_DotSeven()
    dummy = 1

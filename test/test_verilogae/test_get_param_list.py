""" Testing to obtain the parameters of a function
"""
from pathlib import Path

from DMT.core import MCard
from DMT.external import get_param_list


def calculate_be_capacitance(model, vbe, t_dev, *, cbepar=None, flsh=None, **model_parameters):
    flsh = int(flsh)  # be save
    cjep = model.functions["Cjep"].eval(
        temperature=t_dev, voltages={"br_bpei": vbe}, flsh=flsh, **model_parameters
    )
    cjei = model.functions["Cjei"].eval(
        temperature=t_dev, voltages={"br_biei": vbe}, flsh=flsh, **model_parameters
    )
    return cjei + cjep + cbepar


def test_vae_module():
    mc_hicum_l2 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=Path(__file__).resolve().parent / "hicumL2V2p4p0.va",
    )
    mc_hicum_l2.update_from_vae(remove_old_parameters=True)
    module = mc_hicum_l2.get_verilogae_model()

    params = get_param_list(module.functions["Cjep"], info=None)

    assert set(params) == {
        "cjep0",
        "vdep",
        "vge",
        "zep",
        "ajep",
        "vgb",
        "f1vg",
        "flsh",
        "tnom",
        "type",
        "rth",
        "dt",
    }


def test_custom_fct():
    mc_hicum_l2 = MCard(
        ["C", "B", "E", "S", "T"],
        default_module_name="",
        default_subckt_name="",
        va_file=Path(__file__).resolve().parent / "hicumL2V2p4p0.va",
    )
    mc_hicum_l2.update_from_vae(remove_old_parameters=True)
    module = mc_hicum_l2.get_verilogae_model()

    model_function_info = {
        "independent_vars": ("vbe", "t_dev"),
        "depends": (module.functions["Cjep"], module.functions["Cjei"]),
    }
    params = get_param_list(calculate_be_capacitance, info=model_function_info)

    assert set(params) == {
        "ajep",
        "vge",
        "type",
        "cjep0",
        "cjei0",
        "ajei",
        "rth",
        "flsh",
        "vdei",
        "tnom",
        "vgb",
        "vdep",
        "zei",
        "f1vg",
        "cbepar",
        "zep",
        "dt",
    }


if __name__ == "__main__":
    test_vae_module()
    test_custom_fct()

""" Helpers to integrate VerilogAE into DMT
"""
# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-core>
#
# This file is part of DMT_core.
#
# DMT_core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DMT_core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
import warnings
from inspect import signature
from collections import OrderedDict

# VAE models known to DMT
HICUM_L2 = "HICUM_L2"
SGP = "SGP"
HICUM_L0 = "HICUM_L0"


def get_param_list(meq_function, all_parameters=False, info=None):
    """Returns a list with the McParameter names for the given callable in correct order, assuming that only the top-most function is not from VerilogAE

    Parameters
    ----------
    meq_function : function
        Function of the model equation which shall be used.
    all_parameters : {False, True}, optional
        If True, the independent_vars are ignored and the full parameter list is returned.

    Returns
    -------
    params : list
        List of parameters for this function
    """
    if info is None:
        info = {}

    try:
        sig = signature(meq_function)
        func_params = list(sig.parameters)

        # only kwargs : https://stackoverflow.com/questions/196960/can-you-list-the-keyword-arguments-a-function-receives
        func_params = [p.name for p in sig.parameters.values() if (p.kind == p.KEYWORD_ONLY)]
    except TypeError:
        # if meq_function is directly a verilogae function
        func_params = meq_function.parameters

    for attr in ["depends", "depends_optional", "independent_vars"]:
        if not attr in info:
            info[attr] = tuple()

    if not isinstance(info["depends"], tuple):
        raise NotImplementedError("MUST be tuple! Error in " + meq_function.__name__ + "_info")
    if not isinstance(info["depends_optional"], tuple):
        raise NotImplementedError("MUST be tuple! Error in " + meq_function.__name__ + "_info")
    if not isinstance(info["independent_vars"], tuple):
        raise NotImplementedError("MUST be tuple! Error in " + meq_function.__name__ + "_info")

    for dependence in info["depends"]:
        if isinstance(dependence, str):
            func_params.append(dependence)
        else:
            try:
                func_params += dependence.parameters
            except AttributeError:
                func_params += get_param_list(dependence, all_parameters=all_parameters)

    # unique it!
    func_params = list(OrderedDict.fromkeys(func_params))

    if all_parameters:
        func_params = list(OrderedDict.fromkeys(func_params))
        return func_params

    # delete the parameters which are independent and without the opti_params
    params = []
    for param in func_params:
        if not param in info["independent_vars"]:
            params.append(param)

    return params


def get_dmt_model(vae_module, model_type, version):
    """Retrieving a DMT fitting model for XSteps from a VAE compiled VA-Code.

    This function also adds the needed attributes.

    Parameters
    ----------
    vae_module : module
        VAE compiled and installed VA-Code
    model_type : {'HICUM_L0', 'HICUM_L2'}
        Currently supporting only the two HICUM levels
    version : float
        Version of the compiled va-code

    Returns
    -------
    model : module
        The VAE module with added attributes

    """
    warnings.warn(
        "get_DMT_model is deprecated and will be removed in future major releases.\n"
        + "Directly pass the MCard and optionally the special VAE module to the XSteps!",
        category=DeprecationWarning,
    )
    model = vae_module

    if model_type not in [HICUM_L0, HICUM_L2, SGP]:
        raise IOError("DMT->VerilogAE: Currently only 'HICUM' is supported by VAE+DMT.")

    # temprary fix
    class VaeStub:
        pass

    model_patched = VaeStub()
    model_patched.functions = model.functions
    model_patched.modelcard = model.modelcard
    model = model_patched
    # temprary fix

    model.model_type = model_type
    model.version = version
    if "HICUM" in model_type:
        if "L0" in model_type:
            model.hicum_level = 0
        elif "L2" in model_type:
            model.hicum_level = 2
        else:
            raise IOError("DMT->VerilogAE: The HICUM level must be inside the model_type!")
    elif "SGP" in model_type:
        model.hicum_level = 0  # Markus: why do we need that
    else:
        raise IOError("DMT->VerilogAE: Currently only 'HICUM' is supported")

    return model

r""" Some Hdev model equations that can be used for extraction

Etwas Spaß muss sein::

        ,__    _,            ___
        '.`\ /`|     _.-"```   `'.
        ; |  /   .'             `}
        _\|\/_.-'                 }
    _.-"a                 {        }
    .-`  __    /._          {         }\
    '--"`  `""`   `\   ;    {         } \
                |   } __ _\       }\  \
                |  /;`   / :.   }`  \  \
                | | | .-' /  / /     '. '._
                .'__/-' ````.-'.'        '-._'-._
                ```        ````              ``

"""
# DMT_core
# Copyright (C) from 2022  SemiMod
# Copyright (C) until 2021  Markus Müller, Mario Krattenmacher and Pascal Kuthe
# <https://gitlab.com/dmt-development/dmt-device>
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
import numpy as np

from DMT.core import constants
from DMT.core import check_nan_inf
from DMT.extraction.model import Model
from DMT.core.circuit import CircuitElement, RESISTANCE, CAPACITANCE, CURRENT

# from numba import jit

# pylint: disable=too-many-lines


class COOSModel(Model):
    """Defines the equivalent circuit model methods and the equivalent circuit."""

    def __init__(self, model_name, version):
        super().__init__(
            model_name,
            version,
            ["C", "B", "E", "S", "T", "CI", "EI", "BP", "BI", "SI"],
            ["eabs", "temp", "dop", "don", "acc", "mat"],  # 'it_ick', 'ick',
        )

        ### External resistances and sheet resistances
        self.model_velocity_temp_info = {
            "independent_vars": (),
            "depends": ("model_mobility",),
        }

    #################################################################################################################### External resistances and sheet resistances

    def model_series_resistance_temp(self, t_dev=None, r=None, zeta=None, tnom=None, **_kwargs):
        """Temperature dependent series resistance"""
        return r * (t_dev / (tnom + constants.P_CELSIUS0)) ** zeta

    def lattice_mobility(self, mob, dim, T_T0, grading):
        # step 1: calculate lattice mobility and scale it with temperature
        mu_L = mob["mu_L"]
        #   if (mob%bowing_is_device) then
        #     mu_L = mob%mu_L + grading*mob%mu_L_a1 + grading**2*mob%mu_L_a2
        mu_L = mu_L * T_T0 ** mob["gamma_L"]
        return mu_L

    def caughey_thomas(self, mob, mu_L, grading, impurity, t):
        #   type(mob_model) :: mob      !mobility parameters
        #   TYPE(DUAL_NUM)  :: mu_L     !lattice mobility
        #   real(8)         :: grading  !impurity concentration
        #   real(8)         :: impurity !impurity concentration
        #   real(8)         :: t        !temperature in kelvin

        #   real(8)         :: mu_min,mu_min_t
        #   real(8)         :: impurity_ref,impurity_ref_temp
        #   real(8)         :: alpha,alpha_temp
        #   TYPE(DUAL_NUM)  :: mu_LI

        mu_min = mob["mu_min"]
        #   if (mob%bowing_is_device) then
        #     mu_min = mu_min + mob%mu_min_a1*grading + mob%mu_min_a2*grading**2
        #   endif
        if t > 200:
            mu_min_t = mu_min * (t / 300) ** mob["gamma_1"]
        else:
            mu_min_t = mu_min * (t / 200) ** mob["gamma_2"] * (2 / 3) ** mob["gamma_1"]

        impurity_ref = mob["c_ref"]
        impurity_ref_temp = impurity_ref * (t / 300) ** mob["gamma_3"]

        alpha = mob["alpha"]
        alpha_temp = alpha * (t / 300) ** mob["gamma_4"]

        mu_LI = mu_min_t + (mu_L - mu_min_t) / (1 + (impurity / impurity_ref_temp) ** alpha)
        return mu_LI

    def vs_device(self, mob_paras, t_t0, grading):
        # type(mob_model)         :: mob_paras !< semiconductor model id
        # real(8)                 :: t_t0      !< [K] temperatur
        # real(8),optional,value  :: grading   !< [1/m] grading density

        # real(8) :: v_s
        # real(8) :: T_Tmat

        v_s = mob_paras["v_sat"]
        # if (mob_paras%bowing_is_device) then
        # v_s = v_s + mob_paras%v_sat_a1 * grading + mob_paras%v_sat_a2 * grading**2
        # endif

        # temperature
        v_s = v_s * t_t0 ** mob_paras["zeta_v"]
        return v_s

    def vs_default(self, mob, t_t0, grading):
        # type(mob_model)         :: mob           !< semiconductor model id
        # real(8)                 :: t_t0             !< [K] temperatur
        # real(8),optional,value  :: grading !< [1/m] grading density

        # real(8) :: v_s
        # real(8) :: T_Tmat

        # composition dependence
        v_s = mob["v_sat"]
        # if (mob%bowing_is_device) then
        # v_s = v_s + mob%v_sat_a1 * grading + mob%v_sat_a2 * grading**2
        # endif

        # temperature
        v_s = v_s / (1 - mob["A"] + mob["A"] * t_t0)
        return v_s

    def impurity_device(self, mob, mu_L, grading, don, acc, t_t0, n):
        #   type(mob_model) :: mob      !mobility parameters
        #   TYPE(DUAL_NUM)  :: mu_L     !lattice mobility
        #   real(8)         :: grading      !donor concentration
        #   real(8)         :: don      !donor concentration
        #   real(8)         :: acc      !acceptor concentration
        #   real(8)         :: t_t0     !temperature in kelvin
        #   TYPE(DUAL_NUM)  :: n        !electron density at point

        #   TYPE(DUAL_NUM)  :: mu_min
        #   real(8)         :: impurity
        #   TYPE(DUAL_NUM)  :: mu_LI

        mu_min = mob["mu_min"]
        #   if (mob%bowing_is_device) then
        #     mu_min = mu_min + mob%mu_min_a1*grading + mob%mu_min_a2*grading**2
        #   endif
        if True:  # iselec?
            mu_min = mu_min * (1 + (mob["r"] - 1) * acc / (acc + n))
        #   else
        #     mu_min            = mu_min*(1+(mob%r-1)*don/(don+n))
        #   endif

        impurity = abs(don) + abs(acc)
        mu_LI = (
            mu_min
            + (mu_L - mu_min) / (1 + (impurity / mob["c_ref"]) ** mob["alpha"])
            + mob["mu_hd"] / (1 + (impurity / mob["c_ref_2"]) ** mob["alpha_2"])
        )
        mu_LI = mu_LI * (t_t0) ** (
            mob["gamma_1"] / (1 + (impurity / mob["c_ref"]) ** mob["gamma_2"])
        )
        return mu_LI

    def get_vsat(self, semi, mob, T_T0, grading):
        # integer :: is,ib
        # real(8) :: T_T0
        # real(8) :: grading

        # type(mob_model),pointer :: mob,mob_A,mob_B
        # real(8) :: vs,vs_a,vs_B
        # integer :: id_materialA
        # integer :: id_materialB

        vs = 0
        # if (SEMI(is)%is_alloy) then
        # id_materialA = SEMI(is)%id_materialA
        # id_materialB = SEMI(is)%id_materialB
        # mob_A        => SEMI(id_materialA)%band_pointer(ib)%band%mob
        # mob_B        => SEMI(id_materialB)%band_pointer(ib)%band%mob
        # endif

        if "def" in mob["v_sat_type"]:
            if True:
                vs = vs_default(mob, T_T0, grading)

        # elseif (mob%bowing_is_default) then
        #     vs_A = vs_default(mob_A,T_T0,grading)
        #     vs_B = vs_default(mob_B,T_T0,grading)
        #     vs   = bow(vs_A, vs_A, mob%v_sat_bow, grading)

        # elseif (mob%bowing_is_device) then
        #     vs   = vs_default(mob,T_T0,grading)

        elif "dev" in mob["v_sat_type"]:
            if True:
                vs = vs_device(mob, T_T0, grading)

        # elseif (mob%bowing_is_default) then
        #     vs_A = vs_device(mob_A,T_T0,grading)
        #     vs_B = vs_device(mob_B,T_T0,grading)
        #     vs   = bow(vs_A, vs_A, mob%v_sat_bow, grading)

        # elseif (mob%bowing_is_device) then
        #     vs   = vs_device(mob,T_T0,grading)

        # endif
        return vs

    def model_mobility(self, mat, valley, eabs, dop, temp, mu_L, velo=None):
        """return Hdev mobility for material mat, in valley at field eabs, doping dop and temperature temp.
        if velo is not None, return velocity instead of mobility.
        """
        grading = 0  # alloy not implemented here
        T_T0 = temp / mat["SEMI"]["temp0"]

        band, mob, semi = None, None, None
        for band_ in mat["BAND_DEF"]:
            if band_["valley"] == valley:
                band = band_
        for mob_ in mat["MOB_DEF"]:
            if mob_["valley"] == valley:
                mob = mob_
        semi = mat["SEMI"]

        # set the "modelcard" parameters here
        mob["mu_L"] = mu_L

        # if (SEMI(is)%is_alloy) then
        # id_materialA = SEMI(is)%id_materialA
        # id_materialB = SEMI(is)%id_materialB
        # mob_A        => SEMI(id_materialA)%band_pointer(ib)%band%mob
        # mob_B        => SEMI(id_materialB)%band_pointer(ib)%band%mob
        # endif

        # step 1: calculate lattice mobility and scale it with temperature
        if "def" in mob["l_scat_type"]:
            if True:
                mu_L = mob["mu_L"]
            # elif mob['l_scat_type']=='default':
            #     # mu_L_A = mob_A%mu_L
            #     # mu_L_B = mob_B%mu_L
            # elif (mob%bowing_is_device):
            #     # mu_L   = mob%mu_L + grading*mob%mu_L_a1 + grading**2*mob%mu_L_a2
            # else:
            #     raise IOError('***error*** bowing model not set correctly.')

        elif "temp" in mob["l_scat_type"]:
            if True:
                mu_L = self.lattice_mobility(mob, 1, T_T0, grading)
            # elif (mob%bowing_is_default):
            #     mu_L_A = lattice_mobility(mob_A,dim,T_T0,grading)
            #     mu_L_B = lattice_mobility(mob_B,dim,T_T0,grading)
            # elif (mob%bowing_is_device):
            #     mu_L   = lattice_mobility(mob,dim,T_T0,grading)
            # else:
            #     raise IOError('***error*** bowing model not set correctly.')

        else:
            raise IOError("***error*** lattice scattering model not set correctly.")

        # step 2: calculate lattice+impurity mobility using caughey and thomas equation
        if "defa" in mob["li_scat_type"]:
            if True:
                mu_LI = mu_L
            # elseif(mob%bowing_is_default) then
            #     mu_LI = matthiesen_rule(mu_L_A, mu_L_B, mob%mu_bow, grading)
            # elseif(mob%bowing_is_device) then
            #     mu_LI = mu_L
            # else
            #     write(*,*) '***error*** mobility bowing model not set correctly.'
            #     stop
            # endif

        elif "caughey" in mob["li_scat_type"]:
            if True:
                mu_LI = self.caughey_thomas(mob, mu_L, grading, dop, temp)

            # elseif (mob%bowing_is_default) then
            #     mu_LI_A = caughey_thomas(mob_A, mu_L_A,grading, abs(don)+abs(acc), t)
            #     mu_LI_B = caughey_thomas(mob_B, mu_L_B,grading, abs(don)+abs(acc), t)
            #     mu_LI   = matthiesen_rule(mu_LI_A, mu_LI_B, mob%mu_bow, grading)

            # elseif (mob%bowing_is_device) then
            #     mu_LI = caughey_thomas(mob, mu_L,grading, abs(don)+abs(acc), t)
            # else
            #     write(*,*) '***error*** mobility bowing model not set correctly.'
            #     stop
            # endif

        elif "devi" in mob["li_scat_type"]:
            if True:
                mu_LI = self.impurity_device(mob, mu_L, grading, don, acc, T_T0, n)

            # elseif (mob%bowing_is_default) then
            #     mu_LI_A = impurity_device(mob_A, mu_L_A,grading, don,acc,T_T0,n)
            #     mu_LI_B = impurity_device(mob_B, mu_L_B,grading, don,acc,T_T0,n)
            #     mu_LI   = matthiesen_rule(mu_LI_A, mu_LI_B, mob%mu_bow, grading)

            # elseif (mob%bowing_is_device) then
            #     mu_LI = impurity_device(mob  , mu_L,grading  , don,acc, T_T0,n)
            # else
            #     write(*,*) '***error*** mobility bowing model not set correctly.'
            #     stop

        else:
            raise IOError("***error*** li mobility model not set correctly.")

        # if (mob%li_scat_is_tuwien) then !implementation not finished, probably not needed
        # !   if (.not.SEMI(is)%is_alloy) then
        # !     mu_LI   = tu_wien(mob, mu_L, don,acc, T_T0)

        # !   elseif (mob%bowing_is_default) then
        # !     mu_LI_A = tu_wien(mob_A, mu_L_A, don, acc, T_T0)
        # !     mu_LI_B = tu_wien(mob_B, mu_L_B, don, acc, T_T0)
        # !     mu_LI   = matthiesen_rule(mu_LI_A, mu_LI_B, mob%mu_c, grading)

        # !   elseif (mob%bowing_is_device) then
        # !     mu_LI   = tu_wien(mob, mu_L, don,acc, T_T0)
        # !   endif

        # !   endif
        # ! endif

        # step 3: calculate v_s
        if not "def" in mob["hc_scat_type"]:
            vs = get_vsat(semi, mob, T_T0, grading)  # not needed if field dependence is turned off

        # step 2: field dependence if beta>0
        if "def" in mob["hc_scat_type"]:
            mu = mu_LI
            if velo is not None:
                f = eabs
                f = abs(f)
                mu = mu * f
        else:
            f = eabs
            f = abs(f)
            # if f==0:
            #     mu = mu_LI
            if "sat" in mob["hc_scat_type"]:
                if velo is None:
                    mu = mu_LI / ((1 + (f * mu_LI / vs) ** mob["beta"]) ** (1 / mob["beta"]))
                else:
                    mu = mu_LI * f / ((1 + (f * mu_LI / vs) ** mob["beta"]) ** (1 / mob["beta"]))
            elif "ndm" in mob["hc_scat_type"]:
                if velo is None:
                    mu = (mu_LI + vs / f * (f / mob["f0"]) ** mob["beta"]) / (
                        1 + (f / mob["f0"]) ** mob["beta"]
                    )
                else:
                    mu = (
                        f
                        * (mu_LI + vs / f * (f / mob["f0"]) ** mob["beta"])
                        / (1 + (f / mob["f0"]) ** mob["beta"])
                    )
            elif "ddm" in mob["hc_scat_type"]:
                if velo is None:
                    mu = (mu_LI + mob["mu_HC"] * (f / mob["f0"]) ** mob["beta"]) / (
                        1 + (f / mob["f0"]) ** mob["beta"]
                    )
                else:
                    mu = (
                        f
                        * (mu_LI + mob["mu_HC"] * (f / mob["f0"]) ** mob["beta"])
                        / (1 + (f / mob["f0"]) ** mob["beta"])
                    )
            else:
                raise IOError("***error*** hc scat mobility model not set correctly.")

        return mu

    def model_velocity(self, mat, valley, eabs, dop, temp):
        return get_mobility(mat, valley, eabs, dop, temp, velo=True)

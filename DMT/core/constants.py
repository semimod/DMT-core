""" Constants from constants.h from ADMS, or CEDIC simul to be more exact!

Namings :

*  M is a mathematical constant
*  P is a physical constant. The constants have been taken from http://physics.nist.gov
*  others: HICUM constants

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


M_E = 2.7182818284590452354
""" define M_E 2.7182818284590452354 """

M_LOG2E = 1.4426950408889634074
""" define M_LOG2E 1.4426950408889634074 """

M_LOG10E = 0.43429448190325182765
""" define M_LOG10E 0.43429448190325182765 """

M_LN2 = 0.69314718055994530942
""" define M_LN2 0.69314718055994530942 """

M_LN10 = 2.30258509299404568402
""" define M_LN10 2.30258509299404568402 """

M_PI = 3.14159265358979323846
""" define M_PI 3.14159265358979323846 """

M_TWO_PI = 6.28318530717958647652
""" define M_TWO_PI 6.28318530717958647652 """

M_PI_2 = 1.57079632679489661923
""" define M_PI_2 1.57079632679489661923 """

M_PI_4 = 0.78539816339744830962
""" define M_PI_4 0.78539816339744830962 """

M_1_PI = 0.31830988618379067154
""" define M_1_PI 0.31830988618379067154 """

M_2_PI = 0.63661977236758134308
""" define M_2_PI 0.63661977236758134308 """

M_2_SQRTPI = 1.12837916709551257390
""" define M_2_SQRTPI 1.12837916709551257390 """

M_SQRT2 = 1.41421356237309504880
""" define M_SQRT2 1.41421356237309504880 """

M_SQRT1_2 = 0.70710678118654752440
""" define M_SQRT1_2 0.70710678118654752440 """


P_Q = 1.602176462e-19
"""  charge of electron in coulombs 1.602176462e-19 """

P_C = 2.99792458e8
"""  speed of light in vacuum in meters/sec 2.99792458e8 """

P_K = 1.3806503e-23
"""  Boltzmann's constant in joules/kelvin 1.3806503e-23 """

P_H = 6.62606876e-34
"""  Planck's constant in joules*sec 6.62606876e-34 """

P_EPS0 = 8.854187817e-12
""""  permittivity of vacuum in farads/meter 8.854187817e-12 """

P_U0 = 12.566370614e-7
""""  permeability of vacuum in henrys/meter (4.0e-7 * M_PI) (12.566370614e-7) """

P_CELSIUS0 = 273.15
"""  zero celsius in kelvin 273.15 """

VPT_thresh = 1.0e2
Dexp_lim = 80.0
Cexp_lim = 80.0
DFa_fj = 1.921812
DFal_qr = 0.01
RTOLC = 1.0e-5
l_itmax = 100
TMAX = 326.85
TMIN = -100.0
LN_EXP_LIMIT = 11.0
MIN_R = 0.001
Gmin = 1.0e-12


def calc_VT(temp):
    """Calculates the thermal voltage for the given temperature (in Kelvin)"""
    return P_K * temp / P_Q


vT_300 = calc_VT(300)
""" thermal voltage for 300 Kelvin """

DA_FI = 1.921812
""" constant smoothing parameter for HICUM """

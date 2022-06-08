""" Technology class to describe all technology dependencies. Main use is scaling.

If a technology can use TRADICA, the class :class:`DMT.TRADICA.TechTradica` is recommended!

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
from DMT.core.dut_type import DutType

try:
    from pylatex import Section
    from DMT.external.pylatex import Tex
except ImportError:
    pass


class Technology(object):
    r"""This abstract class shall bundle all relevant scaling and extraction routines that are specific for a given technologe.

    Parameters
    ----------
    name : str
        Name of the technology

    Attributes
    ----------
    name : str
        Name of the technology

    """
    name = ""

    def __init__(self, name, scaling_builder=None):
        self.name = name
        self.scaling_builder = scaling_builder

    def print_tex(self, dut_ref, mcard):
        """Prints a technology description, mainly used for autodocumentation reasons.

        Parameters
        ----------
        dut_ref : :class:`~DMT.core.DutView`
            Can be used to obtain tech quanties... (or to generate a TRADICA input file :) )
        mcard : :class:`~DMT.core.McParameterCollection`
            A Modelcard that contains all parameters that are required for scaling, as well as the parameters that shall be scaled.
        """
        doc = Tex()
        with doc.create(Section("Technology :" + self.name)):
            doc.append("Technology description missing")
        return doc

    def get_bib_entries(self):
        """bibliograpy entries of a technology"""
        return ""

    def create_mcard_library(self, lib, mcard, path, dut_type=DutType.npn):
        """Creates a file containing model cards for all sizes of duts present in the lib.

        Parameters
        ----------
        lib : :class:`~DMT.core.DutLib`
        path : str
            File path to write to.
        dut_type : :class:`~DMT.core.DutType`, optional
            Dut types to create model cards for.
        """

    def scale_all(self, mcard, lE0, bE0, nfinger, config):
        """This method receives a Modelcard (that includes relevant scaling parameters such as sheet resistances) and sets the scaled values accordingly.

        Parameters
        ----------
        mcard : :class:`~DMT.core.McParameterCollection`
            A Modelcard or McParameterCompositon that contains all parameters that are required for scaling, as well as the parameters that shall be scaled.
        lE0   : float64
            The length of the desired emitter window to be modeled by mcard.
        bE0   : float64
            The width of the desired emitter window to be modeled by mcard.
        nfinger : integer
            Number of emitter fingers.
        config : str
            A unique identifier for the configuration.
        """
        mcard = self.scale_capacitances(mcard, lE0, bE0, nfinger, config)
        mcard = self.scale_sheet_resistances(mcard, lE0, bE0, nfinger, config)
        mcard = self.scale_currents(mcard, lE0, bE0, nfinger, config)

        return mcard

    def scale_currents(self, mcard, lE0, bE0, nfinger, config):
        """This method receives a Modelcard (that includes relevant scaling parameters such as sheet resistances) and sets the scaled currents accordingly.

        Parameters
        ----------
        mcard : :class:`~DMT.core.McParameterCollection`
            A Modelcard or McParameterCompositon that contains all parameters that are required for scaling, as well as the parameters that shall be scaled.
        lE0   : float64
            The length of the desired emitter window to be modeled by mcard.
        bE0   : float64
            The width of the desired emitter window to be modeled by mcard.
        nfinger : integer
            Number of emitter fingers.
        config : str
            A unique identifier for the configuration.
        """
        raise NotImplementedError

    def scale_capacitances(self, mcard, lE0, bE0, nfinger, config):
        """This method receives a Modelcard (that includes relevant scaling parameters such as sheet resistances) and sets the scaled capacitances accordingly.

        Parameters
        ----------
        mcard : :class:`~DMT.core.McParameterCollection`
            A Modelcard or McParameterCompositon that contains all parameters that are required for scaling, as well as the parameters that shall be scaled.
        lE0   : float64
            The length of the desired emitter window to be modeled by mcard.
        bE0   : float64
            The width of the desired emitter window to be modeled by mcard.
        nfinger : integer
            Number of emitter fingers.
        config : str
            A unique identifier for the configuration.
        """
        raise NotImplementedError

    def scale_sheet_resistances(self, mcard, lE0, bE0, nfinger, config):
        """This method receives a Modelcard (that includes relevant scaling parameters such as sheet resistances) and sets the scaled resistances accordingly.

        Parameters
        ----------
        mcard : :class:`~DMT.core.McParameterCollection`
            A Modelcard or McParameterCollection that contains all parameters that are required for scaling, as well as the parameters that shall be scaled.
        lE0   : float64
            The length of the desired emitter window to be modeled by mcard.
        bE0   : float64
            The width of the desired emitter window to be modeled by mcard.
        nfinger : integer
            Number of emitter fingers.
        config : str
            A unique identifier for the configuration.
        """
        raise NotImplementedError

    def scale_modelcard(
        self, mcard, lE0, bE0, nfinger, config, lE_drawn_ref=None, bE_drawn_ref=None
    ):
        """This method scales a already finished modelcard (no sheet resistances).

        Parameters
        ----------
        mcard : :class:`~DMT.core.McParameterCollection`
            A Modelcard or McParameterCompositon that contains all parameters that are required for scaling, as well as the parameters that shall be scaled.
        lE0   : float64
            The length of the desired emitter window to be modeled by mcard.
        bE0   : float64
            The width of the desired emitter window to be modeled by mcard.
        nfinger : integer
            Number of emitter fingers.
        config : str
            A unique identifier for the configuration.
        """
        raise NotImplementedError

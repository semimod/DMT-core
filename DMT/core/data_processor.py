""" data processor module

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
import skrf as rf
from DMT.core import specifiers, set_col_name, sub_specifiers


def is_iterable(arg):
    """Returns True if the object is iterable

    Source: https://stackoverflow.com/a/36407550/13212532

    """
    try:
        _test = (e for e in arg)
        return True
    except TypeError:
        return False


def flatten(items):
    """Yield items from any nested iterable; see Reference https://stackoverflow.com/a/40857703."""
    for x in items:
        if not isinstance(x, (str, bytes)) and is_iterable(x):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


def strictly_increasing(L):
    """checks if given iterable is strictly increasing or not"""
    return all(x < y for x, y in zip(L, L[1:]))


class DataProcessor(object):
    """Basic class responsible for the manipulation and performing calculations on electrical Data in DMT.

    This class is designed as a `mixin <http://www.qtrac.eu/pyagg.html>`_ class. This design pattern allows to use multiple inheritance in order
    to extend the functionality of other DMT modules by the basic functions provided here.
    The functions here are basic electrical functions on np.array() objects with a clear syntax that should not change a lot in the future.

    Methods
    -------
    convert_n_port_para(para_values, p_from, p_to, z0=float(50)):
        Calculate the p_to n_port parameters from the p_from n_port parameters stored in para_values.

    deembed_short(s_para_values, s_para_short_values):
        de-embed the S parameters in s_para_values using the S parameters from the short dummy.

    deembed_open(s_para_values, s_para_open_values):
        de-embed the S parameters in s_para_values using the S parameters from the open dummy.

    calc_ft(freq, para_values, p_type):
        Calculate the transit frequency ft from the small signal parameters of type p_type in para_values.

    calc_fmax(freq, para_values, p_type):
        Calculate the maximum frequency of oscillation fmax from the small signal parameters of type p_type in para_values.

    calc_cbe(freq, para_values, p_type):
        Calculate the base-emitter junction capacitance from the small signal parameters of type p_type in para_values.

    calc_cbc(freq, para_values, p_type):
        Calculate the base-collector junction capacitance from the small signal parameters of type p_type in para_values.

    Notes
    -----
    ..todo: Nice tex equations here!
    """

    def fix_z0_shape(self, z0, nfreqs, nports):
        """
        Make a port impedance of correct shape for a given network's matrix

        This attempts to broadcast z0 to satisfy
            npy.shape(z0) == (nfreqs,nports)

        Parameters
        ----------
        z0 : number, array-like
            z0 can be:
            * a number (same at all ports and frequencies)
            * an array-like of length == number ports.
            * an array-like of length == number frequency points.
            * the correct shape ==(nfreqs,nports)

        nfreqs : int
            number of frequency points
        nports : int
            number of ports

        Returns
        -------
        z0 : array of shape ==(nfreqs,nports)
            z0  with the right shape for a nport Network

        Examples
        --------
        For a two-port network with 201 frequency points, possible uses may
        be

        >>> z0 = rf.fix_z0_shape(50 , 201,2)
        >>> z0 = rf.fix_z0_shape([50,25] , 201,2)
        >>> z0 = rf.fix_z0_shape(range(201) , 201,2)


        """

        if np.shape(z0) == (nfreqs, nports):
            # z0 is of correct shape. super duper.return it quick.
            return z0.copy()

        elif np.isscalar(z0):
            # z0 is a single number
            return np.array(nfreqs * [nports * [z0]])

        elif len(z0) == nports:
            # assume z0 is a list of impedances for each port,
            # but constant with frequency
            return np.array(nfreqs * [z0])

        elif len(z0) == nfreqs:
            # assume z0 is a list of impedances for each frequency,
            # but constant with respect to ports
            return np.array(nports * [z0]).T

        else:
            raise IndexError("z0 is not an acceptable shape")

    def s2y(self, s_in, z0=50):
        """
        convert scattering parameters [#]_ to admittance parameters [#]_


        .. math::
            y = \\sqrt {y_0} \\cdot (I - s)(I + s)^{-1} \\cdot \\sqrt{y_0}

        Parameters
        ----------
        s : complex array-like
            scattering parameters
        z0 : complex array-like or number
            port impedances

        Returns
        -------
        y : complex array-like
            admittance parameters

        See Also
        --------
        s2z
        s2y
        s2t
        z2s
        z2y
        z2t
        y2s
        y2z
        y2z
        t2s
        t2z
        t2y
        Network.s
        Network.y
        Network.z
        Network.t

        References
        ----------
        .. [#] http://en.wikipedia.org/wiki/S-parameters
        .. [#] http://en.wikipedia.org/wiki/Admittance_parameters
        """
        # cdef int nfreqs, nports
        s = np.copy(s_in)
        Id = np.zeros_like(s_in, dtype=np.cdouble)  # (nfreqs, nports, nports)
        sqrty0 = np.zeros_like(s_in, dtype=np.cdouble)  # (nfreqs, nports, nports)

        nfreqs = s_in.shape[0]
        nports = s_in.shape[1]

        z0 = self.fix_z0_shape(z0, nfreqs, nports)

        s[s == -1.0] = -1.0 + 1e-12  # solve numerical singularity
        s[s == 1.0] = 1.0 + 1e-12  # solve numerical singularity

        # The following is a vectorized version of a for loop for all frequencies.
        # Creating Identity matrices of shape (nports,nports) for each nfreqs
        np.einsum("ijj->ij", Id)[...] = 1.0
        # Creating diagonal matrices of shape (nports, nports) for each nfreqs
        np.einsum("ijj->ij", sqrty0)[...] = np.sqrt(1.0 / z0)
        # s -> y
        # y = sqrty0 @ (Id - s) @  npy.linalg.inv(Id + s) @ sqrty0  # Python>3.5
        y = np.matmul(np.matmul(np.matmul(sqrty0, (Id - s)), np.linalg.inv(Id + s)), sqrty0)
        return y

    def s2z(self, s_in, z0=50):
        """
        Convert scattering parameters [1]_ to impedance parameters [2]_


        .. math::
            z = \\sqrt {z_0} \\cdot (I + s) (I - s)^{-1} \\cdot \\sqrt{z_0}

        Parameters
        ----------
        s : complex array-like
            scattering parameters
        z0 : complex array-like or number
            port impedances.

        Returns
        -------
        z : complex array-like
            impedance parameters



        References
        ----------
        .. [1] http://en.wikipedia.org/wiki/S-parameters
        .. [2] http://en.wikipedia.org/wiki/impedance_parameters

        """
        nfreqs = s_in.shape[0]
        nports = s_in.shape[1]
        s = np.copy(s_in)
        Id = np.zeros_like(s_in, dtype=np.cdouble)  # (nfreqs, nports, nports)
        sqrtz0 = np.zeros_like(s_in, dtype=np.cdouble)  # (nfreqs, nports, nports)

        z0 = self.fix_z0_shape(z0, nfreqs, nports)

        s[s == -1.0] = -1.0 + 1e-12  # solve numerical singularity
        s[s == 1.0] = 1.0 + 1e-12  # solve numerical singularity

        # The following is a vectorized version of a for loop for all frequencies.
        # Creating Identity matrices of shape (nports,nports) for each nfreqs
        np.einsum("ijj->ij", Id)[...] = 1.0
        # Creating diagonal matrices of shape (nports, nports) for each nfreqs
        np.einsum("ijj->ij", sqrtz0)[...] = np.sqrt(z0)
        # s -> z
        # z = sqrtz0 @ npy.linalg.inv(Id - s) @ (Id + s) @ sqrtz0  # Python>3.5
        z = np.matmul(np.matmul(np.matmul(sqrtz0, np.linalg.inv(Id - s)), (Id + s)), sqrtz0)
        return z

    def convert_n_port_para(self, para_values, p_from, p_to, z0=float(50)):
        """n_port parameter conversion routine.

        Convert n_port parameters from p_from to p_to using scikit-rf. Available are all conversion between parameters S,Y,Z,T,A.

        Parameters
        ----------
        para_values  :  np.ndarray()
            Numpy array with shape (n_freq, n_port, n_port) holding the values of the small signal parameter p_from.

        p_from  :  string
            String that specifies which parameters are stored in p_from.

        p_to    :  string
            String that specifies which parameters should be created from the parameters p_from.

        z0      : float()
            Reference impedance in ohms, default is float(50).

        Returns
        -------
        para_new  :  np.ndarray()
            Numpy array with shape (n_freq, n_port, n_port) holding the values of the small signal parameter p_to.
        """
        if p_from == p_to:
            return para_values

        # call the right conversion routine in scikit-rf.
        if p_from == "S":
            if p_to == "Z":
                para_new = self.s2z(para_values, z0)
            elif p_to == "Y":
                para_new = self.s2y(para_values, z0)
            elif p_to == "T":
                para_new = rf.network.s2t(para_values)
            elif p_to == "A":
                para_new = rf.network.s2a(para_values, z0)
            elif p_to == "H":
                para_new = rf.network.s2y(para_values, z0)
                para_new = self.y2h(para_new)

        elif p_from == "Z":
            if p_to == "S":
                para_new = rf.network.z2s(para_values, z0)
            elif p_to == "Y":
                para_new = rf.network.z2y(para_values)
            elif p_to == "T":
                para_new = rf.network.z2t(para_values)
            elif p_to == "A":
                para_new = rf.network.z2a(para_values)

        elif p_from == "Y":
            if p_to == "S":
                para_new = rf.network.y2s(para_values, z0)
            elif p_to == "Z":
                para_new = rf.network.y2z(para_values)
            elif p_to == "T":
                para_new = rf.network.y2t(para_values)
            elif p_to == "A":  # i want to cry: y2a is not available in scikit-rf. workaround here
                para_new = self.y2a(para_values)

        elif p_from == "T":
            if p_to == "S":
                para_new = rf.network.t2s(para_values)
            elif p_to == "Z":
                para_new = rf.network.t2z(para_values)
            elif p_to == "Y":
                para_new = rf.network.t2y(para_values)

        elif p_from == "A":
            if p_to == "Y":
                para_new = self.a2y(para_values)
            elif p_to == "S":
                para_new = rf.network.a2s(para_values, z0)
            elif p_to == "Z":
                raise NotImplementedError

        else:
            raise IOError(
                "DMT -> DataProcessor: You specified an n-port Conversion that is not implemented or makes no sense."
            )

        return para_new

    def y2a(self, y):
        """My own y2a routine since scikit rf does not have one. What a shame!"""
        a = np.zeros(y.shape, dtype="complex")
        for fidx in range(y.shape[0]):
            det_y = np.linalg.det(y[fidx, :, :])

            a[fidx, 0, 0] = -y[fidx, 1, 1] / y[fidx, 1, 0]
            a[fidx, 0, 1] = -1.0 / y[fidx, 1, 0]
            a[fidx, 1, 0] = -det_y / y[fidx, 1, 0]
            a[fidx, 1, 1] = -y[fidx, 0, 0] / y[fidx, 1, 0]

        return a

    def y2h(self, y):
        """My own y2h routine since scikit rf does not have one. What a shame!"""
        h = np.zeros(y.shape, dtype="complex")
        for fidx in range(y.shape[0]):
            det_y = np.linalg.det(y[fidx, :, :])

            h[fidx, 0, 0] = 1
            h[fidx, 1, 1] = det_y
            h[fidx, 0, 1] = -y[fidx, 0, 1]
            h[fidx, 1, 0] = y[fidx, 1, 0]
            h[fidx, :, :] = h[fidx, :, :] / y[fidx, 0, 0]

        return h

    def a2y(self, a):
        """My own a2y routine since scikit rf does not have one. What a shame!"""
        y = np.zeros(a.shape, dtype="complex")
        for fidx in range(a.shape[0]):
            det_a = np.linalg.det(a[fidx, :, :])
            y[fidx, 0, 0] = 1.0 / a[fidx, 0, 1] * a[fidx, 1, 1]
            y[fidx, 1, 1] = 1.0 / a[fidx, 0, 1] * a[fidx, 0, 0]
            y[fidx, 0, 1] = -1.0 / a[fidx, 0, 1] * det_a
            y[fidx, 1, 0] = -1.0 / a[fidx, 0, 1]

        return y

    def parallel_norm(self, s_para_values, ndevices):
        """Normalize the measured S parameters in s_para_values to the number of parallel devices.

        Parameters
        ----------
        s_para_values       :  np.ndarray(np.cmplx128)
            S parameters that shall be de-embedded.

        ndevices            :  int
            Number of parallel devices.

        Returns
        -------
        s_para_values       :  np.ndarray(np.cmplx128)
            Normalized S-para-values

        """
        # create Y para from S para
        y_para_values = self.convert_n_port_para(
            s_para_values, "S", "Y"
        )  # (n_freq, n_port, n_port)
        # normalize Y para
        y_para_values = y_para_values / ndevices

        return self.convert_n_port_para(y_para_values, "Y", "S")

    def calc_RBC_RBE(self, mres, df_RM):
        """Calculate the metallization resistances R_CE and R_BE.

        Parameters
        ----------
        df_RM   : df
            Containing all values for the incoming df, where V_CE=0V.

        Returns
        -------
        mres    : [list]
            List containing the calculated resistance values
        """

        df_RM_clean = df_RM.dropna(axis=0, how="any")

        R_BCM = np.polyfit(np.negative(df_RM_clean["I_C"]), df_RM_clean["V_B"], 1)

        ic_2 = df_RM_clean["I_B"] + df_RM_clean["I_C"]
        R_BEM = np.polyfit(ic_2, df_RM_clean["V_B"], 1)

        mres["R_BCM"] = R_BCM[0]
        mres["R_BEM"] = R_BEM[0]
        return mres

    def calc_RCE(self, mres, df_RM):
        """Calculate the metallization resistances R_BC.

        Parameters
        ----------
        df_RM   : df
            Containing all values for the incoming df, where V_BE=0V.

        Returns
        -------
        mres    : {dict}
            List containing the calculated resistance values
        """
        df_RM_clean = df_RM.dropna(axis=0, how="any")

        R_CEM = np.polyfit((df_RM_clean["I_B"] + df_RM_clean["I_C"]), df_RM_clean["V_C"], 1)

        mres["R_CEM"] = R_CEM[0]

        return mres

    def convert_mres(self, mres):
        """Converts the calculated resistance network from delta- to wye-form.

        Parameters
        ----------
        mres    : {dict}
            List containing the calculated delta-form resistances
        Returns
        -------
        mres    : {dict}
            Same list with appended wye-form parameters.
        """
        R_sum = mres["R_BCM"] + mres["R_CEM"] + mres["R_BEM"]

        R_BM = (mres["R_BEM"] * mres["R_BCM"]) / R_sum
        R_CM = (mres["R_BCM"] * mres["R_CEM"]) / R_sum
        R_EM = (mres["R_BEM"] * mres["R_CEM"]) / R_sum

        mres["R_BM"] = R_BM
        mres["R_CM"] = R_CM
        mres["R_EM"] = R_EM

        return mres

    def deembed_mres(self, df, mres):
        """Substract external voltage drop over metal resistances from measured voltages.

        Parameters
        ----------
        df      : DMT.dataframe
            df contains DC measurements that are to be deembedded.
        mres    : {'R_BM':float64, 'R_CM':float64, 'R_EM'_float64}
            List of calculated resistances R_CM, R_BM, and R_EM.
        """
        col_vb, col_ib, col_vc, col_ic, col_ve = None, None, None, None, None
        try:
            col_vb = df.get_col_name(specifiers.VOLTAGE, "B")
            col_vb_force = set_col_name(
                specifiers.VOLTAGE, "B", sub_specifiers=sub_specifiers.FORCED
            )
            df[col_vb_force] = df[col_vb].to_numpy()
        except KeyError:
            pass
        try:
            col_vc = df.get_col_name(specifiers.VOLTAGE, "C")
            col_vc_force = set_col_name(
                specifiers.VOLTAGE, "C", sub_specifiers=sub_specifiers.FORCED
            )
            df[col_vc_force] = df[col_vc].to_numpy()
        except KeyError:
            pass
        try:
            col_ve = df.get_col_name(specifiers.VOLTAGE, "E")
            col_ve_force = set_col_name(
                specifiers.VOLTAGE, "E", sub_specifiers=sub_specifiers.FORCED
            )
            df[col_ve_force] = df[col_ve].to_numpy()
        except KeyError:
            pass
        try:
            col_ic = df.get_col_name(specifiers.CURRENT, "C")
        except KeyError:
            pass
        try:
            col_ib = df.get_col_name(specifiers.CURRENT, "B")
        except KeyError:
            pass

        if col_vb and col_ib:
            vb = df[col_vb].to_numpy()
            ib = df[col_ib].to_numpy()
            # vb_dif      = [i * mres["R_BM"] for i in ib]
            vb_dif = ib * mres["R_BM"]
            df[col_vb] = vb - vb_dif

        if col_vc and col_ic:
            vc = df[col_vc].to_numpy()
            ic = df[col_ic].to_numpy()
            vc_dif = ic * mres["R_CM"]
            df[col_vc] = vc - vc_dif

        if col_ve and col_ib and col_ic:
            ve = df[col_ve].to_numpy()
            # ie = [sum(i) for i in zip(ic, ib)]
            ie = ib + ic
            # ve_dif      = [i * mres["R_EM"] for i in ie]
            ve_dif = ie * mres["R_EM"]
            df[col_ve] = ve + ve_dif

        return df

    def deembed_short(self, s_para_values, s_para_short_values, times=1):
        """Deembed the measured S parameters in s_para_values from the measured S parameters in s_para_short_values.

        Parameters
        ----------
        s_para_values       :  np.ndarray(np.cmplx128)
            S parameters that shall be de-embedded.

        s_para_short_values  :  np.ndarray(np.cmplx128)
            S parameters of a short dummy.

        times               : int
            Number of times the short has to be removed

        Returns
        -------
        s_para_values       :  np.ndarray(np.cmplx128)
            Short de-embedded S parameters.
        """
        # create Z para from S para
        z_para_values = self.convert_n_port_para(s_para_values, "S", "Z")
        z_para_short_values = self.convert_n_port_para(s_para_short_values, "S", "Z") / times

        # find number of frequency sweeps
        n_sweeps = z_para_values.shape[0] / z_para_short_values.shape[0]
        if not np.mod(n_sweeps, 1) == 0:
            raise IOError(
                "DMT -> DataProcessor: short de-embedding structure does not match the data in df."
            )

        z_para_short_values = np.tile(z_para_short_values, [int(n_sweeps), 1, 1])

        # de-embed
        z_para_values = z_para_values - z_para_short_values

        # convert back to S para
        return self.convert_n_port_para(z_para_values, "Z", "S")

    def deembed_open(self, s_para_values, s_para_open_values, times=1):
        """Deembed the measured S parameters in s_para_values from the measured S parameters in s_para_open_values.

        Parameters
        ----------
        s_para_values       :  np.ndarray(np.cmplx128)
            S parameters that shall be de-embedded.

        s_para_open_values  :  np.ndarray(np.cmplx128)
            S parameters of a short dummy.

        times               : int
            Numer of times the open has to be removed.

        Returns
        -------
        s_para_values       :  np.ndarray(np.cmplx128)
            Short de-embedded S parameters.
        """
        # calculate the y parameters in both dataframes
        y_para_values = self.convert_n_port_para(s_para_values, "S", "Y")
        y_para_open_values = self.convert_n_port_para(s_para_open_values, "S", "Y")

        # find the number of frequency sweeps
        n_sweeps = y_para_values.shape[0] / y_para_open_values.shape[0]
        if not np.mod(n_sweeps, 1) == 0:
            raise IOError(
                "DMT -> DataProcessor: open de-embedding structure does not match the data in df."
            )

        y_para_open_values = np.tile(y_para_open_values, [int(n_sweeps), 1, 1])
        # deembed
        y_para_values = y_para_values - y_para_open_values * times

        # convert Y para back to S para
        return self.convert_n_port_para(y_para_values, "Y", "S")

    def calc_ft(self, freq, para_values, p_type):
        """Calculate the transit frequency F_T using the spot frequency method.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        F_T  :  np.ndarray()
            Array of shape [n_freq] that contains ft from the spot frequency method.
        """
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")

        # calculate ft = f / im( Y(1,1)/Y(2,1) ) element-wise for every frequency
        return freq / np.imag(y_para_values[:, 0, 0] / y_para_values[:, 1, 0])

    def calc_tfit1(self, freq, para_values, p_type):
        """Calculate the transit frequency F_T using the spot frequency method.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        tfit  :  np.ndarray()
            Array of shape [n_freq] that contains tfit from the spot frequency method.
        """

        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")
        omega = 2 * np.pi * freq
        gm = np.real(y_para_values[:, 1, 0])
        # tfi = im ( Y_11 + Y_21)/(gm*omega)
        return np.imag(y_para_values[:, 0, 0] + y_para_values[:, 0, 1]) / (omega * gm)

    def calc_tfit2(self, freq, para_values, p_type):
        """Calculate the transit frequency F_T using the spot frequency method.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        tfit  :  np.ndarray()
            Array of shape [n_freq] that contains tfit from the spot frequency method.
        """

        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")
        omega = 2 * np.pi * freq
        gm = np.real(y_para_values[:, 1, 0])
        # tfi = im ( Y_11 + Y_21)/(gm*omega)
        return np.imag(y_para_values[:, 0, 0] + y_para_values[:, 1, 0]) / (omega * gm)

    def calc_fmax(self, freq, para_values, p_type):
        """Calculate the maximum frequency of oscillation from the unilateral gain.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        fmax         :  np.ndarray()
            Array of shape [n_freq] that contains ft from the spot frequency method.
        """
        # calc the unilateral gain
        gu = self.calc_unilateral_gain(freq, para_values, p_type)

        # calculate FMAX
        return freq * gu**0.5

    # pylint: disable=unused-argument
    def calc_unilateral_gain(self, freq, para_values, p_type):
        """Calculates the unilateral gain `GU <https://www2.eecs.berkeley.edu/Pubs/TechRpts/2016/EECS-2016-15.pdf>`_ .
        | https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=1083579

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        gu           :  np.ndarray()
            Unilateral gain as an array with shape [n_freq].
        """
        # from y parameters
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")
        # calculate GU
        gu = (
            abs(y_para_values[:, 1, 0] - y_para_values[:, 0, 1]) ** 2
            / 4.0
            / (
                np.real(y_para_values[:, 0, 0]) * np.real(y_para_values[:, 1, 1])
                - np.real(y_para_values[:, 0, 1]) * np.real(y_para_values[:, 1, 0])
            )
        )
        return gu

    def calc_mag(self, freq, para_values, p_type):
        """Calculates the maximum available gain MAG.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        mag           :  np.ndarray()
            maximum available gain mag.
        """
        s_para_values = self.convert_n_port_para(para_values, p_type, "S")

        k = self.calc_k(freq, s_para_values, "S")
        mag = (
            (k - np.sqrt(k**2.0 - 1.0))
            * np.abs(s_para_values[:, 1, 0])
            / np.abs(s_para_values[:, 0, 1])
        )

        return mag

    def calc_k(self, freq, para_values, p_type):
        """Calculates the k-factor.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        k           :  np.ndarray()
            Stability factor k.

        Notes
        -----
        ..todo: from s para
        """
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")
        k = (
            2 * np.real(y_para_values[:, 0, 0]) * np.real(y_para_values[:, 1, 1])
            - np.real(y_para_values[:, 0, 1] * y_para_values[:, 1, 0])
        ) / np.abs(y_para_values[:, 0, 1] * y_para_values[:, 1, 0])
        return k

    def calc_msg(self, freq, para_values, p_type):
        """Calculates the maximum stable gain MSG.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        msg          :  np.ndarray()
            Maximum stable gain MAG.

        Notes
        -----
        ..todo: calc from S para too
        """
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")

        msg = np.absolute(y_para_values[:, 1, 0]) / np.absolute(y_para_values[:, 0, 1])
        return msg

    def calc_cap_shunt_port_1(self, freq, para_values, p_type):
        """Calculates the shunt capacitance at port 1 assuming a Pi equivalent circuit capacitance cbe from the small signal parameters para_values.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        cbe           :  np.ndarray()
            Base emitter junction capacitance as an array with shape [n_freq].
        """
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")

        # calculate cbe from y para
        cbe = np.imag(y_para_values[:, 0, 0] + y_para_values[:, 0, 1]) / (2.0 * np.pi * freq)

        return cbe

    def calc_cap_series_thru(self, freq, para_values, p_type):
        """Calculates the the series-thru junction capacitance cbc from the small signal parameters para_values.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        cbc           :  np.ndarray()
            Base collector junction capacitance as an array with shape [n_freq].
        """
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")

        # calculate GU
        return -np.imag(y_para_values[:, 0, 1]) / (2.0 * np.pi * freq)

    def calc_cap_shunt_port_2(self, freq, para_values, p_type):
        """Calculates the active shunt capacitance at port_2 assuming a PI equivalent circuit.

        Parameters
        ----------
        freq         :  np.ndarray()
            Frequencys that correspond to para_values.
        para_values  :  np.ndarray()
            Small signal parameters of type p_type with shape [n_freq, n_port, n_port]
        p_type       :  string
            Type of the small signal parameters in para_values.

        Returns
        -------
        cce           :  np.ndarray()
            Collector emitter junction capacitance as an array with shape [n_freq].
        """
        y_para_values = self.convert_n_port_para(para_values, p_type, "Y")

        # calculate cce from y para
        cce = np.imag(y_para_values[:, 1, 1] + y_para_values[:, 0, 1]) / (2.0 * np.pi * freq)

        return cce

    def calc_beta(self, ic, ib):
        """Calculates the base collector current amplification from dc currents

        Parameters
        ----------
        ic  :  np.ndarray()
            DC Collector current.
        ib  :  np.ndarray()
            DC Base current.

        Returns
        -------
        beta  :  np.ndarray()
            Base collector junction capacitance as an array with shape [n_freq].
        """
        return ic / ib  # I know this seems crazy, however it ist clean coding style.

    def calc_gm(self, ic, vbe, vb_forced=None, vc_forced=None):
        """Calculates the transconductance of a bjt or mosfet.

        Parameters
        ----------
        ic  :  np.ndarray()
            DC Collector current.
        vbe  :  np.ndarray()
            be voltage
        vbc  :  np.ndarray()
            bc voltage

        Returns
        -------
        gm  :  np.ndarray()
            The transconductance
        """
        # vb_forced is not necessarily increasing as needed for gm calculation, e.g. vb is not increasing at constant vc.
        # following code tries to catch that.

        gm = np.zeros_like(vbe)
        if vb_forced is not None and vc_forced is not None:
            vbc_forced = vb_forced - vc_forced
            # V_BC or V_C forced?
            vc_forced_unique = np.unique(np.round(vc_forced, decimals=3))
            vbc_forced_unique = np.unique(np.round(vbc_forced, decimals=3))
            vbc_unique = vbc_forced_unique.size < vc_forced_unique.size
            if vbc_unique:
                v_outer_unique = vbc_forced_unique
                v_outer = vbc_forced
            else:
                v_outer_unique = vc_forced_unique
                v_outer = vc_forced

            for v_out in v_outer_unique:
                indices = np.isclose(v_outer, v_out, rtol=1e-3, atol=4.99e-3)
                vb_unique, indicies_unique, unique_inverse = np.unique(
                    vb_forced[indices], return_index=True, return_inverse=True
                )
                sorted_indices = np.argsort(vb_unique)
                ic_unique = ic[indices][indicies_unique][sorted_indices]
                res = np.empty_like(ic_unique)
                res[sorted_indices] = (
                    np.gradient(np.log(np.abs(ic_unique)), vb_unique[sorted_indices], edge_order=2)
                    * ic_unique
                )
                gm[indices] = res[unique_inverse]

        elif vc_forced is None and vb_forced is None:
            resort = None
            # sort to increasing vbe
            if not strictly_increasing(vbe):
                vbe_indexes = vbe.argsort()
                resort = vbe_indexes.argsort()
                vbe = vbe[vbe_indexes]
                ic = ic[vbe_indexes]

            # calculate
            gm = np.gradient(np.log(np.abs(ic)), vbe) * ic

            if resort is not None:
                gm = gm[resort]

        else:
            raise NotImplementedError(
                "DMT data_processor -> combination of arguments not yet implemented."
            )

        return np.where(gm <= 0.0, np.nan, gm)

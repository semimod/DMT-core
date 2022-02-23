""" singleton

Provides a meta class to ensure single instantiation.

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


class Singleton(type):
    """Implements the Singleton design pattern. Classes that use this class as a metaclass can only be initiated once.

    If a new object of a singleton class is created, the already existing one is returned.
    Source: https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python

    Here something else is added: If a already existing object is "created" again, it tries to transfer the given kwargs to the old object.

    Examples
    --------

    The simulation controller should only exist once because of possible blocking of resources. This class is used to see singleton in action:

    >>> sim_con1 = SimCon(n_core=4)
    >>> sim_con1.n_core
    4

    If now a second simulation controller is created:

    >>> sim_con2 = SimCon(n_core=8)
    >>> sim_con2.n_core
    8

    The new attribute is overwritten with the new value. As the change is made to the already existing instance, this also has now 8 cores:

    >>> sim_con1.n_core
    8

    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
            obj = cls._instances[cls]
        else:
            obj = cls._instances[cls]
            if args:
                raise AttributeError(
                    "DMT: Can not set an value to an unknown attribute of the object.",
                    "Make sure, that all the wanted parameters are kwargs.",
                )

            # Try to set kwargs as parameters for the class.
            for attr, value in kwargs.items():
                if hasattr(obj, attr) and not callable(getattr(obj, attr)):
                    setattr(obj, attr, value)
                else:
                    raise AttributeError(
                        "DMT: Can not set an attribute which is not a member of the object"
                    )

        return obj

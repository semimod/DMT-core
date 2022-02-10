# test Hdev new python module
import COOSpy

path = "/home/markus/.DMT/simulation_results/coos_aeb809d9fb4fdddfdb18378820473068/gummel_0c4744220ce8be7a960285bc853386e1/coos_inp.din"
COOSpy.f90wrap_init(path)
mob = COOSpy.f90wrap_get_mobility_py("GaAs", "G", 0, 1, 1, 1, 300, 1, 1, 1, 0)
print(mob)
mob = COOSpy.f90wrap_get_mobility_py("GaAs", "G", 10e5, 1, 1, 1, 300, 1, 1, 1, 0)
print(mob)

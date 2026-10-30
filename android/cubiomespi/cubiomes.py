import ctypes, os, sys
import glob

# Try relative import first (when used as a package), fallback to absolute (when run locally)
try:
    from .constants import *
except ImportError:
    from constants import *

script_dir = os.path.dirname(os.path.abspath(__file__))

# Find the compiled C extension (setuptools adds platform-specific suffixes like .cpython-311-darwin.so or .pyd)
lib_files = glob.glob(os.path.join(script_dir, "lib_c.*"))
if not lib_files:
    raise FileNotFoundError("Compiled cubiomes library not found. Please install the package using pip.")

lib = ctypes.CDLL(lib_files[0])



class Generator:
    def __init__(self, mc: int, seed: int, dimension: int) -> None:
        self.version = mc
        self.seed = seed
        self.dimension = dimension

    def get_end_y_height(self, x: int, z: int) -> int:
        return get_end_y_height(self, x, z)

    def get_structure_pos(self, structure, rx: int, rz: int) -> tuple[int, int]:
        return get_structure_pos(structure, self, rx, rz)

    def is_viable_structure_pos(self, structure, x: int, z: int) -> bool:
        return is_viable_structure_pos(structure, self, x, z)

    def get_stronghold_pos(self, count=3) -> list[tuple[int, int]]:
        return get_stronghold_pos(self, count)

    def get_spawn_pos(self) -> tuple[int, int]:
        return get_spawn_pos(self)

    def get_biome_at(self, x: int, y: int, z: int):
        return get_biome_at(self, x, y, z)


    def get_bastion_variant(self, x: int, z: int) -> int:
        return get_bastion_variant(self, x, z)

    def find_structure_in_range(self, structure, srx: int, srz: int, erx: int, erz: int) -> list[tuple[int, int]]:
        return find_structure_in_range(self, structure, srx, srz, erx, erz)

    def find_closest_structure(self, structure, cx: int, cz: int, limit: int) -> tuple[int, int]:
        return find_closest_structure(self, structure, cx, cz, limit)




def __c(val: int, seed=False):
    if seed:
        return ctypes.c_uint64(val)
    else:
        return ctypes.c_int(val)



def get_end_y_height(g: Generator, x, z):
    cversion, cseed = __c(g.version), __c(g.seed, True)
    cx = __c(x)
    cz = __c(z)

    f = lib.INTERFACE_getSurfaceHeightEnd
    f.restype = ctypes.c_int
    f.argtypes = [ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
    y = f(cversion, cseed, cx, cz)

    return y


def get_structure_pos(structure: Structure, g: Generator, rx: int, rz: int) -> tuple[int, int]:
    cstructure = __c(structure)
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    crx = __c(rx)
    crz = __c(rz)  
    
    lib.INTERFACE_getStructurePos.restype = ctypes.POINTER(ctypes.c_int)
    lib.INTERFACE_getStructurePos.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
    ptr = lib.INTERFACE_getStructurePos(cstructure, cversion, cseed, crx, crz)
    coords = (ptr[0], ptr[1])
    if coords == (0,0):
        return None
    return coords


def is_viable_structure_pos(structure: Structure, g: Generator, x: int, z: int) -> bool:
    cstructure = __c(structure)
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    cdimension = __c(g.dimension)
    cx = __c(x)
    cz = __c(z)

    lib.INTERFACE_isViableStructurePos.restype = ctypes.c_int
    lib.INTERFACE_isViableStructurePos.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    ptr = lib.INTERFACE_isViableStructurePos(cstructure, cversion, cseed, cdimension, cx, cz)
    return ptr == 1


def get_stronghold_pos(g: Generator, count = 3) -> list[tuple[int, int]]:
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    lib.INTERFACE_getStrongholdPos.restype = ctypes.POINTER(ctypes.c_int)
    lib.INTERFACE_getStrongholdPos.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
    ptr = lib.INTERFACE_getStrongholdPos(cseed, cversion, count)
    sh_locs = [[ptr[2*i], ptr[2*i+1]] for i in range(count)]
    return sh_locs


def get_spawn_pos(g: Generator) -> tuple[int, int]:
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    f = lib.INTERFACE_getSpwan
    f.restype = ctypes.POINTER(ctypes.c_int)
    f.argtypes = [ctypes.c_uint64, ctypes.c_int]
    ptr = f(cseed, cversion)
    loc = (ptr[0], ptr[1])
    return loc


def get_biome_at(g: Generator, x: int, y: int, z: int) -> BiomeID:
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    cdimension = __c(g.dimension)
    cx = __c(x)
    cy = __c(y)
    cz = __c(z)
    f = lib.INTERFACE_getBiomeAt
    f.restype = ctypes.c_int
    f.argtypes = [ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    biome = f(cversion, cseed, cdimension, cx, cy, cz)
    try:
        from .constants import BiomeID
        return BiomeID(biome)
    except (ImportError, ValueError):
        return biome


def get_bastion_variant(g: Generator, x: int, z: int) -> BastionType:
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    cx = __c(x)
    cz = __c(z)
    f = lib.INTERFACE_getBastionVariant
    f.restype = ctypes.c_int
    f.argtypes = [ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
    variant = f(cversion, cseed, cx, cz)
    return variant



def find_structure_in_range(g: Generator, structure: Structure, srx: int, srz: int, erx: int, erz: int) -> list[tuple[int,int]]:
    cstructure = __c(structure)
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    cdimension = __c(g.dimension)
    csrx = __c(srx)
    csrz = __c(srz)
    cerx = __c(erx)
    cerz = __c(erz)

    lib.INTERFACE_find_in_range.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_int))
    lib.INTERFACE_find_in_range.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]

    ptrarr = lib.INTERFACE_find_in_range(cstructure, cversion, cseed, cdimension, csrx, csrz, cerx, cerz)
    structure_count = ptrarr[0][0]
    structure_array = [(ptrarr[i][0], ptrarr[i][1]) for i in range(1,structure_count)]

    if structure_array == []:
        return None
    return structure_array


def find_closest_structure(g: Generator, structure: Structure, cx: int, cz: int, limit: int) -> tuple[int, int]:
    cstructure = __c(structure)
    cversion = __c(g.version)
    cseed = __c(g.seed, True)
    cdimension = __c(g.dimension)
    ccx = __c(cx)
    ccz = __c(cz)
    climit = __c(limit)
    
    f = lib.INTERFACE_find_closest_structure
    f.restype = ctypes.POINTER(ctypes.c_int)
    f.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
    ptr = f(cstructure, cversion, cseed, cdimension, ccx, ccz, climit)

    coords = (ptr[0], ptr[1])
    if coords == (0,0):
        return None
    return coords
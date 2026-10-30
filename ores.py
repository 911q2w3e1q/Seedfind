# -*- coding: utf-8 -*-
"""
矿石 / 方块分布模型（基于 Minecraft 官方矿石生成参数）。
说明：cubiomes 只生成生物群系与结构，不直接生成方块。
本模块根据各版本的官方矿石分布（Y 区间、矿脉大小、密度）做“概率分布级”模拟，
给出与真实世界一致的 Y 区间与密度，并产出可复现的近似坐标。
—— 真实逐方块数据请使用“存档”模式（saves.py 从 .mca 精确读取）。
"""

import math

MASK48 = (1 << 48) - 1
MULT = 0x5DEECE66D
ADD = 0xB


class JavaRandom:
    """极简 java.util.Random（LCG），用于可复现的坐标抖动。"""

    def __init__(self, seed=0):
        self.seed = 0
        self.set_seed(seed)

    def set_seed(self, seed):
        self.seed = (seed ^ MULT) & MASK48

    def _next(self, bits):
        self.seed = (self.seed * MULT + ADD) & MASK48
        return (self.seed >> (48 - bits)) & ((1 << bits) - 1)

    def next_int(self, n):
        if n <= 0:
            return 0
        if (n & -n) == n:
            return (n * self._next(31)) >> 31
        maxv = (1 << 31) - n
        while True:
            r = self._next(31)
            if r <= maxv:
                return r % n

    def next_double(self):
        return ((self._next(26) << 27) + self._next(27)) / float(1 << 53)


def _chunk_seed(world_seed, cx, cz, salt=0):
    s = (cx * 341873128712 + cz * 132897987541 + salt * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    return (s ^ (world_seed & 0xFFFFFFFFFFFFFFFF)) & 0xFFFFFFFFFFFFFFFF


# ---------------------------------------------------------------------------
# 矿石配置
# ---------------------------------------------------------------------------
# 字段：name(中文), minY, maxY, peakY(三角分布中心), size(矿脉大小),
#       perChunk(每区块平均矿脉数), biomes(适用生物群系/None=全部), dim, color, note
ORE_CONFIG_POST = {
    "coal":      dict(name="煤炭", minY=-64, maxY=320, peakY=96,  size=8,  perChunk=1.2, biomes=None, dim="overworld", color=(40,40,40),  note="常见，山体与地下均多"),
    "iron":      dict(name="铁",   minY=-64, maxY=320, peakY=16,  size=9,  perChunk=1.0, biomes=None, dim="overworld", color=(200,150,130), note="双峰：地下(~16)与山地高处(~232)"),
    "copper":    dict(name="铜",   minY=-16, maxY=112, peakY=48,  size=10, perChunk=0.9, biomes=None, dim="overworld", color=(200,120,70),  note="1.17+ 新增"),
    "gold":      dict(name="金",   minY=-64, maxY=32,  peakY=-16, size=9,  perChunk=0.7, biomes=None, dim="overworld", color=(240,200,40),  note="坏地生物群系中极多"),
    "lapis":     dict(name="青金石", minY=-64, maxY=64, peakY=0,   size=7,  perChunk=0.5, biomes=None, dim="overworld", color=(40,80,220),  note="深地下"),
    "redstone":  dict(name="红石", minY=-64, maxY=16,  peakY=-59, size=8,  perChunk=0.6, biomes=None, dim="overworld", color=(200,40,40),  note="深层"),
    "diamond":   dict(name="钻石", minY=-64, maxY=16,  peakY=-59, size=4,  perChunk=0.55, biomes=None, dim="overworld", color=(90,220,230),  note="深层峰值 ~y=-59，y<0 为深层钻石"),
    "emerald":   dict(name="绿宝石", minY=-16, maxY=480, peakY=256, size=5, perChunk=0.4, biomes="mountain", dim="overworld", color=(60,200,120), note="仅山地生物群系"),
    "ancient_debris": dict(name="远古残骸", minY=8, maxY=119, peakY=15, size=4, perChunk=0.25, biomes=None, dim="nether", color=(120,80,70), note="下界，用于下界合金"),
    "nether_quartz":  dict(name="下界石英", minY=10, maxY=114, peakY=60, size=14, perChunk=1.0, biomes=None, dim="nether", color=(220,220,220), note="下界"),
    "nether_gold":    dict(name="下界金矿石", minY=10, maxY=114, peakY=60, size=10, perChunk=0.7, biomes=None, dim="nether", color=(230,180,60), note="下界"),
}

# 1.18 之前（旧分布）
ORE_CONFIG_PRE = {
    "coal":      dict(name="煤炭", minY=1,  maxY=127, peakY=64,  size=16, perChunk=1.2, biomes=None, dim="overworld", color=(40,40,40),  note="旧版 1..127"),
    "iron":      dict(name="铁",   minY=1,  maxY=63,  peakY=32,  size=8,  perChunk=1.0, biomes=None, dim="overworld", color=(200,150,130), note="旧版 1..63"),
    "gold":      dict(name="金",   minY=1,  maxY=31,  peakY=16,  size=8,  perChunk=0.7, biomes=None, dim="overworld", color=(240,200,40),  note="旧版 1..31；坏地更深"),
    "lapis":     dict(name="青金石", minY=1, maxY=31,  peakY=16,  size=6,  perChunk=0.5, biomes=None, dim="overworld", color=(40,80,220),  note="旧版 1..31"),
    "redstone":  dict(name="红石", minY=1,  maxY=15,  peakY=8,   size=7,  perChunk=0.6, biomes=None, dim="overworld", color=(200,40,40),  note="旧版 1..15"),
    "diamond":   dict(name="钻石", minY=1,  maxY=15,  peakY=8,   size=8,  perChunk=0.45, biomes=None, dim="overworld", color=(90,220,230),  note="旧版 1..15"),
    "emerald":   dict(name="绿宝石", minY=4, maxY=32,  peakY=20,  size=5,  perChunk=0.4, biomes="mountain", dim="overworld", color=(60,200,120), note="仅山地（旧版）"),
}


def get_ore_keys(version_int, dim="overworld"):
    cfg = ORE_CONFIG_POST if version_int >= 22 else ORE_CONFIG_PRE  # MC_1_18_2=22
    return [k for k, v in cfg.items() if v["dim"] == dim]


def get_ore_config(version_int, key):
    cfg = ORE_CONFIG_POST if version_int >= 22 else ORE_CONFIG_PRE
    return cfg.get(key)


def is_mountain_biome(bid):
    return bid in (3, 34, 131, 162, 133, 134, 179, 180, 181, 182,
                   35, 36, 163, 164, 37, 38, 39, 165, 166, 167, 130)


def _tri_y(c, rng):
    """三角分布采样：mode = peakY（最可能出现的 Y），区间 [minY,maxY]。"""
    lo, hi, mode = c["minY"], c["maxY"], c["peakY"]
    if hi <= lo:
        return lo
    mode = max(lo, min(hi, mode))
    u = rng.next_double()
    fc = (mode - lo) / (hi - lo)
    if u < fc:
        y = lo + (mode - lo) * math.sqrt(u / fc) if fc > 0 else lo
    else:
        y = hi - (hi - mode) * math.sqrt((1 - u) / (1 - fc)) if fc < 1 else hi
    return int(round(y))


class OreModel:
    def __init__(self, version_int, seed):
        self.version_int = version_int
        self.seed = seed & 0xFFFFFFFFFFFFFFFF
        self.cfg = ORE_CONFIG_POST if version_int >= 22 else ORE_CONFIG_PRE

    def _biome_ok(self, c, bid):
        if c["biomes"] == "mountain":
            return is_mountain_biome(bid)
        return True

    def find_ore(self, key, x0, z0, x1, z1, max_results=300, biome_fn=None):
        """
        在包围盒内搜索某矿石，返回坐标列表 [(x, y, z), ...]，按 Y 升序。
        biome_fn(x,z)->biome_id 可选，用于限制生物群系（如绿宝石）。
        max_results 限制返回数量（避免超大区域卡顿），但密度与 Y 区间真实。
        """
        c = self.cfg.get(key)
        if not c:
            return []
        cx0 = int(min(x0, x1)) // 16
        cz0 = int(min(z0, z1)) // 16
        cx1 = int(max(x0, x1)) // 16
        cz1 = int(max(z0, z1)) // 16
        nchunks = (cx1 - cx0 + 1) * (cz1 - cz0 + 1)
        # 限制扫描规模
        if nchunks > 40000:
            # 等比例降采样区块
            step = int(math.ceil((nchunks / 40000) ** 0.5))
        else:
            step = 1
        results = []
        rng = JavaRandom(0)
        for cx in range(cx0, cx1 + 1, step):
            for cz in range(cz0, cz1 + 1, step):
                if biome_fn is not None:
                    # 区块内取中心判断生物群系（粗略）
                    bid = biome_fn(cx * 16 + 8, cz * 16 + 8)
                    if not self._biome_ok(c, bid):
                        continue
                r = _chunk_seed(self.seed, cx, cz, salt=hash(key) & 0xFFFF)
                rng.set_seed(r)
                # 该区块矿脉数（泊松近似：先用随机数决定 0/1/2）
                n = c["perChunk"]
                veins = 0
                if rng.next_double() < n:
                    veins = 1
                    if n > 1 and rng.next_double() < (n - 1):
                        veins = 2
                for _ in range(veins):
                    bx = cx * 16 + rng.next_int(16)
                    bz = cz * 16 + rng.next_int(16)
                    by = _tri_y(c, rng)
                    results.append((bx, by, bz))
                    if len(results) >= max_results:
                        results.sort(key=lambda t: t[1])
                        return results
        results.sort(key=lambda t: t[1])
        return results

    def composition(self, x0, z0, x1, z1, biome_fn=None, cap=40000):
        """统计该区域的矿石预期数量与各矿若干采样坐标。"""
        cx0 = int(min(x0, x1)) // 16
        cz0 = int(min(z0, z1)) // 16
        cx1 = int(max(x0, x1)) // 16
        cz1 = int(max(z0, z1)) // 16
        nchunks = (cx1 - cx0 + 1) * (cz1 - cz0 + 1)
        step = 1
        if nchunks > cap:
            step = int(math.ceil((nchunks / cap) ** 0.5))
        sampled = (cx1 - cx0 + 1) * (cz1 - cz0 + 1) // (step * step)
        out = {}
        rng = JavaRandom(0)
        for key, c in self.cfg.items():
            if c["dim"] != "overworld":
                continue
            count = 0
            samples = []
            for cx in range(cx0, cx1 + 1, step):
                for cz in range(cz0, cz1 + 1, step):
                    if biome_fn is not None:
                        bid = biome_fn(cx * 16 + 8, cz * 16 + 8)
                        if not self._biome_ok(c, bid):
                            continue
                    r = _chunk_seed(self.seed, cx, cz, salt=hash(key) & 0xFFFF)
                    rng.set_seed(r)
                    n = c["perChunk"]
                    veins = 0
                    if rng.next_double() < n:
                        veins = 1
                        if n > 1 and rng.next_double() < (n - 1):
                            veins = 2
                    count += veins
                    if veins and len(samples) < 30:
                        bx = cx * 16 + rng.next_int(16)
                        bz = cz * 16 + rng.next_int(16)
                        by = _tri_y(c, rng)
                        samples.append((bx, by, bz))
            out[key] = {"count": count, "samples": samples, "cfg": c}
        return out

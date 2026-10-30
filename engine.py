# -*- coding: utf-8 -*-
"""
Minecraft Java 版世界生成引擎封装。
底层使用 cubiomespi（Cubiomes 的 Python 绑定）提供：
  - 全版本（MC 1.0 ~ 1.21）种子 -> 生物群系 / 结构定位
  - 结构坐标查询、出生点、要塞、生物群系地图渲染
本文件只依赖 cubiomespi，不直接生成方块（方块/矿石由 ores.py 用官方生成参数模拟，
已加载存档的方块由 saves.py 从 .mca 精确读取）。
"""
import math
import cubiomespi as cp

# ----------------------------------------------------------------------------
# 版本列表：把 cubiomespi 的 MCVersion 枚举转成友好名称
# ----------------------------------------------------------------------------
_VERSION_LABELS = {
    "MC_1_0_0": "1.0", "MC_1_1_0": "1.1", "MC_1_2_5": "1.2.5",
    "MC_1_3_2": "1.3.2", "MC_1_4_7": "1.4.7", "MC_1_5_2": "1.5.2",
    "MC_1_6_4": "1.6.4", "MC_1_7_10": "1.7.10", "MC_1_8_9": "1.8.9",
    "MC_1_9_4": "1.9.4", "MC_1_10_2": "1.10.2", "MC_1_11_2": "1.11.2",
    "MC_1_12_2": "1.12.2", "MC_1_13_2": "1.13.2", "MC_1_14_4": "1.14.4",
    "MC_1_15_2": "1.15.2", "MC_1_16_1": "1.16.1", "MC_1_16_5": "1.16.5",
    "MC_1_17_1": "1.17.1", "MC_1_18_2": "1.18.2", "MC_1_19": "1.19",
    "MC_1_19_2": "1.19.2", "MC_1_20": "1.20", "MC_1_21": "1.21",
}

VERSION_DEFAULT = "MC_1_20"


def get_versions():
    """返回 [(友好名称, 枚举整数值), ...]，按版本顺序排列。"""
    out = []
    for name, val in cp.MCVersion.__members__.items():
        out.append((_VERSION_LABELS.get(name, name), int(val)))
    # 按枚举整数值（即发布顺序）排序
    out.sort(key=lambda t: t[1])
    return out


def version_label_to_int(label):
    for name, val in cp.MCVersion.__members__.items():
        if _VERSION_LABELS.get(name, name) == label:
            return int(val)
    return int(cp.MCVersion.__members__[VERSION_DEFAULT])


def is_new_ore_model(version_int):
    """1.18（含）之后使用新的矿石分布模型。"""
    return version_int >= int(cp.MCVersion.MC_1_18_2)


# ----------------------------------------------------------------------------
# 结构列表：把 cubiomespi.Structure 的 (id, 名称) 元组暴露出来
# locatable=False 的结构（如矿井）按区块随机生成，无法精确定位单点。
# ----------------------------------------------------------------------------
def get_structures():
    """
    返回结构定义列表：
      {key, name(英文), cn(中文名), sid(整数结构ID), dim(维度), locatable(bool), y_note(str)}
    """
    cn_map = {
        "Desert_Pyramid": "沙漠神殿", "Jungle_Temple": "丛林神庙",
        "Jungle_Pyramid": "丛林神庙", "Swamp_Hut": "女巫小屋", "Igloo": "雪屋",
        "Village": "村庄", "Ocean_Ruin": "海底废墟", "Shipwreck": "沉船",
        "Monument": "海底神殿", "Mansion": "林地府邸", "Outpost": "掠夺者前哨站",
        "Ruined_Portal": "破损传送门", "Ruined_Portal_N": "破损传送门(下界)",
        "Ancient_City": "远古城市", "Treasure": "埋藏的宝藏", "Mineshaft": "矿井(随机生成)",
        "Desert_Well": "沙漠水井", "Geode": "紫晶洞", "Fortress": "下界要塞",
        "Bastion": "堡垒遗迹", "End_City": "末地城", "End_Gateway": "末地折跃门",
        "End_Island": "末地岛", "Trail_Ruin": "远古残迹", "Trial_Chambers": "试炼密室",
        "Feature": "特性",
    }
    items = []
    raw = []
    for key, val in cp.Structure.__dict__.items():
        if key.startswith("__") or key == "FEATURE_NUM":
            continue
        if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], int):
            raw.append((key, val[0], val[1]))
    # 维度归属（粗略）
    nether = {"Fortress", "Bastion", "Ruined_Portal_N"}
    end = {"End_City", "End_Gateway", "End_Island"}
    # 无法精确定位的结构
    not_locatable = {"Mineshaft", "Feature", "Desert_Well", "Geode", "Trail_Ruin"}
    for key, sid, name in raw:
        if key in nether:
            dim = "下界"
        elif key in end:
            dim = "末地"
        else:
            dim = "主世界"
        loc = key not in not_locatable
        y_note = _structure_y_note(key)
        items.append({
            "key": key, "name": name, "cn": cn_map.get(key, name), "sid": sid,
            "dim": dim, "locatable": loc, "y_note": y_note,
        })
    # 排序：按维度再按名称
    dim_order = {"主世界": 0, "下界": 1, "末地": 2}
    items.sort(key=lambda d: (dim_order[d["dim"]], d["name"]))
    return items


def _structure_y_note(key):
    notes = {
        "Swamp_Hut": "女巫小屋： floor 约在海平面附近（沼泽地表，通常 y≈62）",
        "Ancient_City": "远古城市：深暗之域，中心约 y=-20 ~ -52",
        "Monument": "海底神殿：中心约 y=58 ~ 62",
        "Mansion": "林地府邸：地表",
        "Village": "村庄：地表（平原/沙漠/热带草原/针叶林/雪原）",
        "Stronghold": "要塞：随地形起伏，无单一固定 Y",
        "Fortress": "下界要塞：下界地表附近",
        "Bastion": "堡垒遗迹：下界 y≈30 ~ 120",
        "End_City": "末地城：末地空岛 y≈60 ~ 90",
        "Ruined_Portal": "破损传送门：主世界/下界地表",
        "Trial_Chambers": "试炼密室：y≈-20 ~ -40",
        "Igloo": "雪屋：积雪生物群系地表",
        "Desert_Pyramid": "沙漠神殿：沙漠地表",
        "Jungle_Pyramid": "丛林神庙：丛林地表",
        "Ocean_Ruin": "海底废墟：海床附近",
        "Shipwreck": "沉船：海床/沙滩附近",
        "Outpost": "掠夺者前哨站：地表",
        "Treasure": "埋藏的宝藏：沙滩/海底 y≈40 ~ 60",
    }
    return notes.get(key, "地表生成（具体 Y 随地形）")


# ----------------------------------------------------------------------------
# 生成器与基础查询
# ----------------------------------------------------------------------------
def make_generator(version_int, seed, dimension=0):
    return cp.Generator(version_int, int(seed) & 0xFFFFFFFFFFFFFFFF, dimension)


def get_spawn(g):
    x, z = cp.get_spawn_pos(g)
    return x, z


def get_biome_id(g, x, y, z):
    return int(cp.get_biome_at(g, int(x), int(y), int(z)))


def get_strongholds(g, count=3):
    return [tuple(p) for p in cp.get_stronghold_pos(g, count)]


def find_structures_in_area(g, struct_sid, x0, z0, x1, z1):
    """
    在方块坐标包围盒 [x0..x1]×[z0..z1] 内查找某类结构。
    逐区域调用 get_structure_pos（find_in_range 的 ctypes 封装不稳定，故自实现）。
    返回 [(x, z), ...] 结构方块坐标。
    """
    rx0, rx1 = int(math.floor(min(x0, x1) / 512)), int(math.floor(max(x0, x1) / 512))
    rz0, rz1 = int(math.floor(min(z0, z1) / 512)), int(math.floor(max(z0, z1) / 512))
    out = []
    SID = int(struct_sid)
    for rx in range(rx0, rx1 + 1):
        for rz in range(rz0, rz1 + 1):
            pos = cp.get_structure_pos(SID, g, rx, rz)
            if not pos:
                continue
            x, z = int(pos[0]), int(pos[1])
            # get_structure_pos 只给出“候选”位置；必须用 is_viable_structure_pos
            # 校验该位置是否真的生成（生物群系/维度条件），否则会误报每个区域都有。
            try:
                if not cp.is_viable_structure_pos(SID, g, x, z):
                    continue
            except Exception:
                continue
            out.append((x, z))
    return out


def find_closest_structure(g, struct_sid, x, z, limit=4000):
    pos = cp.find_closest_structure(g, struct_sid, int(x), int(z), int(limit))
    if pos:
        return int(pos[0]), int(pos[1])
    return None


# ----------------------------------------------------------------------------
# 生物群系配色
# ----------------------------------------------------------------------------
BIOME_COLORS = {
    -1: (0, 0, 0),
    0: (48, 80, 168), 1: (122, 168, 72), 2: (194, 178, 128), 3: (120, 120, 120),
    4: (72, 120, 56), 5: (68, 104, 80), 6: (64, 96, 64), 7: (80, 112, 144),
    8: (128, 40, 40), 9: (64, 64, 160), 10: (80, 120, 168), 11: (88, 132, 176),
    12: (240, 240, 240), 13: (224, 224, 232), 14: (130, 130, 235), 15: (160, 160, 235),
    16: (192, 192, 160), 17: (184, 160, 96), 18: (96, 128, 64), 19: (96, 120, 80),
    20: (128, 128, 128), 21: (64, 128, 48), 22: (80, 144, 64), 23: (96, 144, 72),
    24: (32, 64, 144), 25: (112, 112, 120), 26: (160, 168, 176), 27: (96, 144, 80),
    28: (104, 152, 88), 29: (48, 96, 48), 30: (104, 136, 152), 31: (112, 144, 160),
    32: (80, 128, 80), 33: (88, 136, 88), 34: (112, 120, 80), 35: (160, 160, 80),
    36: (176, 168, 96), 37: (160, 96, 64), 38: (144, 112, 80), 39: (168, 120, 88),
    40: (80, 96, 112), 41: (96, 112, 128), 42: (112, 128, 144), 43: (128, 144, 160),
    44: (0, 128, 160), 45: (32, 144, 176), 46: (48, 96, 160), 47: (0, 96, 144),
    48: (0, 112, 160), 49: (0, 64, 128), 50: (0, 80, 144), 127: (0, 0, 0),
    129: (168, 196, 96), 130: (196, 180, 128), 131: (136, 136, 136), 132: (168, 184, 112),
    133: (96, 136, 104), 134: (72, 112, 80), 140: (224, 240, 248), 149: (72, 144, 64),
    151: (96, 152, 80), 155: (108, 152, 88), 156: (116, 160, 96), 157: (56, 104, 56),
    158: (112, 144, 160), 160: (92, 140, 92), 161: (100, 148, 100), 162: (144, 144, 144),
    163: (176, 176, 96), 164: (184, 184, 112), 165: (168, 80, 64), 166: (152, 120, 88),
    167: (176, 128, 96), 168: (88, 152, 80), 169: (96, 160, 88), 170: (96, 32, 32),
    171: (128, 48, 48), 172: (48, 96, 96), 173: (64, 56, 56), 174: (128, 96, 64),
    175: (72, 160, 80), 177: (156, 168, 160), 178: (132, 144, 160), 179: (144, 152, 168),
    180: (160, 144, 152), 181: (144, 136, 152), 182: (160, 152, 160), 183: (32, 32, 40),
    184: (112, 128, 96), 185: (240, 168, 184),
}


def biome_color(bid):
    return BIOME_COLORS.get(bid, (140, 140, 140))


# ----------------------------------------------------------------------------
# 生物群系地图渲染（返回 PIL 图像 + 采样网格，供 UI 显示与框选换算）
# ----------------------------------------------------------------------------
def generate_biome_map(g, center_x, center_z, width_px, height_px, blocks_per_px=1,
                       surface_y=64, callback=None):
    """
    以 (center_x, center_z) 为图像中心，生成生物群系彩色地图。
    返回 dict: image(PIL.Image), min_x, min_z, blocks_per_px
    """
    from PIL import Image
    min_x = int(center_x - width_px * blocks_per_px / 2)
    min_z = int(center_z - height_px * blocks_per_px / 2)
    img = Image.new("RGB", (width_px, height_px))
    px = img.load()
    total = width_px * height_px
    done = 0
    for py in range(height_px):
        z = min_z + py * blocks_per_px
        for pxx in range(width_px):
            x = min_x + pxx * blocks_per_px
            bid = int(cp.get_biome_at(g, x, surface_y, z))
            px[pxx, py] = biome_color(bid)
            done += 1
        if callback and (py % 8 == 0):
            callback(done / total)
    return {
        "image": img,
        "min_x": min_x, "min_z": min_z,
        "blocks_per_px": blocks_per_px,
    }


# ----------------------------------------------------------------------------
# 粗略地表高度估计（用于 3D 预览；非精确，仅形态参考）
# ----------------------------------------------------------------------------
def _hash2(x, z, seed):
    h = (x * 374761393 + z * 668265263 + seed * 2147483647) & 0xFFFFFFFFFFFFFFFF
    h = (h ^ (h >> 13)) * 1274126177 & 0xFFFFFFFFFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFFFF) / 0xFFFFFFFF


def _smooth_noise(x, z, seed, scale=64):
    gx = x / scale
    gz = z / scale
    x0 = math.floor(gx); z0 = math.floor(gz)
    fx = gx - x0; fz = gz - z0
    sx = fx * fx * (3 - 2 * fx); sz = fz * fz * (3 - 2 * fz)
    n00 = _hash2(x0, z0, seed); n10 = _hash2(x0 + 1, z0, seed)
    n01 = _hash2(x0, z0 + 1, seed); n11 = _hash2(x0 + 1, z0 + 1, seed)
    return (n00 * (1 - sx) + n10 * sx) * (1 - sz) + (n01 * (1 - sx) + n11 * sx) * sz


def estimate_height(g, x, z, surface_y=64):
    """基于生物群系类别 + 平滑噪声给出粗略地表高度（主世界）。"""
    bid = int(cp.get_biome_at(g, x, surface_y, z))
    # 生物群系基础高度与振幅
    if bid in (0, 10, 11, 24, 44, 45, 46, 47, 48, 49, 50):  # 海洋类
        base, amp = 40, 4
    elif bid in (16, 26, 15):  # 沙滩/蘑菇岸
        base, amp = 62, 2
    elif bid in (12, 13, 30, 31, 158, 140, 26):  # 雪原类
        base, amp = 70, 6
    elif bid in (3, 34, 179, 180, 181, 182, 131, 162, 133, 134):  # 山地类
        base, amp = 100, 40
    elif bid in (35, 36, 163, 164, 37, 38, 39, 165, 166, 167):  # 恶地/高原
        base, amp = 90, 30
    elif bid in (6, 184, 134):  # 沼泽/红树沼
        base, amp = 62, 2
    else:  # 平原/森林/丛林等
        base, amp = 70, 10
    n = _smooth_noise(x, z, 12345, 48)
    return int(base + (n - 0.5) * 2 * amp)


if __name__ == "__main__":
    print("versions:", [v[0] for v in get_versions()])
    print("structures count:", len(get_structures()))

# -*- coding: utf-8 -*-
"""
Minecraft 存档读取（仅已加载区块）。
使用 anvil-parser2 读取 .mca 区域文件，只能看到磁盘上实际存在的区块
（即玩家曾经加载/生成过的区块），不会凭空生成新区块。
"""
import os
import gzip
import zlib
import io
import threading
import anvil
from nbt.nbt import NBTFile

# 维度 -> 区域文件夹候选路径（按顺序尝试，优先新布局）。
# 1.21.x 及更早：主世界 region/、下界 DIM-1/region、末地 DIM1/region。
# 26.x（26.1 起，2026-03）：Mojang 把各维度移入 dimensions/minecraft/<dim>/region。
DIM_DIRS = {
    "主世界": ["region", os.path.join("dimensions", "minecraft", "overworld", "region")],
    "下界": [os.path.join("DIM-1", "region"),
             os.path.join("dimensions", "minecraft", "the_nether", "region")],
    "末地": [os.path.join("DIM1", "region"),
             os.path.join("dimensions", "minecraft", "the_end", "region")],
}


def _dim_dir(folder, dim):
    """返回该维度实际存在的区域目录（优先新布局），不存在则返回 None。"""
    for rel in DIM_DIRS.get(dim, []):
        p = os.path.join(folder, rel)
        if os.path.isdir(p):
            return p
    return None

# 常见方块配色（用于顶部方块地图渲染）
BLOCK_COLORS = {
    "grass_block": (96, 160, 72), "tall_grass": (96, 160, 72),
    "dirt": (134, 96, 64), "coarse_dirt": (134, 96, 64), "podzol": (110, 84, 60),
    "stone": (128, 128, 128), "andesite": (140, 132, 124), "diorite": (200, 200, 198),
    "granite": (160, 110, 90), "deepslate": (64, 64, 72), "bedrock": (40, 40, 40),
    "sand": (219, 201, 140), "sandstone": (210, 190, 130),
    "water": (48, 90, 200), "ice": (160, 200, 230), "packed_ice": (170, 210, 235),
    "snow_block": (240, 240, 248), "snow": (244, 244, 250), "powder_snow": (235, 240, 248),
    "grass": (96, 160, 72), "mycelium": (130, 96, 130), "gravel": (150, 140, 130),
    "terracotta": (160, 100, 70), "white_terracotta": (200, 190, 175),
    "clay": (150, 150, 170), "soul_sand": (110, 90, 70), "soul_soil": (100, 85, 65),
    "netherrack": (120, 40, 40), "basalt": (90, 90, 100), "blackstone": (50, 48, 55),
    "crimson_nylium": (150, 40, 60), "warped_nylium": (40, 120, 110),
    "end_stone": (220, 220, 150), "obsidian": (20, 12, 30), "air": (180, 200, 220),
}


def block_color(name):
    if name is None:
        return (180, 200, 220)
    key = name.split(":")[-1]
    return BLOCK_COLORS.get(key, (120, 120, 120))


def _read_level_dat(path):
    out = {}
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return out
    raw = None
    for offset in (0, 8):  # 现代 level.dat 有时带 8 字节头
        try:
            raw = gzip.decompress(data[offset:])
            break
        except Exception:
            raw = None
    if raw is None:
        try:
            raw = zlib.decompress(data)
        except Exception:
            return out
    try:
        nf = NBTFile(buffer=io.BytesIO(raw))
    except Exception:
        return out
    root = nf
    data_tag = root.get("Data") if root.get("Data") is not None else root
    try:
        seed = data_tag.get("Seed")
        if seed is not None:
            out["seed"] = int(seed.value)
    except Exception:
        pass
    try:
        lv = data_tag.get("LevelName")
        if lv is not None:
            out["name"] = str(lv.value)
    except Exception:
        pass
    try:
        ver = data_tag.get("Version")
        if ver is not None:
            nm = ver.get("Name")
            dv = ver.get("Id")
            if nm is not None:
                out["version_name"] = str(nm.value)
            if dv is not None:
                out["data_version"] = int(dv.value)
    except Exception:
        pass
    return out


class Save:
    def __init__(self, folder):
        self.folder = folder
        self.name = os.path.basename(os.path.normpath(folder))
        self.info = _read_level_dat(os.path.join(folder, "level.dat"))
        self._region_cache = {}
        self._lock = threading.Lock()

    def dimensions(self):
        out = []
        for dim in DIM_DIRS:
            if _dim_dir(self.folder, dim) is not None:
                out.append(dim)
        return out or ["主世界"]

    def _region_files(self, dim):
        p = _dim_dir(self.folder, dim)
        if p is None:
            return []
        files = []
        for fn in os.listdir(p):
            if fn.startswith("r.") and fn.endswith(".mca"):
                files.append(os.path.join(p, fn))
        return files

    def get_region(self, dim, rx, rz):
        key = (dim, rx, rz)
        with self._lock:
            if key in self._region_cache:
                return self._region_cache[key]
            for fp in self._region_files(dim):
                base = os.path.basename(fp)
                # r.RX.RZ.mca
                parts = base.split(".")
                if len(parts) >= 4 and parts[0] == "r":
                    try:
                        if int(parts[1]) == rx and int(parts[2]) == rz:
                            reg = anvil.Region.from_file(fp)
                            self._region_cache[key] = reg
                            return reg
                    except Exception:
                        continue
        return None

    def loaded_chunks(self, dim):
        """返回该维度所有已加载区块的全局区块坐标列表 [(cx, cz), ...]。"""
        out = []
        for fp in self._region_files(dim):
            base = os.path.basename(fp)
            parts = base.split(".")
            if len(parts) < 4 or parts[0] != "r":
                continue
            try:
                rx, rz = int(parts[1]), int(parts[2])
            except ValueError:
                continue
            reg = self.get_region(dim, rx, rz)
            if reg is None:
                continue
            for lx in range(32):
                for lz in range(32):
                    if reg.chunk_location(lx, lz) != (0, 0):
                        out.append((rx * 32 + lx, rz * 32 + lz))
        return out

    def get_block(self, dim, x, y, z):
        rx = x // 512
        rz = z // 512
        reg = self.get_region(dim, rx, rz)
        if reg is None:
            return None
        cx = x // 16
        cz = z // 16
        lx = cx - rx * 32
        lz = cz - rz * 32
        if reg.chunk_location(lx, lz) == (0, 0):
            return None
        try:
            chunk = anvil.Chunk.from_region(reg, lx, lz)
            b = chunk.get_block(x - cx * 16, y, z - cz * 16)
            return b.name() if b is not None else None
        except Exception:
            return None

    def find_blocks(self, dim, keyword, max_results=2000, chunk_limit=None,
                    x0=None, z0=None, x1=None, z1=None, callback=None):
        """
        在已加载区块中搜索方块名包含 keyword 的方块。
        可限定区域 [x0..x1]×[z0..z1]（区块坐标级别），chunk_limit 限制扫描区块数。
        返回 [(x, y, z, name), ...]
        """
        keyword = keyword.lower()
        results = []
        chunks = self.loaded_chunks(dim)
        if x0 is not None:
            cx0, cx1 = int(min(x0, x1)) // 16, int(max(x0, x1)) // 16
            cz0, cz1 = int(min(z0, z1)) // 16, int(max(z0, z1)) // 16
            chunks = [(c[0], c[1]) for c in chunks
                      if cx0 <= c[0] <= cx1 and cz0 <= c[1] <= cz1]
        if chunk_limit:
            chunks = chunks[:chunk_limit]
        total = len(chunks)
        for i, (cx, cz) in enumerate(chunks):
            rx, rz = cx // 32, cz // 32
            lx, lz = cx - rx * 32, cz - rz * 32
            reg = self.get_region(dim, rx, rz)
            if reg is None or reg.chunk_location(lx, lz) == (0, 0):
                continue
            try:
                chunk = anvil.Chunk.from_region(reg, lx, lz)
            except Exception:
                continue
            # 扫描 0..319 层（含下界/末地的大致范围）
            for y in range(-64, 320):
                for bx in range(16):
                    for bz in range(16):
                        try:
                            b = chunk.get_block(bx, y, bz)
                        except Exception:
                            b = None
                        if b is None:
                            continue
                        nm = b.name()
                        if keyword in nm.lower():
                            results.append((cx * 16 + bx, y, cz * 16 + bz, nm))
                            if len(results) >= max_results:
                                if callback:
                                    callback(1.0)
                                return results
            if callback and total:
                callback((i + 1) / total)
        return results

    def count_blocks(self, dim, x0, z0, x1, z1, chunk_limit=1200, callback=None):
        """
        统计已加载区域中各方块出现次数（顶部及地下扫描，带区块上限以防卡顿）。
        返回 collections.Counter {方块名: 次数}。
        """
        from collections import Counter
        cnt = Counter()
        cx0, cx1 = int(min(x0, x1)) // 16, int(max(x0, x1)) // 16
        cz0, cz1 = int(min(z0, z1)) // 16, int(max(z0, z1)) // 16
        chunks = [(c[0], c[1]) for c in self.loaded_chunks(dim)
                  if cx0 <= c[0] <= cx1 and cz0 <= c[1] <= cz1]
        if chunk_limit:
            chunks = chunks[:chunk_limit]
        total = len(chunks)
        for i, (cx, cz) in enumerate(chunks):
            rx, rz = cx // 32, cz // 32
            lx, lz = cx - rx * 32, cz - rz * 32
            reg = self.get_region(dim, rx, rz)
            if reg is None or reg.chunk_location(lx, lz) == (0, 0):
                continue
            try:
                chunk = anvil.Chunk.from_region(reg, lx, lz)
            except Exception:
                continue
            for y in range(-64, 256):
                for bx in range(16):
                    for bz in range(16):
                        try:
                            b = chunk.get_block(bx, y, bz)
                        except Exception:
                            b = None
                        if b is None:
                            continue
                        nm = b.name()
                        if "air" in nm or "cave_air" in nm or "void_air" in nm:
                            continue
                        cnt[nm] += 1
            if callback and total:
                callback((i + 1) / total)
        return cnt

    def render_top_map(self, dim, center_x, center_z, width_px, height_px,
                       blocks_per_px=4, y_top=320, y_bottom=-64, y_step=3,
                       callback=None):
        """
        渲染已加载区域的“顶部方块”地图（真实方块）。
        每个像素对应 blocks_per_px 个方块；只渲染已加载区块，未加载处留灰。
        """
        from PIL import Image
        min_x = int(center_x - width_px * blocks_per_px / 2)
        min_z = int(center_z - height_px * blocks_per_px / 2)
        img = Image.new("RGB", (width_px, height_px), (60, 60, 60))
        px = img.load()
        # 预计算已加载区块集合
        loaded = set(self.loaded_chunks(dim))
        # 区块顶部高度缓存：每个已加载区块只扫描一次顶部
        top_cache = {}

        def chunk_top(cx, cz):
            if (cx, cz) in top_cache:
                return top_cache[(cx, cz)]
            top = None
            for y in range(y_top, y_bottom - 1, -y_step):
                nm = self.get_block(dim, cx * 16 + 8, y, cz * 16 + 8)
                if nm and "air" not in nm and "cave_air" not in nm \
                        and "void_air" not in nm:
                    top = nm
                    break
            if top is None:
                top = self.get_block(dim, cx * 16 + 8, y_bottom, cz * 16 + 8)
            top_cache[(cx, cz)] = top
            return top

        total = width_px * height_px
        done = 0
        for py in range(height_px):
            z = min_z + py * blocks_per_px
            cz = z // 16
            for pxx in range(width_px):
                x = min_x + pxx * blocks_per_px
                cx = x // 16
                if (cx, cz) not in loaded:
                    done += 1
                    continue
                # 用区块顶部代表该列（已缓存，保证性能）
                px[pxx, py] = block_color(chunk_top(cx, cz))
                done += 1
            if callback and (py % 8 == 0):
                callback(done / total)
        return {
            "image": img,
            "min_x": min_x, "min_z": min_z,
            "blocks_per_px": blocks_per_px,
        }


if __name__ == "__main__":
    # 自测：用 anvil 创建一个临时区域并读回
    import tempfile
    reg = anvil.EmptyRegion(0, 0)
    stone = anvil.Block("minecraft", "stone")
    diamond = anvil.Block("minecraft", "diamond_ore")
    for y in range(0, 10):
        reg.set_block(stone, 0, y, 0)
    reg.set_block(diamond, 0, 5, 0)
    tmp = tempfile.mktemp(suffix=".mca")
    reg.save(tmp)
    r2 = anvil.Region.from_file(tmp)
    c = anvil.Chunk.from_region(r2, 0, 0)
    print("read back:", c.get_block(0, 5, 0).name)
    print("OK saves module")

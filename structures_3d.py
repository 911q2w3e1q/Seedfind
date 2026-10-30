# -*- coding: utf-8 -*-
"""
结构 3D 形状数据（简化/示意模型）。

重要说明：
  Minecraft 每个结构的“精确逐方块布局”需要专门的逆向数据，这里用
  “近似包围盒 + 风格化实体”来直观呈现结构的大小、比例与大致外形。
  尺寸取自真实结构的近似尺寸（单位：方块），用于预览与尺寸参考，并非逐方块还原。

  坐标约定（局部，单位方块）：
    - x/z 以结构中心为原点（左右/前后对称）；
    - y 以“地表基准”为 0，往上为正、往下为负（地下结构 yoff<0）。
  绘制时再平移到世界坐标 (origin_x, ground_y, origin_z)。
"""
import math

# 每个可定位结构的风格化模型参数
#   cn     中文名
#   color  主体颜色（hex）
#   w,d,h  包围盒尺寸（x 方向, z 方向, 高度）
#   yoff   整体相对地表基准的下沉量（地下结构为负）
#   style  渲染风格
MODELS = {
    "Desert_Pyramid":   dict(cn="沙漠神殿",     color="#d9b36b", w=21, d=21, h=25, yoff=0,   style="pyramid"),
    "Jungle_Temple":    dict(cn="丛林神庙",     color="#6b8f3a", w=12, d=15, h=12, yoff=0,   style="box"),
    "Jungle_Pyramid":   dict(cn="丛林神庙",     color="#6b8f3a", w=12, d=15, h=12, yoff=0,   style="box"),
    "Swamp_Hut":        dict(cn="女巫小屋",     color="#6e5a3c", w=7,  d=9,  h=7,  yoff=0,   style="hut"),
    "Igloo":            dict(cn="雪屋",         color="#e8eef5", w=7,  d=7,  h=5,  yoff=0,   style="hut"),
    "Village":          dict(cn="村庄",         color="#b08858", w=24, d=24, h=8,  yoff=0,   style="cluster"),
    "Ocean_Ruin":        dict(cn="海底废墟",     color="#9aa6a0", w=10, d=10, h=8,  yoff=-2,  style="box"),
    "Shipwreck":        dict(cn="沉船",         color="#7a5a3a", w=14, d=7,  h=6,  yoff=-3,  style="box"),
    "Monument":         dict(cn="海底神殿",     color="#c9cdd2", w=21, d=21, h=22, yoff=-3,  style="monument"),
    "Mansion":          dict(cn="林地府邸",     color="#6b4f33", w=20, d=20, h=14, yoff=0,   style="box"),
    "Outpost":          dict(cn="掠夺者前哨站", color="#7a6a4a", w=9,  d=9,  h=16, yoff=0,   style="tower"),
    "Ruined_Portal":    dict(cn="破损传送门",   color="#7d6b8a", w=6,  d=6,  h=7,  yoff=0,   style="box"),
    "Ruined_Portal_N":  dict(cn="破损传送门(下界)", color="#7d6b8a", w=6, d=6, h=7, yoff=0,  style="box"),
    "Ancient_City":     dict(cn="远古城市",     color="#3a3f4a", w=26, d=26, h=18, yoff=-2,  style="city"),
    "Treasure":         dict(cn="埋藏的宝藏",   color="#caa15a", w=2,  d=2,  h=2,  yoff=-2,  style="box"),
    "Mineshaft":        dict(cn="矿井",         color="#6b5640", w=20, d=20, h=10, yoff=-10, style="box"),
    "Trial_Chambers":   dict(cn="试炼密室",     color="#9a7b4f", w=22, d=22, h=12, yoff=-12, style="box"),
    "Fortress":         dict(cn="下界要塞",     color="#5a3a3a", w=20, d=20, h=18, yoff=0,   style="box"),
    "Bastion":          dict(cn="堡垒遗迹",     color="#4a3a5a", w=22, d=22, h=20, yoff=0,   style="box"),
    "End_City":         dict(cn="末地城",       color="#9aa0c0", w=10, d=10, h=24, yoff=0,   style="tower"),
    "End_Gateway":      dict(cn="末地折跃门",   color="#7ad0ff", w=3,  d=3,  h=3,  yoff=0,   style="box"),
    "End_Island":       dict(cn="末地岛",       color="#cfcac0", w=20, d=20, h=12, yoff=-6,  style="box"),
    "Trail_Ruin":       dict(cn="远古残迹",     color="#8a7a5a", w=10, d=10, h=7,  yoff=0,   style="box"),
}


def _box(x0, z0, y0, w, d, h):
    """返回一个轴对齐盒子的局部坐标 (x0,y0,z0,x1,y1,z1)。"""
    return (x0, y0, z0, x0 + w, y0 + h, z0 + d)


def _center(w, d):
    """以中心为原点时，盒子的 x0/z0 起点。"""
    return -w / 2.0, -d / 2.0


def build_boxes(key):
    """返回某结构的局部坐标盒子列表 [(x0,y0,z0,x1,y1,z1), ...]。"""
    m = MODELS.get(key)
    if not m:
        return []
    w, d, h, yoff, style = m["w"], m["d"], m["h"], m["yoff"], m["style"]
    cx0, cz0 = _center(w, d)
    boxes = []

    if style == "box":
        boxes.append(_box(cx0, cz0, yoff, w, d, h))

    elif style == "hut":
        # 墙体 + 尖顶
        body_h = max(2, h * 0.6)
        boxes.append(_box(cx0, cz0, yoff, w, d, body_h))
        boxes.append(_box(cx0, cz0, yoff + body_h, w, d, h - body_h))

    elif style == "pyramid":
        # 阶梯金字塔（3 层）
        b1 = max(2, h * 0.45)
        b2 = max(2, h * 0.32)
        boxes.append(_box(cx0, cz0, yoff, w, d, b1))
        boxes.append(_box(cx0 * 0.7, cz0 * 0.7, yoff + b1, w * 0.7, d * 0.7, b2))
        boxes.append(_box(cx0 * 0.4, cz0 * 0.4, yoff + b1 + b2, w * 0.4, d * 0.4,
                          h - b1 - b2))

    elif style == "tower":
        # 中央高塔 + 底座
        boxes.append(_box(cx0, cz0, yoff, w, d, h * 0.25))
        tw = w * 0.5
        boxes.append(_box(cx0 + (w - tw) / 2, cz0 + (d - tw) / 2,
                          yoff + h * 0.25, tw, tw, h * 0.75))

    elif style == "monument":
        # 底座 + 中央立柱 + 顶部房间
        b1 = max(3, h * 0.4)
        boxes.append(_box(cx0, cz0, yoff, w, d, b1))
        cw = w * 0.28
        boxes.append(_box(cx0 + (w - cw) / 2, cz0 + (d - cw) / 2,
                          yoff + b1, cw, cw, h - b1 - 3))
        boxes.append(_box(cx0 + (w - cw) / 2, cz0 + (d - cw) / 2,
                          yoff + h - 3, cw * 1.6, cw * 1.6, 3))

    elif style == "city":
        # 平台 + 中央“远古回响”框 + 若干立柱
        boxes.append(_box(cx0, cz0, yoff, w, d, 2))
        fw = 6
        boxes.append(_box(cx0 + (w - fw) / 2, cz0 + (d - fw) / 2,
                          yoff + 2, fw, fw, h - 2))
        for dx, dz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            pw = 3
            boxes.append(_box(cx0 + (w - pw) / 2 + dx * w * 0.32,
                              cz0 + (d - pw) / 2 + dz * d * 0.32,
                              yoff + 2, pw, pw, h * 0.5))

    elif style == "cluster":
        # 村庄：若干小屋散布
        spots = [(-w * 0.3, -d * 0.3), (w * 0.25, -d * 0.2),
                 (-w * 0.1, d * 0.28), (w * 0.3, d * 0.3), (0, 0)]
        for i, (sx, sz) in enumerate(spots):
            hw, hd = 5, 5
            hhouse = 4 + (i % 2)
            boxes.append(_box(sx - hw / 2, sz - hd / 2, yoff, hw, hd, hhouse))
            boxes.append(_box(sx - hw / 2, sz - hd / 2, yoff + hhouse,
                              hw, hd, 2))  # 屋顶
    else:
        boxes.append(_box(cx0, cz0, yoff, w, d, h))

    return boxes


def get_model(key):
    """返回 {cn, color, w, d, h, yoff, style, boxes}。没有则返回 None。"""
    m = MODELS.get(key)
    if not m:
        return None
    out = dict(m)
    out["boxes"] = build_boxes(key)
    return out


def model_extent(key):
    """返回模型在局部坐标的包围范围，用于设置 3D 视角。"""
    boxes = build_boxes(key)
    if not boxes:
        return (0, 0, 0, 0, 0, 0)
    xs = [v for b in boxes for v in (b[0], b[3])]
    ys = [v for b in boxes for v in (b[1], b[4])]
    zs = [v for b in boxes for v in (b[2], b[5])]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


# ---------------------------------------------------------------------------
# matplotlib 3D 绘制（桌面与 Kivy 内嵌 matplotlib 共用）
# ---------------------------------------------------------------------------
def _draw_box(ax, x0, y0, z0, x1, y1, z1, color, alpha=0.55):
    """在 3D 轴上画一个盒子（半透明面 + 边框）。坐标系：x,y,z。"""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3D

    # 6 个面（每个面是 4 个角点）
    faces = [
        [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],  # -z
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],  # +z
        [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],  # -x
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],  # +x
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],  # -y
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],  # +y
    ]
    poly = Poly3DCollection(faces, alpha=alpha, facecolor=color,
                            edgecolor="black", linewidth=0.6)
    ax.add_collection3d(poly)

    # 12 条棱
    edges = [
        (x0, y0, z0, x1, y0, z0), (x1, y0, z0, x1, y1, z0),
        (x1, y1, z0, x0, y1, z0), (x0, y1, z0, x0, y0, z0),
        (x0, y0, z1, x1, y0, z1), (x1, y0, z1, x1, y1, z1),
        (x1, y1, z1, x0, y1, z1), (x0, y1, z1, x0, y0, z1),
        (x0, y0, z0, x0, y0, z1), (x1, y0, z0, x1, y0, z1),
        (x1, y1, z0, x1, y1, z1), (x0, y1, z0, x0, y1, z1),
    ]
    for e in edges:
        ax.add_line(Line3D([e[0], e[3]], [e[1], e[4]], [e[2], e[5]],
                           color="black", linewidth=0.8))


def draw_model_3d(ax, key, origin_x, origin_z, ground_y=0, title=None,
                  show_axes=True):
    """
    在 3D 轴上绘制结构模型（平移到世界坐标）。
    参数：
      ax         matplotlib 3D 轴
      key        结构 key（如 Swamp_Hut）
      origin_x/origin_z  结构所在的方块坐标（对应 get_structure_pos 的结果）
      ground_y  该处地表高度（模型 y=0 基准）
      title     标题
    返回 True/False（是否成功绘制）。
    """
    m = get_model(key)
    if not m:
        return False

    for (lx0, ly0, lz0, lx1, ly1, lz1) in m["boxes"]:
        # 平移到世界坐标：y 方向叠加地表高度
        _draw_box(ax,
                  lx0 + origin_x, ly0 + ground_y, lz0 + origin_z,
                  lx1 + origin_x, ly1 + ground_y, lz1 + origin_z,
                  m["color"], alpha=0.6)

    # 视角自适应
    ext = model_extent(key)
    cx = (ext[0] + ext[3]) / 2 + origin_x
    cy = (ext[1] + ext[4]) / 2 + ground_y
    cz = (ext[2] + ext[5]) / 2 + origin_z
    span = max(ext[3] - ext[0], ext[4] - ext[1], ext[5] - ext[2], 1) * 1.4
    ax.set_xlim(cx - span / 2, cx + span / 2)
    ax.set_ylim(cy - span / 2, cy + span / 2)
    ax.set_zlim(min(ground_y + ext[1], ground_y - span / 2),
                ground_y + ext[4] + span / 2)

    ax.set_xlabel("X")
    ax.set_ylabel("Y (高度)")
    ax.set_zlabel("Z")
    if title:
        ax.set_title(title)
    if not show_axes:
        ax.set_axis_off()
    return True

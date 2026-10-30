# -*- coding: utf-8 -*-
"""
Minecraft 种子查询器 —— 安卓版（Kivy）
复用桌面版同一套引擎逻辑：engine / ores / saves / structures_3d。
功能：种子查询（版本/维度/生物群系地图/结构搜索+Y距离筛选/矿石方块搜索/
      框选区域/3D 预览/结构 3D 形状）、存档查询（仅已加载区块）。

构建与安装见同目录 README_android.md。
"""
import os
import sys
import math
import threading

os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.core.window import Window

# 让 matplotlib 使用 Kivy 后端（用于 3D 预览 / 结构 3D 形状）
import matplotlib
matplotlib.use("KivyAgg")

import engine
import ores
import saves
import structures_3d

DIM_MAP = {"主世界": 0, "下界": -1, "末地": 1}
STRUCT_COLOR = (1, 0.27, 0.27, 1)
SEED_STRUCT_DEFS = engine.get_structures()


# ---------------------------------------------------------------------------
# 地图控件：2D 地图（平移 / 缩放 / 框选）+ 结构覆盖点
# 世界坐标 <-> 屏幕坐标映射与桌面版一致（采用渲染分辨率 + 拉伸显示）
# ---------------------------------------------------------------------------
class MapWidget(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.center_x = 0
        self.center_z = 0
        self.bpp = 8                      # 每个“渲染像素”代表的方块数（缩放档位）
        self.render_w = 200
        self.render_h = 200
        self.image = None
        self.tex = None
        self.mode = "pan"                  # 'pan' 或 'select'
        self.selection = None              # (wx0,wz0,wx1,wz1)
        self.structures = []               # (wx,wz,color,label)
        self._sel_start = None
        self._pan_start = None
        self.render_cb = None              # fn(cx,cz,rw,rh,bpp)->PIL.Image
        self.bind(size=self._redraw)

    # ---- 缩放系数（渲染分辨率 -> 显示像素）----
    @property
    def scale_x(self):
        return self.render_w / self.width if self.width else 1

    @property
    def scale_z(self):
        return self.render_h / self.height if self.height else 1

    @property
    def bpp_eff_x(self):
        return self.bpp * self.scale_x

    @property
    def bpp_eff_z(self):
        return self.bpp * self.scale_z

    def set_image(self, pil):
        if pil.mode != "RGB":
            pil = pil.convert("RGB")
        self.image = pil
        self._update_tex()
        self._redraw()

    def _update_tex(self):
        if self.image is None:
            self.tex = None
            return
        from kivy.graphics.texture import Texture
        buf = self.image.tobytes()
        tex = Texture.create(size=self.image.size, colorfmt="rgb")
        tex.blit_buffer(buf, colorfmt="rgb", bufferfmt="ubyte")
        self.tex = tex

    def render(self):
        if self.render_cb is None:
            return
        img = self.render_cb(self.center_x, self.center_z,
                             self.render_w, self.render_h, self.bpp)
        if img is not None:
            self.set_image(img)

    def zoom(self, factor):
        self.bpp = max(1, min(64, int(round(self.bpp * factor))))
        self.render()

    def reset_view(self, cx, cz):
        self.center_x, self.center_z = cx, cz
        self.render()

    def screen_to_world(self, px, py):
        minx = self.center_x - self.render_w * self.bpp / 2
        minz = self.center_z - self.render_h * self.bpp / 2
        return int(minx + px * self.bpp_eff_x), int(minz + py * self.bpp_eff_z)

    def world_to_screen(self, wx, wz):
        minx = self.center_x - self.render_w * self.bpp / 2
        minz = self.center_z - self.render_h * self.bpp / 2
        return (wx - minx) / self.bpp_eff_x, (wz - minz) / self.bpp_eff_z

    def view_bounds(self):
        w = self.render_w * self.bpp
        h = self.render_h * self.bpp
        return (int(self.center_x - w / 2), int(self.center_z - h / 2),
                int(self.center_x + w / 2), int(self.center_z + h / 2))

    def set_structures(self, lst):
        self.structures = lst
        self._redraw()

    def clear_structures(self):
        self.structures = []
        self.selection = None
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        with self.canvas:
            if self.tex:
                Rectangle(texture=self.tex, pos=(0, 0), size=self.size)
            # 结构点
            for wx, wz, color, _ in self.structures:
                sx, sy = self.world_to_screen(wx, wz)
                if -12 <= sx <= self.width + 12 and -12 <= sy <= self.height + 12:
                    Color(*color)
                    Rectangle(pos=(sx - 4, sy - 4), size=(8, 8))
            # 选区
            if self.selection:
                x0, z0, x1, z1 = self.selection
                sx0, sy0 = self.world_to_screen(x0, z0)
                sx1, sy1 = self.world_to_screen(x1, z1)
                Color(1, 0.8, 0, 1)
                Line(rectangle=(min(sx0, sx1), min(sy0, sy1),
                                abs(sx1 - sx0), abs(sy1 - sy0)), dash_offset=4)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.mode == "select" and touch.button in ("left", ""):
                self._sel_start = touch.pos
                return True
            self._pan_start = (touch.x, touch.y, self.center_x, self.center_z)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.mode == "select" and self._sel_start:
            wx0, wz0 = self.screen_to_world(*self._sel_start)
            wx1, wz1 = self.screen_to_world(touch.x, touch.y)
            self.selection = (wx0, wz0, wx1, wz1)
            self._redraw()
            return True
        if self._pan_start:
            x0, y0, cx, cz = self._pan_start
            dx = (touch.x - x0) * self.bpp_eff_x
            dy = (touch.y - y0) * self.bpp_eff_z
            self.center_x = cx - dx
            self.center_z = cz - dy
            self.render()
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.mode == "select" and self._sel_start:
            self._sel_start = None
            return True
        self._pan_start = None
        return super().on_touch_up(touch)


def run_bg(work, done, *args):
    """后台线程执行 work()，完成通过 Clock 回调 done(result)。"""
    def _run():
        try:
            res = ("ok", work())
        except Exception as ex:
            res = ("error", str(ex))
        Clock.schedule_once(lambda dt: done(res), 0)
    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# 种子查询界面
# ---------------------------------------------------------------------------
class SeedScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "seed"
        self.gen = None
        self.version_int = None
        self.dim = 0
        self.struct_items = []
        self.ore_items = []
        self.struct_points = []
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=6, spacing=4)

        # 顶部控制
        top = GridLayout(cols=3, size_hint_y=None, height=30, spacing=4)
        self.seed_in = TextInput(text="123456789", multiline=False)
        top.add_widget(Label(text="种子"))
        top.add_widget(self.seed_in)
        self.btn_rand = Button(text="随机")
        self.btn_rand.bind(on_press=lambda x: self._random_seed())
        top.add_widget(self.btn_rand)
        root.add_widget(top)

        ver = GridLayout(cols=3, size_hint_y=None, height=30, spacing=4)
        self.ver_spin = Spinner(text="26.3", values=[v[0] for v in engine.get_versions()])
        self.ver_spin.bind(text=self._on_ver_change)
        ver.add_widget(Label(text="版本"))
        ver.add_widget(self.ver_spin)
        self.dim_spin = Spinner(text="主世界", values=list(DIM_MAP.keys()))
        self.dim_spin.bind(text=self._on_dim_change)
        ver.add_widget(self.dim_spin)
        root.add_widget(ver)

        mid = GridLayout(cols=2, size_hint_y=None, height=30, spacing=4)
        self.btn_gen = Button(text="生成 / 刷新地图")
        self.btn_gen.bind(on_press=lambda x: self._on_generate())
        mid.add_widget(self.btn_gen)
        self.pb = matplotlib_progress()
        mid.add_widget(self.pb)
        root.add_widget(mid)

        nav = GridLayout(cols=5, size_hint_y=None, height=30, spacing=4)
        for t, f in [("放大", lambda: self.map.zoom(0.7)),
                     ("缩小", lambda: self.map.zoom(1.4)),
                     ("回出生点", self._reset_view),
                     ("清除选择", lambda: self.map.clear_structures()),
                     ("框选模式", self._toggle_select)]:
            b = Button(text=t)
            b.bind(on_press=lambda x, ff=f: ff())
            nav.add_widget(b)
        root.add_widget(nav)

        # 地图 + 结果
        body = BoxLayout(orientation="horizontal", spacing=4)
        self.map = MapWidget(size_hint=(0.62, 1))
        self.map.render_cb = self._render_cb
        body.add_widget(self.map)

        right = BoxLayout(orientation="vertical", spacing=4)
        self.sel_label = Label(text="选区：未选择（使用整张地图范围）", size_hint_y=None, height=24)
        right.add_widget(self.sel_label)
        self.result_box = _ResultList()
        right.add_widget(self.result_box)

        btn3d = Button(text="一键 3D 预览", size_hint_y=None, height=34)
        btn3d.bind(on_press=lambda x: self._on_3d())
        right.add_widget(btn3d)
        body.add_widget(right)
        root.add_widget(body)

        # 结构查询
        struct = GridLayout(cols=3, size_hint_y=None, height=30, spacing=4)
        self.struct_spin = Spinner(text="", values=[])
        struct.add_widget(Label(text="结构"))
        struct.add_widget(self.struct_spin)
        b = Button(text="查看结构 3D 形状")
        b.bind(on_press=lambda x: self._on_view_struct_3d())
        struct.add_widget(b)
        root.add_widget(struct)

        yz = GridLayout(cols=4, size_hint_y=None, height=30, spacing=4)
        self.y_min = TextInput(hint_text="Y下限", multiline=False)
        self.y_max = TextInput(hint_text="Y上限", multiline=False)
        self.dist = TextInput(text="30000", hint_text="距出生点上限", multiline=False)
        yz.add_widget(Label(text="Y范围"))
        yz.add_widget(self.y_min)
        yz.add_widget(self.y_max)
        yz.add_widget(self.dist)
        root.add_widget(yz)

        sbtn = GridLayout(cols=2, size_hint_y=None, height=30, spacing=4)
        b1 = Button(text="搜索选区内结构")
        b1.bind(on_press=lambda x: self._on_search_struct("area"))
        b2 = Button(text="按半径搜附近")
        b2.bind(on_press=lambda x: self._on_search_struct("radius"))
        sbtn.add_widget(b1); sbtn.add_widget(b2)
        root.add_widget(sbtn)

        # 矿石 / 方块
        ore = GridLayout(cols=3, size_hint_y=None, height=30, spacing=4)
        self.ore_spin = Spinner(text="", values=[])
        ore.add_widget(Label(text="方块"))
        ore.add_widget(self.ore_spin)
        b3 = Button(text="搜索该方块坐标")
        b3.bind(on_press=lambda x: self._on_search_ore())
        ore.add_widget(b3)
        root.add_widget(ore)
        b4 = Button(text="区域方块构成", size_hint_y=None, height=28)
        b4.bind(on_press=lambda x: self._on_composition())
        root.add_widget(b4)
        self.status = Label(text="就绪：输入种子并生成地图", size_hint_y=None, height=24)
        root.add_widget(self.status)

        self.add_widget(root)
        self._rebuild_struct_combo()
        self._rebuild_ore_combo()

    # ---- 工具 ----
    def _set_status(self, s):
        self.status.text = s

    def _random_seed(self):
        self.seed_in.text = str(__import__("random").randint(-(2 ** 63), 2 ** 63 - 1))

    def _on_ver_change(self, sp, val):
        self._rebuild_ore_combo()

    def _on_dim_change(self, sp, val):
        self.dim = DIM_MAP[val]
        self._rebuild_struct_combo()
        self._rebuild_ore_combo()

    def _rebuild_struct_combo(self):
        dim = DIM_MAP[self.dim_spin.text]
        self.struct_items = [s for s in SEED_STRUCT_DEFS if s["dim"] == dim_map_inv(dim) and s["locatable"]]
        self.struct_spin.values = [s["cn"] for s in self.struct_items]
        if self.struct_spin.values:
            self.struct_spin.text = self.struct_spin.values[0]

    def _rebuild_ore_combo(self):
        vint = engine.version_label_to_int(self.ver_spin.text)
        dim = DIM_MAP[self.dim_spin.text]
        keys = ores.get_ore_keys(vint, "nether" if dim == -1 else "overworld")
        self.ore_items = [(k, ores.get_ore_config(vint, k)) for k in keys]
        self.ore_spin.values = [c["name"] for _, c in self.ore_items]
        if self.ore_spin.values:
            self.ore_spin.text = self.ore_spin.values[0]

    def _get_seed(self):
        s = self.seed_in.text.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            self._popup("种子必须是整数（可正可负）。")
            return None

    def _area(self):
        if self.map.selection:
            return self.map.selection
        return self.map.view_bounds()

    def _render_cb(self, cx, cz, rw, rh, bpp):
        if self.gen is None:
            return None
        return engine.generate_biome_map(self.gen, cx, cz, rw, rh, bpp,
                                         surface_y=64)["image"]

    def _on_generate(self):
        seed = self._get_seed()
        if seed is None:
            return
        self.version_int = engine.version_label_to_int(self.ver_spin.text)
        self.dim = DIM_MAP[self.dim_spin.text]
        self.gen = engine.make_generator(self.version_int, seed, self.dim)
        self._set_status("正在生成地图…")
        self.pb.value = 0

        def work():
            sx, sz = engine.get_spawn(self.gen)
            self.map.center_x, self.map.center_z = sx, sz
            Clock.schedule_once(lambda dt: self.map.render(), 0)
            return sx, sz
        def done(res):
            if res[0] == "error":
                self._popup("生成失败：" + res[1]); return
            sx, sz = res[1]
            self.map.set_structures([(sx, sz, (1, 0.84, 0, 1), "出生点")])
            self._set_status(f"已生成 {self.ver_spin.text} 种子 {seed}（{self.dim_spin.text}）")
        run_bg(work, done)

    def _reset_view(self):
        if self.gen is None:
            return
        sx, sz = engine.get_spawn(self.gen)
        self.map.reset_view(sx, sz)

    def _toggle_select(self):
        self.map.mode = "select" if self.map.mode == "pan" else "pan"
        self._set_status("框选模式：" + ("开" if self.map.mode == "select" else "关（拖拽=平移）"))

    def _on_search_struct(self, mode):
        if self.gen is None:
            self._popup("请先生成地图。"); return
        item = next((s for s in self.struct_items if s["cn"] == self.struct_spin.text), None)
        if not item:
            return
        if mode == "radius":
            try:
                R = int(self.dist.text)
            except ValueError:
                R = 30000
            sx, sz = engine.get_spawn(self.gen)
            area = (sx - R, sz - R, sx + R, sz + R)
        else:
            area = self._area()
        ymin, ymax = self._parse_y()
        try:
            maxd = float(self.dist.text) if self.dist.text else 1e9
        except ValueError:
            maxd = 1e9
        sid = item["sid"]; g = self.gen; sx, sz = engine.get_spawn(g)
        self._set_status(f"正在搜索 {item['name']} …")
        self.pb.value = 0

        def work():
            return engine.find_structures_in_area(g, sid, *area)
        def done(res):
            if res[0] == "error":
                self._popup("搜索失败：" + res[1]); return
            found = res[1]
            self.result_box.clear()
            pts = []
            shown = 0
            for (x, z) in found:
                d = math.dist((x, z), (sx, sz))
                if d > maxd:
                    continue
                y_est = engine.estimate_height(g, x, z)
                if ymin is not None and y_est < ymin:
                    continue
                if ymax is not None and y_est > ymax:
                    continue
                self.result_box.add(item["cn"], x, y_est, z, d, item["y_note"])
                pts.append((x, z, y_est))
                shown += 1
            self.struct_points = pts
            self.map.set_structures([(sx, sz, (1, 0.84, 0, 1), "出生点")] +
                                   [(x, z, STRUCT_COLOR, item["name"]) for x, z, _ in pts])
            self._set_status(f"找到 {item['name']} {shown} 个（已按 Y/距离筛选）"
                             + (f"；扫描到 {len(found)} 个" if shown != len(found) else ""))
        run_bg(work, done)

    def _parse_y(self):
        ymin = ymax = None
        try:
            if self.y_min.text.strip():
                ymin = int(self.y_min.text)
        except ValueError:
            ymin = None
        try:
            if self.y_max.text.strip():
                ymax = int(self.y_max.text)
        except ValueError:
            ymax = None
        return ymin, ymax

    def _on_search_ore(self):
        if self.gen is None:
            self._popup("请先生成地图。"); return
        item = next((c for k, c in self.ore_items if c["name"] == self.ore_spin.text), None)
        if not item:
            return
        area = self._area()
        key = next(k for k, c in self.ore_items if c is item)
        biome_fn = (lambda x, z: engine.get_biome_id(self.gen, x, 64, z)
                    if item.get("biomes") == "mountain" else None)
        self._set_status(f"正在搜索 {item['name']} …")
        om = ores.OreModel(self.version_int, int(self.seed_in.text))

        def work():
            return om.find_ore(key, area[0], area[1], area[2], area[3],
                              max_results=400, biome_fn=biome_fn)
        def done(res):
            if res[0] == "error":
                self._popup("搜索失败：" + res[1]); return
            results = res[1]
            self.result_box.clear()
            for (x, y, z) in results:
                self.result_box.add(item["name"], x, y, z, "", f"Y={y}")
            self._set_status(f"{item['name']}：搜索到 {len(results)} 处（坐标近似，Y 精确）")
        run_bg(work, done)

    def _on_composition(self):
        if self.gen is None:
            self._popup("请先生成地图。"); return
        area = self._area()
        om = ores.OreModel(self.version_int, int(self.seed_in.text))
        self._set_status("正在统计区域方块构成 …")
        self.pb.value = 0

        def work():
            return om.composition(area[0], area[1], area[2], area[3],
                                 biome_fn=lambda x, z: engine.get_biome_id(self.gen, x, 64, z))
        def done(res):
            if res[0] == "error":
                self._popup("统计失败：" + res[1]); return
            comp = res[1]
            self.result_box.clear()
            for k, v in comp.items():
                c = v["cfg"]
                self.result_box.add(c["name"], "-", "-", "-", "-",
                                    f"约 {v['count']} 个矿脉 ({c['note']})")
            self._set_status("区域矿石构成已列出（基于生成参数估计）")
        run_bg(work, done)

    def _on_view_struct_3d(self):
        if self.gen is None:
            self._popup("请先生成地图。"); return
        item = next((s for s in self.struct_items if s["cn"] == self.struct_spin.text), None)
        if not item:
            return
        x = z = y = None
        sel = self.result_box.selected()
        if sel:
            try:
                x = int(sel[1]); z = int(sel[3])
                y = None if sel[2] in ("", "-") else int(sel[2])
            except Exception:
                x = z = y = None
        if x is None and self.struct_points:
            px, pz, py = self.struct_points[0]
            x, z, y = px, pz, py
        if x is None:
            sx, sz = engine.get_spawn(self.gen)
            x, z = sx, sz
        if y is None:
            y = engine.estimate_height(self.gen, x, z)
        App.get_running_app().show_struct_3d(item["key"], x, z, y)

    def _on_3d(self):
        if self.gen is None:
            self._popup("请先生成地图。"); return
        b = self.map.view_bounds()
        n = 40
        xs = [b[0] + (b[2] - b[0]) * i / (n - 1) for i in range(n)]
        zs = [b[1] + (b[3] - b[1]) * i / (n - 1) for i in range(n)]
        pts = [(p[0], p[2], p[1]) for p in self.struct_points]
        App.get_running_app().show_terrain_3d(self.gen, xs, zs, pts, self.ver_spin.text)

    def _popup(self, msg):
        self._pp = Popup(title="提示", content=Label(text=msg), size_hint=(0.8, 0.4))
        self._pp.open()


# ---------------------------------------------------------------------------
# 存档查询界面
# ---------------------------------------------------------------------------
class SaveScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "save"
        self.save_obj = None
        self.dim = "主世界"
        self.block_points = []
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=6, spacing=4)
        top = GridLayout(cols=2, size_hint_y=None, height=30, spacing=4)
        b = Button(text="打开存档文件夹…")
        b.bind(on_press=lambda x: self._open())
        top.add_widget(b)
        self.dim_spin = Spinner(text="主世界", values=["主世界"])
        top.add_widget(self.dim_spin)
        root.add_widget(top)
        self.info = Label(text="尚未打开存档", size_hint_y=None, height=40)
        root.add_widget(self.info)

        nav = GridLayout(cols=4, size_hint_y=None, height=30, spacing=4)
        for t, f in [("放大", lambda: self.map.zoom(0.7)),
                     ("缩小", lambda: self.map.zoom(1.4)),
                     ("清除选择", lambda: self.map.clear_structures()),
                     ("框选模式", self._toggle_select)]:
            b = Button(text=t)
            b.bind(on_press=lambda x, ff=f: ff())
            nav.add_widget(b)
        root.add_widget(nav)

        b = Button(text="加载地图（仅已加载区块）", size_hint_y=None, height=30)
        b.bind(on_press=lambda x: self._on_load())
        root.add_widget(b)

        body = BoxLayout(orientation="horizontal", spacing=4)
        self.map = MapWidget(size_hint=(0.62, 1))
        self.map.render_cb = self._render_cb
        body.add_widget(self.map)
        right = BoxLayout(orientation="vertical", spacing=4)
        self.result_box = _ResultList()
        right.add_widget(self.result_box)
        b3 = Button(text="一键 3D 预览", size_hint_y=None, height=34)
        b3.bind(on_press=lambda x: self._on_3d())
        right.add_widget(b3)
        body.add_widget(right)
        root.add_widget(body)

        kw = GridLayout(cols=3, size_hint_y=None, height=30, spacing=4)
        self.block_in = TextInput(text="diamond_ore", hint_text="方块名(含)", multiline=False)
        kw.add_widget(Label(text="方块"))
        kw.add_widget(self.block_in)
        b4 = Button(text="搜索该方块")
        b4.bind(on_press=lambda x: self._on_search_block())
        kw.add_widget(b4)
        root.add_widget(kw)
        b5 = Button(text="选区方块构成", size_hint_y=None, height=28)
        b5.bind(on_press=lambda x: self._on_composition())
        root.add_widget(b5)
        self.status = Label(text="打开含 level.dat 的存档", size_hint_y=None, height=24)
        root.add_widget(self.status)
        self.add_widget(root)

    def _set_status(self, s):
        self.status.text = s

    def _toggle_select(self):
        self.map.mode = "select" if self.map.mode == "pan" else "pan"
        self._set_status("框选模式：" + ("开" if self.map.mode == "select" else "关"))

    def _open(self):
        fc = FileChooserListView(dirselect=True)
        box = BoxLayout(orientation="vertical")
        box.add_widget(fc)
        bb = BoxLayout(size_hint_y=None, height=36)
        ok = Button(text="选择此文件夹")
        cancel = Button(text="取消")
        bb.add_widget(ok); bb.add_widget(cancel)
        box.add_widget(bb)
        p = Popup(title="选择存档文件夹", content=box, size_hint=(0.95, 0.9))

        def choose(x):
            path = fc.selection[0] if fc.selection else None
            if not path:
                return
            if not os.path.isfile(os.path.join(path, "level.dat")):
                self._popup("该文件夹不是有效存档（未找到 level.dat）。"); return
            self.save_obj = saves.Save(path)
            dims = self.save_obj.dimensions()
            self.dim_spin.values = dims
            self.dim = dims[0]
            self.dim_spin.text = self.dim
            self.info.text = (f"名称: {self.save_obj.name}\n种子: {self.save_obj.info.get('seed','未知')}\n"
                              f"版本: {self.save_obj.info.get('version_name','未知')}\n可用维度: {', '.join(dims)}")
            p.dismiss()
            self._set_status("已打开存档，请选择维度后加载地图")
        ok.bind(on_press=choose)
        cancel.bind(on_press=lambda x: p.dismiss())
        p.open()

    def _on_load(self):
        if self.save_obj is None:
            self._popup("请先打开存档。"); return
        self.dim = self.dim_spin.text
        self._set_status(f"正在加载 {self.dim} 已加载区块地图…")

        def work():
            return self.save_obj.render_top_map(self.dim, self.map.center_x, self.map.center_z,
                                              self.map.render_w, self.map.render_h,
                                              blocks_per_px=self.map.bpp)
        def done(res):
            if res[0] == "error":
                self._popup("加载失败：" + res[1]); return
            data = res[1]
            cx = data["min_x"] + (self.map.render_w * self.map.bpp) / 2
            cz = data["min_z"] + (self.map.render_h * self.map.bpp) / 2
            self.map.set_image(data["image"])
            self.map.center_x, self.map.center_z = cx, cz
            nch = len(self.save_obj.loaded_chunks(self.dim))
            self._set_status(f"{self.dim} 已加载区块数: {nch}（灰色=未加载）")
        run_bg(work, done)

    def _render_cb(self, cx, cz, rw, rh, bpp):
        if self.save_obj is None:
            return None
        return self.save_obj.render_top_map(self.dim, cx, cz, rw, rh, blocks_per_px=bpp)["image"]

    def _area(self):
        if self.map.selection:
            return self.map.selection
        return self.map.view_bounds()

    def _on_search_block(self):
        if self.save_obj is None:
            self._popup("请先打开存档并加载地图。"); return
        kw = self.block_in.text.strip()
        if not kw:
            self._popup("请输入方块名，如 diamond_ore / chest / spawner"); return
        area = self._area()
        dim = self.dim
        self._set_status(f"在已加载区块中搜索 {kw} …")

        def work():
            return self.save_obj.find_blocks(dim, kw, max_results=3000,
                                            x0=area[0], z0=area[1], x1=area[2], z1=area[3])
        def done(res):
            if res[0] == "error":
                self._popup("搜索失败：" + res[1]); return
            results = res[1]
            self.result_box.clear()
            pts = []
            for (x, y, z, nm) in results:
                d = math.dist((x, z), (0, 0))
                self.result_box.add(nm.split(":")[-1], x, y, z, d, "")
                pts.append((x, y, z))
            self.block_points = pts
            self._set_status(f"在已加载区块中找到 {len(results)} 个匹配 {kw} 的方块")
        run_bg(work, done)

    def _on_composition(self):
        if self.save_obj is None:
            self._popup("请先打开存档并加载地图。"); return
        area = self._area()
        dim = self.dim
        self._set_status("正在统计选区方块构成（已加载区块）…")

        def work():
            return self.save_obj.count_blocks(dim, area[0], area[1], area[2], area[3], chunk_limit=1200)
        def done(res):
            if res[0] == "error":
                self._popup("统计失败：" + res[1]); return
            cnt = res[1]
            self.result_box.clear()
            for nm, c in cnt.most_common(200):
                self.result_box.add(nm.split(":")[-1], "-", "-", "-", c, "")
            self._set_status(f"选区共统计到 {len(cnt)} 种方块，已按数量排序")
        run_bg(work, done)

    def _on_3d(self):
        if self.save_obj is None:
            self._popup("请先打开存档并加载地图。"); return
        dim = self.dim
        b = self.map.view_bounds()
        cx0, cx1 = b[0] // 16, b[2] // 16
        cz0, cz1 = b[1] // 16, b[3] // 16
        chunks = [(c[0], c[1]) for c in self.save_obj.loaded_chunks(dim)
                  if cx0 <= c[0] <= cx1 and cz0 <= c[1] <= cz1][:2000]
        X, Y, Z, P = [], [], [], []
        for (cx, cz) in chunks:
            rx, rz = cx // 32, cz // 32
            reg = self.save_obj.get_region(dim, rx, rz)
            if reg is None:
                continue
            lx, lz = cx - rx * 32, cz - rz * 32
            if reg.chunk_location(lx, lz) == (0, 0):
                continue
            top = None
            for y in range(319, -64, -2):
                nm = self.save_obj.get_block(dim, cx * 16 + 8, y, cz * 16 + 8)
                if nm and "air" not in nm:
                    top = y; break
            if top is None:
                top = -64
            X.append(cx * 16 + 8); Y.append(cz * 16 + 8); Z.append(top)
        for p in self.block_points:
            P.append((p[0], p[2], p[1]))
        App.get_running_app().show_save_3d(X, Y, Z, P, dim)

    def _popup(self, msg):
        self._pp = Popup(title="提示", content=Label(text=msg), size_hint=(0.8, 0.4))
        self._pp.open()


# ---------------------------------------------------------------------------
# 结果列表（ScrollView + GridLayout）
# ---------------------------------------------------------------------------
class _ResultList(ScrollView):
    COLS = ["类型", "X", "Y", "Z", "距离", "备注"]

    def __init__(self, **kw):
        super().__init__(**kw)
        self.layout = GridLayout(cols=len(self.COLS), size_hint_y=None, spacing=1)
        self.layout.bind(minimum_height=self.layout.setter("height"))
        # 表头
        for c in self.COLS:
            self.layout.add_widget(Label(text=c, bold=True, size_hint_y=None, height=22))
        self.add_widget(self.layout)
        self._rows = []

    def clear(self):
        self.layout.clear_widgets()
        for c in self.COLS:
            self.layout.add_widget(Label(text=c, bold=True, size_hint_y=None, height=22))
        self._rows = []

    def add(self, kind, x, y, z, dist, note):
        vals = [str(kind), str(x), str(y), str(z),
                (f"{dist:.0f}" if isinstance(dist, (int, float)) and dist != "" else str(dist)),
                str(note)]
        for v in vals:
            self.layout.add_widget(Label(text=v, size_hint_y=None, height=20))
        self._rows.append(vals)

    def selected(self):
        return None  # 安卓版简化：默认用第一个找到的点


# ---------------------------------------------------------------------------
# 3D 屏幕（matplotlib + KivyAgg）
# ---------------------------------------------------------------------------
class ThreeDScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "threed"
        self.box = BoxLayout(orientation="vertical")
        self.add_widget(self.box)

    def show(self, build_fn, title):
        self.box.clear_widgets()
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_kivyagg import FigureCanvasKivyAgg
        fig = plt.figure(figsize=(6, 5))
        ax = fig.add_subplot(111, projection="3d")
        build_fn(ax)
        canvas = FigureCanvasKivyAgg(fig)
        self.box.add_widget(canvas)
        back = Button(text="返回", size_hint_y=None, height=36)
        back.bind(on_press=lambda x: App.get_running_app().back_to(self._return))
        self.box.add_widget(back)
        self._title = title
        App.get_running_app().sm.current = "threed"

    def _return(self):
        App.get_running_app().sm.current = self._prev


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def dim_map_inv(dim):
    for k, v in DIM_MAP.items():
        if v == dim:
            return k
    return "主世界"


def matplotlib_progress():
    try:
        from kivy.uix.progressbar import ProgressBar
        return ProgressBar(max=100, value=0)
    except Exception:
        from kivy.uix.slider import Slider
        return Slider(min=0, max=100, value=0)


# ---------------------------------------------------------------------------
# 主应用
# ---------------------------------------------------------------------------
class SeedQueryApp(App):
    def build(self):
        self.sm = ScreenManager()
        self.seed_screen = SeedScreen()
        self.save_screen = SaveScreen()
        self.threed = ThreeDScreen()
        self.sm.add_widget(self.seed_screen)
        self.sm.add_widget(self.save_screen)
        self.sm.add_widget(self.threed)

        root = BoxLayout(orientation="vertical")
        tabs = BoxLayout(size_hint_y=None, height=40)
        b1 = Button(text="种子查询")
        b1.bind(on_press=lambda x: setattr(self.sm, "current", "seed"))
        b2 = Button(text="存档查询")
        b2.bind(on_press=lambda x: setattr(self.sm, "current", "save"))
        tabs.add_widget(b1); tabs.add_widget(b2)
        root.add_widget(tabs)
        root.add_widget(self.sm)
        return root

    def back_to(self, fn):
        fn()

    # ---- 3D 展示 ----
    def show_struct_3d(self, key, x, z, y):
        def build(ax):
            structures_3d.draw_model_3d(ax, key, x, z, y,
                                       title=f"{structures_3d.get_model(key)['cn']} @ X{x} Z{z}（近似示意）")
        self.threed._prev = self.sm.current
        self.threed.show(build, "结构 3D 形状")

    def show_terrain_3d(self, g, xs, zs, pts, ver):
        import numpy as np
        def build(ax):
            X, Y, Z = [], [], []
            for z in zs:
                for x in xs:
                    X.append(x); Y.append(z)
                    Z.append(engine.estimate_height(g, int(x), int(z)))
            X = np.array(X); Y = np.array(Y); Z = np.array(Z)
            if len(X) >= 3:
                ax.plot_trisurf(X, Y, Z, cmap="terrain", alpha=0.85, linewidth=0, antialiased=True)
            elif len(X) > 0:
                ax.scatter(X, Y, Z, c="orange", s=40)
            if pts:
                pa = np.array(pts)
                ax.scatter(pa[:, 0], pa[:, 1], pa[:, 2], c="red", s=28, depthshade=False)
            ax.set_xlabel("X"); ax.set_ylabel("Z"); ax.set_zlabel("Y (高度)")
            ax.set_title(f"3D 地形预览（{ver}）")
        self.threed._prev = self.sm.current
        self.threed.show(build, "3D 地形预览")

    def show_save_3d(self, X, Y, Z, P, dim):
        import numpy as np
        def build(ax):
            X = np.array(X); Y = np.array(Y); Z = np.array(Z)
            if len(X) >= 3:
                ax.scatter(X, Y, Z, c="seagreen", s=20, alpha=0.7)
            if P:
                pa = np.array(P)
                ax.scatter(pa[:, 0], pa[:, 1], pa[:, 2], c="red", s=28, depthshade=False)
            ax.set_xlabel("X"); ax.set_ylabel("Z"); ax.set_zlabel("Y (高度)")
            ax.set_title(f"3D 真实地形（{dim}，已加载区块）")
        self.threed._prev = self.sm.current
        self.threed.show(build, "3D 真实地形")


if __name__ == "__main__":
    SeedQueryApp().run()

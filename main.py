# -*- coding: utf-8 -*-
"""
Minecraft 种子查询器 —— 主程序（tkinter GUI）
功能：
  [种子查询] 支持 MC 1.0~1.21（下拉最新显示为 26.3）全部 Java 版本，查询生物群系地图、
             结构坐标、结构 3D 形状、框选区域、方块/矿石搜索（基于官方生成参数）、3D 预览。
  [存档查询] 读取本地存档 .mca，仅显示已加载区块的真实方块与顶部地图。
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import random
import os
import math
import sys
import time
import traceback
import numpy as np

import engine
import ores
import saves
import structures_3d
from mapview import MapView


# ------------------------------------------------------------------
# 全局异常捕获：即使 -w 无控制台模式也能弹窗并显示错误，避免“神秘闪退”
# ------------------------------------------------------------------
def _write_error_log(tb_text):
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "error.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "  程序异常\n")
            f.write(tb_text + "\n")
    except Exception:
        pass


def _global_except(exc_type, exc_value, exc_tb):
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _write_error_log(tb_text)
    try:
        messagebox.showerror(
            "程序出错",
            "发生未捕获异常，详情已写入 error.log：\n\n" + tb_text[-2000:])
    except Exception:
        pass


sys.excepthook = _global_except


# tkinter 回调线程中的异常不会走 sys.excepthook，单独接管
def _tk_report_callback(*args):
    _global_except(*args)


tk.Tk.report_callback_exception = staticmethod(_tk_report_callback)

DIM_MAP = {"主世界": 0, "下界": -1, "末地": 1}
STRUCT_COLOR = "#ff4444"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Minecraft 种子查询器 (Java 版)")
        self.geometry("1180x740")
        try:
            self.iconbitmap()
        except Exception:
            pass

        # 状态
        self.seed_gen = None
        self.seed_version_int = None
        self.seed_dim = 0
        self.seed_struct_defs = engine.get_structures()
        self.seed_struct_points = []
        self._map_progress = None

        self.save_obj = None
        self.save_dim = "主世界"
        self.save_block_points = []

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        self._build_seed_tab()
        self._build_save_tab()

        self.status = ttk.Label(self, text="就绪：请先在“种子查询”输入种子并生成地图",
                               anchor="w", relief="sunken")
        self.status.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # 通用工具
    # ------------------------------------------------------------------
    def _set_status(self, msg):
        self.status.config(text=msg)

    def _err(self, msg):
        messagebox.showerror("提示", msg)

    def _run_bg(self, work, prog, done):
        """在后台线程执行 work(prog)；返回 ("ok", 值) 或 ("error", 信息)。"""
        def _p(f):
            if prog:
                self.after(0, lambda: prog(f))

        def _run():
            try:
                val = work(_p)
                res = ("ok", val)
            except Exception as ex:
                res = ("error", str(ex))
            if done:
                self.after(0, lambda: done(res))
        threading.Thread(target=_run, daemon=True).start()

    def _clear_results(self, tree):
        for row in tree.get_children():
            tree.delete(row)

    def _add_result(self, tree, kind, x, y, z, dist, note):
        tree.insert("", "end", values=(kind, x, y if y != "" else "-",
                                       z, (f"{dist:.0f}" if dist != "" else "-"), note))

    def _copy_selected(self, tree):
        sel = tree.selection()
        if not sel:
            return
        lines = []
        for s in sel:
            v = tree.item(s, "values")
            lines.append(f"{v[1]} {v[2]} {v[3]}")
        txt = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(txt)
        self._set_status(f"已复制 {len(lines)} 条坐标到剪贴板")

    # ------------------------------------------------------------------
    # 种子查询选项卡
    # ------------------------------------------------------------------
    def _build_seed_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="种子查询")

        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=4, pady=4)
        right = ttk.Frame(tab)
        right.pack(side="right", fill="both", expand=True, padx=4, pady=4)

        pw = ttk.PanedWindow(left, orient="vertical")
        pw.pack(fill="both", expand=True)
        ctrls = ttk.Frame(pw, width=380)
        resf = ttk.Frame(pw)
        pw.add(ctrls, weight=2)
        pw.add(resf, weight=3)

        # ---- 控制区 ----
        row = 0

        ttk.Label(ctrls, text="种子 (Seed):").grid(row=row, column=0, sticky="w", pady=2)
        self.seed_entry = ttk.Entry(ctrls, width=26)
        self.seed_entry.insert(0, "123456789")
        self.seed_entry.grid(row=row, column=1, sticky="we")
        self.btn_rand = ttk.Button(ctrls, text="随机", width=6,
                                   command=self._random_seed)
        self.btn_rand.grid(row=row, column=2, padx=2)
        row += 1

        ttk.Label(ctrls, text="版本:").grid(row=row, column=0, sticky="w")
        self.ver_combo = ttk.Combobox(ctrls, width=24, state="readonly")
        vers = [v[0] for v in engine.get_versions()]
        self.ver_combo["values"] = vers
        self.ver_combo.set("1.20")
        self.ver_combo.grid(row=row, column=1, columnspan=2, sticky="we")
        self.ver_combo.bind("<<ComboboxSelected>>", lambda e: self._rebuild_seed_ore_combo())
        row += 1

        ttk.Label(ctrls, text="维度:").grid(row=row, column=0, sticky="w")
        self.seed_dim_combo = ttk.Combobox(ctrls, width=24, state="readonly",
                                           values=list(DIM_MAP.keys()))
        self.seed_dim_combo.set("主世界")
        self.seed_dim_combo.grid(row=row, column=1, columnspan=2, sticky="we")
        self.seed_dim_combo.bind("<<ComboboxSelected>>",
                                 lambda e: (self._rebuild_seed_struct_combo(),
                                            self._rebuild_seed_ore_combo()))
        row += 1

        self.btn_gen = ttk.Button(ctrls, text="生成 / 刷新地图",
                                  command=self._on_generate)
        self.btn_gen.grid(row=row, column=0, columnspan=3, sticky="we", pady=3)
        row += 1

        self.seed_pb = ttk.Progressbar(ctrls, mode="determinate")
        self.seed_pb.grid(row=row, column=0, columnspan=3, sticky="we")
        row += 1

        # 地图导航
        nav = ttk.Frame(ctrls)
        nav.grid(row=row, column=0, columnspan=3, sticky="we", pady=2)
        ttk.Button(nav, text="放大", width=7, command=lambda: self._zoom_seed(0.7)).pack(side="left")
        ttk.Button(nav, text="缩小", width=7, command=lambda: self._zoom_seed(1.4)).pack(side="left")
        ttk.Button(nav, text="回出生点", width=9, command=self._reset_seed_view).pack(side="left")
        ttk.Button(nav, text="清除选择", width=9, command=lambda: self.seed_map.clear_structures()).pack(side="left")
        row += 1

        self.seed_sel_label = ttk.Label(ctrls, text="选区：未选择（将使用整张地图范围）",
                                        foreground="#aaaaaa")
        self.seed_sel_label.grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        # 3D 切换
        self.btn_3d_seed = ttk.Button(ctrls, text="一键 3D 预览",
                                      command=lambda: self._on_3d_toggle("seed"))
        self.btn_3d_seed.grid(row=row, column=0, columnspan=3, sticky="we", pady=2)
        row += 1

        # 结构查询
        ttk.Separator(ctrls, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="we", pady=4)
        row += 1
        ttk.Label(ctrls, text="— 结构查询 —").grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        ttk.Label(ctrls, text="结构:").grid(row=row, column=0, sticky="w")
        self.seed_struct_combo = ttk.Combobox(ctrls, width=24, state="readonly")
        self.seed_struct_combo.grid(row=row, column=1, columnspan=2, sticky="we")
        self._rebuild_seed_struct_combo()
        row += 1

        ttk.Label(ctrls, text="Y 范围(过滤):").grid(row=row, column=0, sticky="w")
        self.seed_y_min = ttk.Entry(ctrls, width=8)
        self.seed_y_min.grid(row=row, column=1, sticky="w")
        self.seed_y_max = ttk.Entry(ctrls, width=8)
        self.seed_y_max.grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(ctrls, text="距出生点上限:").grid(row=row, column=0, sticky="w")
        self.seed_dist = ttk.Entry(ctrls, width=12)
        self.seed_dist.insert(0, "30000")
        self.seed_dist.grid(row=row, column=1, columnspan=2, sticky="w")
        row += 1

        ttk.Button(ctrls, text="搜索选区内结构", command=lambda: self._on_search_struct("area")).grid(
            row=row, column=0, columnspan=1, sticky="we")
        ttk.Button(ctrls, text="按半径搜附近", command=lambda: self._on_search_struct("radius")).grid(
            row=row, column=1, columnspan=2, sticky="we")
        row += 1

        ttk.Button(ctrls, text="查看结构 3D 形状", command=self._on_view_struct_3d).grid(
            row=row, column=0, columnspan=3, sticky="we", pady=2)
        row += 1

        # 方块/矿石查询
        ttk.Separator(ctrls, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="we", pady=4)
        row += 1
        ttk.Label(ctrls, text="— 方块 / 矿石查询 —").grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        ttk.Label(ctrls, text="方块:").grid(row=row, column=0, sticky="w")
        self.seed_ore_combo = ttk.Combobox(ctrls, width=24, state="readonly")
        self.seed_ore_combo.grid(row=row, column=1, columnspan=2, sticky="we")
        self._rebuild_seed_ore_combo()
        row += 1

        ttk.Button(ctrls, text="搜索该方块坐标", command=self._on_search_ore).grid(
            row=row, column=0, columnspan=2, sticky="we")
        ttk.Button(ctrls, text="区域方块构成", command=self._on_seed_composition).grid(
            row=row, column=2, sticky="we")
        row += 1

        ttk.Label(ctrls, text="注：种子模式的矿石为基于官方生成参数的概率分布（Y 区间精确，坐标近似）。",
                  foreground="#888888", wraplength=360).grid(row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1

        # ---- 结果区 ----
        cols = ("类型", "X", "Y", "Z", "距离", "备注")
        self.seed_tree = ttk.Treeview(resf, columns=cols, show="headings", height=18)
        for c in cols:
            self.seed_tree.heading(c, text=c)
        self.seed_tree.column("类型", width=90)
        self.seed_tree.column("X", width=70)
        self.seed_tree.column("Y", width=60)
        self.seed_tree.column("Z", width=70)
        self.seed_tree.column("距离", width=60)
        self.seed_tree.column("备注", width=150)
        sb = ttk.Scrollbar(resf, orient="vertical", command=self.seed_tree.yview)
        self.seed_tree.configure(yscrollcommand=sb.set)
        self.seed_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        ttk.Button(resf, text="复制选中坐标", command=lambda: self._copy_selected(self.seed_tree)).pack(side="bottom", fill="x")

        # ---- 地图 ----
        self.seed_map = MapView(right)
        self.seed_map.container.pack(fill="both", expand=True)
        self.seed_map.render_callback = self._seed_render_callback
        self.seed_map.get_3d_data = self._seed_3d
        # 选择变化时更新标签
        self._seed_sel_poll()

    def _seed_sel_poll(self):
        sel = self.seed_map.selection
        if sel:
            self.seed_sel_label.config(
                text=f"选区 X[{sel[0]},{sel[2]}] Z[{sel[1]},{sel[3]}]")
        else:
            self.seed_sel_label.config(text="选区：未选择（将使用整张地图范围）")
        self.after(250, self._seed_sel_poll)

    def _rebuild_seed_struct_combo(self):
        dim = self.seed_dim_combo.get()
        items = [s for s in self.seed_struct_defs if s["dim"] == dim and s["locatable"]]
        self._seed_struct_items = items
        labels = [f"{s['cn']}" for s in items]
        self.seed_struct_combo["values"] = labels
        if labels:
            self.seed_struct_combo.set(labels[0])

    def _rebuild_seed_ore_combo(self):
        ver = self.ver_combo.get()
        vint = engine.version_label_to_int(ver)
        dim = DIM_MAP[self.seed_dim_combo.get()]
        keys = ores.get_ore_keys(vint, "nether" if dim == -1 else "overworld")
        self._seed_ore_items = [(k, ores.get_ore_config(vint, k)) for k in keys]
        labels = [c["name"] for _, c in self._seed_ore_items]
        self.seed_ore_combo["values"] = labels
        if labels:
            self.seed_ore_combo.set(labels[0])

    def _random_seed(self):
        self.seed_entry.delete(0, tk.END)
        self.seed_entry.insert(0, str(random.randint(-(2**63), 2**63 - 1)))

    def _get_seed(self):
        s = self.seed_entry.get().strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            self._err("种子必须是整型数字（可正可负）。")
            return None

    def _zoom_seed(self, factor):
        self.seed_map.bpp = max(1, min(64, int(round(self.seed_map.bpp * factor))))
        self.seed_map.bpp_eff = self.seed_map.bpp / self.seed_map.disp_scale
        self.seed_map.render()

    def _reset_seed_view(self):
        if self.seed_gen is None:
            return
        sx, sz = engine.get_spawn(self.seed_gen)
        self.seed_map.center_x = sx
        self.seed_map.center_z = sz
        self.seed_map.render()

    def _on_generate(self):
        seed = self._get_seed()
        if seed is None:
            return
        ver = self.ver_combo.get()
        self.seed_version_int = engine.version_label_to_int(ver)
        self.seed_dim = DIM_MAP[self.seed_dim_combo.get()]
        self.seed_gen = engine.make_generator(self.seed_version_int, seed, self.seed_dim)

        def work(p):
            self._map_progress = p
            # 居中到出生点
            sx, sz = engine.get_spawn(self.seed_gen)
            self.seed_map.center_x = sx
            self.seed_map.center_z = sz
            self.after(0, self.seed_map.render)
            return True

        def done(res):
            self._map_progress = None
            self.seed_pb["value"] = 100
            if res[0] == "error":
                self._err("生成失败：" + res[1])
                return
            # 标记出生点
            sx, sz = engine.get_spawn(self.seed_gen)
            self.seed_map.set_structures([(sx, sz, "#ffd700", "出生点")])
            self._set_status(f"已生成 {ver} 种子 {seed} 的地图（{self.seed_dim_combo.get()}）")
        self._run_bg(work, lambda f: self.seed_pb.config(value=f * 100), done)

    def _seed_render_callback(self, cx, cz, rw, rh, bpp):
        if self.seed_gen is None:
            return None
        cb = self._map_progress
        return engine.generate_biome_map(self.seed_gen, cx, cz, rw, rh, bpp,
                                         surface_y=64, callback=cb)["image"]

    def _area_from_map(self, mv):
        if mv.selection:
            return mv.selection
        return mv.view_bounds()

    # ---- 结构搜索 ----
    def _on_search_struct(self, mode):
        if self.seed_gen is None:
            self._err("请先生成地图。")
            return
        sel = self.seed_struct_combo.get()
        item = next((s for s in self._seed_struct_items if s["cn"] == sel), None)
        if not item:
            return
        if mode == "radius":
            try:
                R = int(self.seed_dist.get())
            except ValueError:
                R = 30000
            sx, sz = engine.get_spawn(self.seed_gen)
            area = (sx - R, sz - R, sx + R, sz + R)
        else:
            area = self._area_from_map(self.seed_map)

        ymin, ymax = self._parse_y_range()
        try:
            maxd = float(self.seed_dist.get()) if self.seed_dist.get() else 1e9
        except ValueError:
            maxd = 1e9

        struct_sid = item["sid"]
        g = self.seed_gen
        sx, sz = engine.get_spawn(g)

        self._set_status(f"正在搜索 {item['name']} …")
        self.seed_pb["value"] = 0

        def work(p):
            found = engine.find_structures_in_area(g, struct_sid, *area)
            return found

        def done(res):
            if res[0] == "error":
                self._err("搜索失败：" + res[1])
                return
            found = res[1]
            self._clear_results(self.seed_tree)
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
                self._add_result(self.seed_tree, item["cn"], x, y_est, z, d,
                                item["y_note"])
                pts.append((x, z, y_est))
                shown += 1
            self.seed_struct_points = pts
            self.seed_map.set_structures(
                [(sx, sz, "#ffd700", "出生点")] +
                [(x, z, STRUCT_COLOR, item["name"]) for x, z, _ in pts])
            self.seed_pb["value"] = 100
            self._set_status(f"找到 {item['name']} {shown} 个（已按 Y/距离筛选）"
                             + (f"；共扫描到 {len(found)} 个" if shown != len(found) else ""))
        self._run_bg(work, None, done)

    def _parse_y_range(self):
        ymin = ymax = None
        try:
            if self.seed_y_min.get().strip():
                ymin = int(self.seed_y_min.get())
        except ValueError:
            ymin = None
        try:
            if self.seed_y_max.get().strip():
                ymax = int(self.seed_y_max.get())
        except ValueError:
            ymax = None
        return ymin, ymax

    # ---- 结构 3D 形状查看 ----
    def _on_view_struct_3d(self):
        if self.seed_gen is None:
            self._err("请先生成地图。")
            return
        sel = self.seed_struct_combo.get()
        item = next((s for s in self._seed_struct_items if s["cn"] == sel), None)
        if not item:
            return
        key = item["key"]

        # 确定展示位置：优先用结果列表选中的行，其次第一个找到的点，最后出生点
        x = z = y = None
        rows = self.seed_tree.selection()
        if rows:
            v = self.seed_tree.item(rows[0], "values")
            try:
                x = int(v[1]); z = int(v[3])
                y = None if v[2] in ("", "-") else int(v[2])
            except Exception:
                x = z = y = None
        if x is None and self.seed_struct_points:
            px, pz, py = self.seed_struct_points[0]
            x, z, y = px, pz, py
        if x is None:
            sx, sz = engine.get_spawn(self.seed_gen)
            x, z = sx, sz
        if y is None:
            y = engine.estimate_height(self.seed_gen, x, z)
        self._open_struct_3d_window(key, x, z, y)

    def _open_struct_3d_window(self, key, x, z, y):
        import matplotlib
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                                      NavigationToolbar2Tk)

        # 中文字体
        for cjk in ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei",
                    "Noto Sans CJK SC", "Arial Unicode MS", "PingFang SC"]:
            try:
                matplotlib.font_manager.findfont(cjk, fallback_to_default=False)
                matplotlib.rcParams["font.sans-serif"] = [cjk]
                matplotlib.rcParams["axes.unicode_minus"] = False
                break
            except Exception:
                continue

        m = structures_3d.get_model(key)
        cn = m["cn"] if m else key
        win = tk.Toplevel(self)
        win.title(f"结构 3D 形状：{cn}  @ ({x}, {z})")
        win.geometry("660x580")
        fig = Figure(figsize=(6.4, 5.2), dpi=100)
        ax = fig.add_subplot(111, projection="3d")
        ok = structures_3d.draw_model_3d(
            ax, key, x, z, y,
            title=f"{cn}  @ X{x} Z{z}（尺寸为近似示意）")
        if not ok:
            ax.text(0, 0, 0, "该结构暂无 3D 模型")
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        NavigationToolbar2Tk(canvas, win).pack()
        fig.tight_layout()
        canvas.draw()
        ttk.Label(
            win,
            text="说明：结构外形为基于真实尺寸的示意模型，用于直观查看大小与比例，并非逐方块还原。",
            foreground="#888888", wraplength=620).pack(side="bottom")

    # ---- 矿石搜索 ----
    def _on_search_ore(self):
        if self.seed_gen is None:
            self._err("请先生成地图。")
            return
        sel = self.seed_ore_combo.get()
        item = next((c for k, c in self._seed_ore_items if c["name"] == sel), None)
        if not item:
            return
        area = self._area_from_map(self.seed_map)
        om = ores.OreModel(self.seed_version_int, int(self.seed_entry.get()))
        key = None
        for k, c in self._seed_ore_items:
            if c is item:
                key = k
        biome_fn = (lambda x, z: engine.get_biome_id(self.seed_gen, x, 64, z)
                    if item.get("biomes") == "mountain" else None)

        self._set_status(f"正在搜索 {item['name']} …")

        def work(p):
            return om.find_ore(key, area[0], area[1], area[2], area[3],
                              max_results=400, biome_fn=biome_fn)

        def done(res):
            if res[0] == "error":
                self._err("搜索失败：" + res[1])
                return
            results = res[1]
            self._clear_results(self.seed_tree)
            for (x, y, z) in results:
                d = ""
                self._add_result(self.seed_tree, item["name"], x, y, z, d,
                                f"Y={y}")
            self._set_status(f"{item['name']}：搜索到 {len(results)} 处（坐标近似，Y 精确）")
        self._run_bg(work, None, done)

    def _on_seed_composition(self):
        if self.seed_gen is None:
            self._err("请先生成地图。")
            return
        area = self._area_from_map(self.seed_map)
        om = ores.OreModel(self.seed_version_int, int(self.seed_entry.get()))
        self._set_status("正在统计区域方块构成 …")
        self.seed_pb["value"] = 0

        def work(p):
            return om.composition(area[0], area[1], area[2], area[3],
                                 biome_fn=lambda x, z: engine.get_biome_id(
                                     self.seed_gen, x, 64, z))

        def done(res):
            if res[0] == "error":
                self._err("统计失败：" + res[1])
                return
            comp = res[1]
            self._clear_results(self.seed_tree)
            for k, v in comp.items():
                c = v["cfg"]
                note = f"约{v['count']}矿脉; 样例Y见下"
                self._add_result(self.seed_tree, c["name"], "-", "-", "-", "-",
                                f"预计约 {v['count']} 个矿脉 ({c['note']})")
            self.seed_pb["value"] = 100
            self._set_status("区域矿石构成已列出（基于生成参数估计）")
        self._run_bg(work, lambda f: self.seed_pb.config(value=f * 100), done)

    # ---- 3D（种子）----
    def _seed_3d(self):
        g = self.seed_gen
        if g is None:
            return {"X": np.array([]), "Y": np.array([]), "Z": np.array([]),
                    "points": [], "title": "3D 预览（请先生成地图）"}
        b = self.seed_map.view_bounds()
        n = 46
        xs = np.linspace(b[0], b[2], n)
        zs = np.linspace(b[1], b[3], n)
        X, Y, Z = [], [], []
        for z in zs:
            for x in xs:
                X.append(x); Y.append(z)
                Z.append(engine.estimate_height(g, int(x), int(z)))
        X = np.array(X); Y = np.array(Y); Z = np.array(Z)
        pts = [(p[0], p[2], p[1]) for p in self.seed_struct_points]
        return {"X": X, "Y": Y, "Z": Z, "points": pts,
                "title": f"3D 地形预览（{self.ver_combo.get()}）"}

    # ------------------------------------------------------------------
    # 存档查询选项卡
    # ------------------------------------------------------------------
    def _build_save_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="存档查询")

        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=4, pady=4)
        right = ttk.Frame(tab)
        right.pack(side="right", fill="both", expand=True, padx=4, pady=4)

        pw = ttk.PanedWindow(left, orient="vertical")
        pw.pack(fill="both", expand=True)
        ctrls = ttk.Frame(pw, width=380)
        resf = ttk.Frame(pw)
        pw.add(ctrls, weight=2)
        pw.add(resf, weight=3)

        row = 0
        self.btn_open = ttk.Button(ctrls, text="打开存档文件夹…",
                                   command=self._on_open_save)
        self.btn_open.grid(row=row, column=0, columnspan=3, sticky="we", pady=2)
        row += 1

        self.save_info = tk.StringVar(value="尚未打开存档")
        ttk.Label(ctrls, textvariable=self.save_info, foreground="#cccccc",
                  wraplength=360, justify="left").grid(
            row=row, column=0, columnspan=3, sticky="w")
        row += 1

        ttk.Label(ctrls, text="维度:").grid(row=row, column=0, sticky="w")
        self.save_dim_combo = ttk.Combobox(ctrls, width=24, state="readonly")
        self.save_dim_combo.set("主世界")
        self.save_dim_combo.grid(row=row, column=1, columnspan=2, sticky="we")
        self.save_dim_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self._save_dim_changed())
        row += 1

        self.btn_load_map = ttk.Button(ctrls, text="加载地图（仅已加载区块）",
                                       command=self._on_load_save_map)
        self.btn_load_map.grid(row=row, column=0, columnspan=3, sticky="we", pady=2)
        row += 1
        self.save_pb = ttk.Progressbar(ctrls, mode="determinate")
        self.save_pb.grid(row=row, column=0, columnspan=3, sticky="we")
        row += 1

        nav = ttk.Frame(ctrls)
        nav.grid(row=row, column=0, columnspan=3, sticky="we", pady=2)
        ttk.Button(nav, text="放大", width=7, command=lambda: self._zoom_save(0.7)).pack(side="left")
        ttk.Button(nav, text="缩小", width=7, command=lambda: self._zoom_save(1.4)).pack(side="left")
        ttk.Button(nav, text="清除选择", width=9, command=lambda: self.save_map.clear_structures()).pack(side="left")
        row += 1
        self.save_sel_label = ttk.Label(ctrls, text="选区：未选择", foreground="#aaaaaa")
        self.save_sel_label.grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1

        self.btn_3d_save = ttk.Button(ctrls, text="一键 3D 预览",
                                      command=lambda: self._on_3d_toggle("save"))
        self.btn_3d_save.grid(row=row, column=0, columnspan=3, sticky="we", pady=2)
        row += 1

        ttk.Separator(ctrls, orient="horizontal").grid(row=row, column=0, columnspan=3, sticky="we", pady=4)
        row += 1
        ttk.Label(ctrls, text="— 方块查询（真实数据）—").grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1
        ttk.Label(ctrls, text="方块名(含):").grid(row=row, column=0, sticky="w")
        self.save_block_entry = ttk.Entry(ctrls, width=18)
        self.save_block_entry.insert(0, "diamond_ore")
        self.save_block_entry.grid(row=row, column=1, columnspan=2, sticky="we")
        row += 1
        ttk.Button(ctrls, text="搜索该方块", command=self._on_save_search_block).grid(
            row=row, column=0, columnspan=2, sticky="we")
        ttk.Button(ctrls, text="选区方块构成", command=self._on_save_composition).grid(
            row=row, column=2, sticky="we")
        row += 1
        ttk.Label(ctrls, text="提示：只读取磁盘上已生成的 .mca，未加载区块不会凭空生成。",
                  foreground="#888888", wraplength=360).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=2)
        row += 1

        # 结果
        cols = ("类型", "X", "Y", "Z", "距离", "备注")
        self.save_tree = ttk.Treeview(resf, columns=cols, show="headings", height=18)
        for c in cols:
            self.save_tree.heading(c, text=c)
        for c, w in zip(cols, (90, 70, 60, 70, 60, 150)):
            self.save_tree.column(c, width=w)
        sb = ttk.Scrollbar(resf, orient="vertical", command=self.save_tree.yview)
        self.save_tree.configure(yscrollcommand=sb.set)
        self.save_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        ttk.Button(resf, text="复制选中坐标", command=lambda: self._copy_selected(self.save_tree)).pack(side="bottom", fill="x")

        # 地图
        self.save_map = MapView(right)
        self.save_map.container.pack(fill="both", expand=True)
        self.save_map.render_callback = self._save_render_callback
        self.save_map.get_3d_data = self._save_3d
        self._save_sel_poll()

    def _save_sel_poll(self):
        sel = self.save_map.selection
        if sel:
            self.save_sel_label.config(text=f"选区 X[{sel[0]},{sel[2]}] Z[{sel[1]},{sel[3]}]")
        else:
            self.save_sel_label.config(text="选区：未选择（将使用整张地图范围）")
        self.after(250, self._save_sel_poll)

    def _on_open_save(self):
        folder = filedialog.askdirectory(title="选择 Minecraft 存档文件夹（含 level.dat）")
        if not folder:
            return
        if not os.path.isfile(os.path.join(folder, "level.dat")):
            self._err("该文件夹不是有效的存档（未找到 level.dat）。")
            return
        self.save_obj = saves.Save(folder)
        dims = self.save_obj.dimensions()
        self.save_dim_combo["values"] = dims
        if self.save_dim not in dims:
            self.save_dim = dims[0]
        self.save_dim_combo.set(self.save_dim)
        info = (f"名称: {self.save_obj.name}\n"
                f"种子: {self.save_obj.info.get('seed','未知')}\n"
                f"版本: {self.save_obj.info.get('version_name', '未知')} "
                f"(DataVersion={self.save_obj.info.get('data_version','?')})\n"
                f"可用维度: {', '.join(dims)}")
        self.save_info.set(info)
        self._set_status("已打开存档，请选择维度后加载地图")

    def _save_dim_changed(self):
        self.save_dim = self.save_dim_combo.get()

    def _zoom_save(self, factor):
        self.save_map.bpp = max(1, min(64, int(round(self.save_map.bpp * factor))))
        self.save_map.bpp_eff = self.save_map.bpp / self.save_map.disp_scale
        self.save_map.render()

    def _on_load_save_map(self):
        if self.save_obj is None:
            self._err("请先打开存档。")
            return
        self.save_dim = self.save_dim_combo.get()
        dim = self.save_dim
        self._set_status(f"正在加载 {dim} 已加载区块地图…")
        self.save_pb["value"] = 0

        def work(p):
            return self.save_obj.render_top_map(
                dim, self.save_map.center_x, self.save_map.center_z,
                self.save_map.render_w, self.save_map.render_h,
                blocks_per_px=self.save_map.bpp, callback=p)

        def done(res):
            if res[0] == "error":
                self._err("加载失败：" + res[1])
                return
            data = res[1]
            cx = data["min_x"] + (self.save_map.render_w * self.save_map.bpp) / 2
            cz = data["min_z"] + (self.save_map.render_h * self.save_map.bpp) / 2
            self.save_map.show_image(data["image"], center_x=cx, center_z=cz)
            self.save_pb["value"] = 100
            nch = len(self.save_obj.loaded_chunks(dim))
            self._set_status(f"{dim} 已加载区块数: {nch}（灰色=未加载）")
        self._run_bg(work, lambda f: self.save_pb.config(value=f * 100), done)

    def _save_render_callback(self, cx, cz, rw, rh, bpp):
        if self.save_obj is None:
            return None
        return self.save_obj.render_top_map(self.save_dim, cx, cz, rw, rh,
                                           blocks_per_px=bpp)["image"]

    def _on_save_search_block(self):
        if self.save_obj is None:
            self._err("请先打开存档并加载地图。")
            return
        kw = self.save_block_entry.get().strip()
        if not kw:
            self._err("请输入方块名，如 diamond_ore / chest / spawner")
            return
        area = self._area_from_map(self.save_map)
        dim = self.save_dim
        self._set_status(f"在已加载区块中搜索 {kw} …")
        self.save_pb["value"] = 0

        def work(p):
            return self.save_obj.find_blocks(dim, kw, max_results=3000,
                                            x0=area[0], z0=area[1], x1=area[2], z1=area[3],
                                            callback=p)

        def done(res):
            if res[0] == "error":
                self._err("搜索失败：" + res[1])
                return
            results = res[1]
            self._clear_results(self.save_tree)
            pts = []
            for (x, y, z, nm) in results:
                d = math.dist((x, z), (0, 0))
                self._add_result(self.save_tree, nm.split(":")[-1], x, y, z, d, "")
                pts.append((x, y, z))
            self.save_block_points = pts
            self.save_pb["value"] = 100
            self._set_status(f"在已加载区块中找到 {len(results)} 个匹配 {kw} 的方块")
        self._run_bg(work, lambda f: self.save_pb.config(value=f * 100), done)

    def _on_save_composition(self):
        if self.save_obj is None:
            self._err("请先打开存档并加载地图。")
            return
        area = self._area_from_map(self.save_map)
        dim = self.save_dim
        self._set_status("正在统计选区方块构成（已加载区块）…")
        self.save_pb["value"] = 0

        def work(p):
            return self.save_obj.count_blocks(dim, area[0], area[1], area[2], area[3],
                                             chunk_limit=1200, callback=p)

        def done(res):
            if res[0] == "error":
                self._err("统计失败：" + res[1])
                return
            cnt = res[1]
            self._clear_results(self.save_tree)
            for nm, c in cnt.most_common(200):
                self._add_result(self.save_tree, nm.split(":")[-1], "-", "-", "-", c, "")
            self.save_pb["value"] = 100
            self._set_status(f"选区共统计到 {len(cnt)} 种方块，已按数量排序")
        self._run_bg(work, lambda f: self.save_pb.config(value=f * 100), done)

    def _save_3d(self):
        if self.save_obj is None:
            return {"X": np.array([]), "Y": np.array([]), "Z": np.array([]),
                    "points": [], "title": "3D 预览（请先加载存档）"}
        dim = self.save_dim
        b = self.save_map.view_bounds()
        cx0, cx1 = b[0] // 16, b[2] // 16
        cz0, cz1 = b[1] // 16, b[3] // 16
        chunks = [(c[0], c[1]) for c in self.save_obj.loaded_chunks(dim)
                  if cx0 <= c[0] <= cx1 and cz0 <= c[1] <= cz1]
        chunks = chunks[:2000]
        X, Y, Z, P = [], [], [], []
        for (cx, cz) in chunks:
            rx, rz = cx // 32, cz // 32
            reg = self.save_obj.get_region(dim, rx, rz)
            if reg is None:
                continue
            lx, lz = cx - rx * 32, cz - rz * 32
            if reg.chunk_location(lx, lz) == (0, 0):
                continue
            # 顶部方块高度
            top = None
            for y in range(319, -64, -2):
                nm = self.save_obj.get_block(dim, cx * 16 + 8, y, cz * 16 + 8)
                if nm and "air" not in nm:
                    top = y
                    break
            if top is None:
                top = -64
            X.append(cx * 16 + 8); Y.append(cz * 16 + 8); Z.append(top)
        for p in self.save_block_points:
            P.append((p[0], p[2], p[1]))
        return {"X": np.array(X), "Y": np.array(Y), "Z": np.array(Z),
                "points": P, "title": f"3D 真实地形（{dim}，已加载区块）"}

    # ------------------------------------------------------------------
    # 3D 切换（通用）
    # ------------------------------------------------------------------
    def _on_3d_toggle(self, tab):
        mv = self.seed_map if tab == "seed" else self.save_map
        if mv.mode_3d:
            mv.toggle_3d()
            self._set_status("已切回 2D 地图")
            return
        self._set_status("正在计算 3D 数据…")

        def work(p):
            if tab == "seed":
                return self._seed_3d()
            return self._save_3d()

        def done(res):
            if res[0] == "error":
                self._err("3D 生成失败：" + res[1])
                return
            mv.get_3d_data = lambda: res[1]
            mv.toggle_3d()
            self._set_status("3D 预览已生成（可拖拽旋转/缩放）")
        self._run_bg(work, None, done)


if __name__ == "__main__":
    app = App()
    app.mainloop()

# -*- coding: utf-8 -*-
"""
地图视图组件：2D 画布（生物群系/顶部方块地图，支持框选区域、平移、缩放）
+ 可一键切换的 3D 预览（matplotlib 嵌入）。
内部以较低分辨率渲染再放大显示，保证生成速度。
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# 必须在导入任何 matplotlib 后端模块之前设置 backend
import matplotlib
matplotlib.use("TkAgg")


class MapView:
    def __init__(self, master, width=620, height=560):
        self.width = width
        self.height = height
        self.render_w = 310
        self.render_h = 280
        self.disp_scale = width / self.render_w

        self.container = ttk.Frame(master)
        self.canvas = tk.Canvas(self.container, width=width, height=height,
                                bg="#3a3a3a", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.frame3d = ttk.Frame(self.container)
        self._fig_canvas = None
        self._fig_toolbar = None

        # 状态
        self.center_x = 0
        self.center_z = 0
        self.bpp = 8            # 每个“渲染像素”代表多少方块（缩放档位）
        self.bpp_eff = self.bpp / self.disp_scale
        self.photo = None
        self.image = None
        self.sel_rect = None
        self.sel_start = None
        self.selection = None   # (wx0,wz0,wx1,wz1) 世界坐标
        self.structures = []    # (wx, wz, color, label)
        self.mode_3d = False

        self.render_callback = None   # fn(cx,cz,rw,rh,bpp)->PIL.Image(渲染分辨率)
        self.get_3d_data = None      # fn()->dict(X,Y,Z,C,points,title)

        self._bind_events()

    # ---- 事件 ----
    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag_select)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<ButtonPress-3>", self._on_pan_press)
        self.canvas.bind("<B3-Motion>", self._on_pan_drag)
        self.canvas.bind("<MouseWheel>", self._on_wheel)

    def _on_press(self, e):
        if self.mode_3d:
            return
        self.sel_start = (e.x, e.y)
        if self.sel_rect:
            self.canvas.delete(self.sel_rect)
        self.sel_rect = self.canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="#ffcc00", width=2, dash=(4, 3))

    def _on_drag_select(self, e):
        if self.mode_3d or not self.sel_rect:
            return
        x0, y0 = self.sel_start
        self.canvas.coords(self.sel_rect, x0, y0, e.x, e.y)

    def _on_release(self, e):
        if self.mode_3d or not self.sel_rect:
            return
        x0, y0 = self.sel_start
        x1, y1 = e.x, e.y
        wx0, wz0 = self.screen_to_world(min(x0, x1), min(y0, y1))
        wx1, wz1 = self.screen_to_world(max(x0, x1), max(y0, y1))
        if abs(wx1 - wx0) < 8 or abs(wz1 - wz0) < 8:
            self.canvas.delete(self.sel_rect)
            self.sel_rect = None
            self.selection = None
        else:
            self.selection = (wx0, wz0, wx1, wz1)

    def _on_pan_press(self, e):
        self._pan_start = (e.x, e.y, self.center_x, self.center_z)

    def _on_pan_drag(self, e):
        if self.mode_3d:
            return
        x0, y0, cx, cz = self._pan_start
        dx = (e.x - x0) * self.bpp_eff
        dy = (e.y - y0) * self.bpp_eff
        self.center_x = cx - dx
        self.center_z = cz - dy
        self.render()

    def _on_wheel(self, e):
        if self.mode_3d:
            return
        wx, wz = self.screen_to_world(e.x, e.y)
        factor = 0.82 if e.delta > 0 else 1.22
        self.bpp = max(1, min(64, int(round(self.bpp * factor))))
        self.bpp_eff = self.bpp / self.disp_scale
        self.center_x = wx + (e.x - self.width / 2) * self.bpp_eff
        self.center_z = wz + (e.y - self.height / 2) * self.bpp_eff
        self.render()

    # ---- 坐标变换（基于显示像素与 bpp_eff）----
    def screen_to_world(self, px, py):
        min_x = self.center_x - self.width * self.bpp_eff / 2
        min_z = self.center_z - self.height * self.bpp_eff / 2
        return int(min_x + px * self.bpp_eff), int(min_z + py * self.bpp_eff)

    def world_to_screen(self, wx, wz):
        min_x = self.center_x - self.width * self.bpp_eff / 2
        min_z = self.center_z - self.height * self.bpp_eff / 2
        return (wx - min_x) / self.bpp_eff, (wz - min_z) / self.bpp_eff

    def view_bounds(self):
        w = self.width * self.bpp_eff
        h = self.height * self.bpp_eff
        return (int(self.center_x - w / 2), int(self.center_z - h / 2),
                int(self.center_x + w / 2), int(self.center_z + h / 2))

    # ---- 渲染 ----
    def _display(self, img):
        self.image = img
        disp = img.resize((self.width, self.height), Image.NEAREST)
        self.photo = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self._draw_structures()
        if self.selection:
            wx0, wz0, wx1, wz1 = self.selection
            sx0, sy0 = self.world_to_screen(wx0, wz0)
            sx1, sy1 = self.world_to_screen(wx1, wz1)
            self.sel_rect = self.canvas.create_rectangle(
                sx0, sy0, sx1, sy1, outline="#ffcc00", width=2, dash=(4, 3))

    def show_image(self, img, center_x=None, center_z=None):
        if self.mode_3d:
            return
        if center_x is not None:
            self.center_x = center_x
        if center_z is not None:
            self.center_z = center_z
        self._display(img)

    def render(self):
        if self.mode_3d:
            return
        if self.render_callback is None:
            return
        img = self.render_callback(self.center_x, self.center_z,
                                  self.render_w, self.render_h, self.bpp)
        if img is None:
            return
        self._display(img)

    def _draw_structures(self):
        for wx, wz, color, _ in self.structures:
            sx, sy = self.world_to_screen(wx, wz)
            if -12 <= sx <= self.width + 12 and -12 <= sy <= self.height + 12:
                self.canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4,
                                        fill=color, outline="white", width=1)

    def set_structures(self, struct_list):
        self.structures = struct_list
        if not self.mode_3d:
            self._draw_structures()

    def clear_structures(self):
        self.structures = []
        self.selection = None
        self.render()

    # ---- 3D ----
    def toggle_3d(self):
        if self.mode_3d:
            self._show_2d()
        else:
            self._show_3d()
        return self.mode_3d

    def _show_2d(self):
        self.mode_3d = False
        if self._fig_canvas:
            self._fig_canvas.get_tk_widget().pack_forget()
        if self._fig_toolbar:
            self._fig_toolbar.pack_forget()
        self.frame3d.pack_forget()
        self.canvas.pack(fill="both", expand=True)
        self.render()

    def _show_3d(self):
        if self.get_3d_data is None:
            return
        # 尽量使用系统中文字体，避免 3D 标题/坐标出现缺字方框
        for cjk in ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei",
                    "Noto Sans CJK SC", "Arial Unicode MS", "PingFang SC"]:
            try:
                matplotlib.font_manager.findfont(cjk, fallback_to_default=False)
                matplotlib.rcParams["font.sans-serif"] = [cjk]
                matplotlib.rcParams["axes.unicode_minus"] = False
                break
            except Exception:
                continue
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

        data = self.get_3d_data()
        self.mode_3d = True
        self.canvas.pack_forget()
        self.frame3d.pack(fill="both", expand=True)
        if self._fig_canvas is None:
            self.fig = Figure(figsize=(6.2, 5.4), dpi=100)
            self.ax = self.fig.add_subplot(111, projection="3d")
            self._fig_canvas = FigureCanvasTkAgg(self.fig, master=self.frame3d)
            self._fig_canvas.get_tk_widget().pack(fill="both", expand=True)
            self._fig_toolbar = NavigationToolbar2Tk(self._fig_canvas, self.frame3d)
            self._fig_toolbar.pack()
        self.ax.clear()
        X, Y, Z = data.get("X"), data.get("Y"), data.get("Z")
        points = data.get("points")
        if X is not None and len(X) > 0:
            self.ax.plot_trisurf(X, Y, Z, cmap="terrain", alpha=0.85,
                                 linewidth=0, antialiased=True)
        if points:
            import numpy as np
            pa = np.array(points)
            self.ax.scatter(pa[:, 0], pa[:, 1], pa[:, 2], c="red", s=28,
                           depthshade=False, label="结构/方块")
        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Z")
        self.ax.set_zlabel("Y (高度)")
        self.ax.set_title(data.get("title", "3D 预览"))
        self.fig.tight_layout()
        self._fig_canvas.draw()

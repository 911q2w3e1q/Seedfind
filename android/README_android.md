# Minecraft 种子查询器 · 安卓版（Kivy）

用 **Kivy** 重写的安卓端，复用桌面版同一套引擎逻辑（`engine / ores / saves / structures_3d`），功能与桌面版一致：

- 种子查询：版本（下拉最新显示为 **26.3**）、维度、生物群系地图
- 结构搜索：选结构 → 设 **Y 范围** + **距出生点上限** → 按半径 / 选区筛选
- 矿石 / 方块搜索、区域方块构成
- **框选区域**（地图“框选模式”按钮切换 拖拽=框选 / 拖拽=平移，双指或按钮缩放）
- **一键 3D 预览**（地形高度 + 结构/方块散点）
- **查看结构 3D 形状**（近似真实尺寸的 3D 模型，直观看大小/比例）
- 存档查询：打开含 `level.dat` 的存档，**只读取已加载区块**的真实方块

> 说明：本目录是一个**可编译工程**。但出包只需**一条命令**（`bash build.sh`，内部即 `buildozer android debug`），它会自动用 NDK 把 `cubiomes` 原生库交叉编译成手机架构，再打包，**最终只产出【一个】arm64-v8a 的 `.apk`**。`cubiomes` 必须在你电脑上用 NDK 编译（无法在别人机器预编译后通用），所以交付的是工程而非现成 apk——但对你来说就是跑一条命令。

---

## 目录结构

```
android/
├── main.py                 # Kivy 界面与全部交互逻辑（安卓版入口）
├── engine.py / ores.py / saves.py / structures_3d.py   # 与桌面版同款引擎
├── cubiomespi/             # cubiomes 本地包（Python 加载器 + C 源码；lib_c.so 在打包时自动交叉编译）
│   ├── cubiomes.py         # 用 ctypes 加载 lib_c.so
│   ├── constants.py / util.py / __init__.py
│   └── lib/                # 原生 C 源码（newlib.c + lib/cubiomes/*.c|*.h|tables/）
├── build.sh                # 一键出包（= buildozer android debug，单命令产出单个 apk）
├── tools/build_cubiomes_android.sh   # 交叉编译 lib_c.so（由 buildozer 的 pre_build_cmd 自动调用）
├── buildozer.spec          # 打包配置
├── tools/build_cubiomes_android.sh   # 交叉编译 lib_c.so 的脚本
└── README_android.md       # 本文件
```

---

## 一、准备环境（一次性）

需要本地有 Python 3.11、JDK 17、Android SDK + NDK，以及 `buildozer`。

### 1. 安装 buildozer（建议用虚拟环境）
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install buildozer
```
> 首次运行 `buildozer android debug` 会自动下载 Android SDK / NDK / build-tools 并解压到 `~/.buildozer`。
> 也可以自己装 Android Studio 的 SDK Manager，把 `ANDROID_SDK_ROOT` 指过去。

### 2. 安装 Android NDK（用于编译 cubiomes 原生库）
推荐 NDK **25b**（与 `buildozer.spec` 的 `android.ndk = 25b` 对应）。
- 用 Android Studio 的 SDK Manager 安装 NDK (Side by Side) 25.x；或
- 命令行下载并解压到某目录，例如 `~/Android/Sdk/ndk/25.0.8775105`。

---

## 二、一条命令出包（编译 + 打包）

种子/结构/矿石的计算依赖 cubiomes 的 C 库，打包时**会自动**用 NDK 把它编成手机的 `lib_c.so`（见 `buildozer.spec` 的 `android.pre_build_cmd`），无需手动操作。只要一条命令：

```bash
cd android
bash build.sh                 # 等价于： buildozer android debug
```

- 首次运行会自动下载 Android SDK / NDK r25b / build-tools 并解压到 `~/.buildozer`，请耐心等待（约几百 MB～1GB，取决于网速）。
- 成功后得到**单个** apk：`android/bin/Seedquery-1.0-arm64-v8a-debug.apk`。
- 想支持 32 位旧手机（armeabi-v7a）？编辑 `tools/build_cubiomes_android.sh` 把 `TARGET` 改成 `armv7a-linux-androideabi`，并在 `buildozer.spec` 的 `android.archs` 加上 `armeabi-v7a` 再重跑；此时会产出对应架构的单个 apk。
- 想出 release 包（可分享/上架）：`buildozer android release`（需要自有签名密钥，参考 buildozer 文档）。

---

## 三、安装到手机

```bash
# 手机开启“开发者选项 → USB 调试”，用数据线连接
adb install bin/Seedquery-1.0-arm64-v8a-debug.apk
```
或直接把 `.apk` 传到手机，在文件管理器里点开安装（需允许“未知来源”）。

---

## 四、权限说明

- 打开本地存档需要读取存储权限。Android 11+ 对“所有文件访问”限制较严：首次打开存档若提示，请在系统设置里给本应用“所有文件访问权限”（我们在 `buildozer.spec` 已声明 `MANAGE_EXTERNAL_STORAGE`）。
- 应用联网不是必须的（全部计算在本地），请勿授予不必要的权限。

---

## 五、常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| 启动后点“生成地图”闪退 / 报找不到 `lib_c` | 打包时 NDK 编译失败（多见于 NDK 未下载或路径不对）。重跑 `bash build.sh` 看 pre_build 阶段的 clang 报错；或手动 `export ANDROID_NDK=...` 后 `bash tools/build_cubiomes_android.sh` 验证。 |
| APK 很大（上百 MB） | matplotlib + numpy + kivy 体积较大，属正常；如需瘦身可改用纯 Kivy 自绘 3D（去掉 matplotlib）。 |
| 打开存档看不到区块 | 只有玩家**实际进入加载过**的区块才有数据；未加载区域不会凭空生成（符合设计）。 |
| 安卓版点“一键 3D 预览”黑屏 | 部分旧机型 matplotlib(KivyAgg) 兼容性差；可改用桌面版，或反馈机型我们优化。 |

---

## 六、与桌面版的差异

- 界面从 tkinter 换成 Kivy（触屏交互：拖拽平移、双指/按钮缩放、框选模式）。
- 引擎逻辑（版本、结构、矿石、存档读取、结构 3D 模型）**完全一致**，只是 UI 层不同。
- 版本下拉显示 **26.1 / 26.2 / 26.3**（Mojang 2025-12 起改用“年.更新”日历版号，1.21.11 之后依次为 26.1→26.2→26.3）。经核实，26.x 的世界生成算法与 1.21.4 完全一致，本应用把 26.x 映射到同一套 Cubiomes 生成器，产出的生物群系/结构坐标对 26.x 是**真实有效**的（详见仓库根目录 README 的“版本说明”）。

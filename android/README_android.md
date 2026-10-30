# Minecraft 种子查询器 · 安卓版（Kivy）

用 **Kivy** 重写的安卓端，复用桌面版同一套引擎逻辑（`engine / ores / saves / structures_3d`），功能与桌面版一致：

- 种子查询：版本（下拉最新显示为 **26.3**）、维度、生物群系地图
- 结构搜索：选结构 → 设 **Y 范围** + **距出生点上限** → 按半径 / 选区筛选
- 矿石 / 方块搜索、区域方块构成
- **框选区域**（地图“框选模式”按钮切换 拖拽=框选 / 拖拽=平移，双指或按钮缩放）
- **一键 3D 预览**（地形高度 + 结构/方块散点）
- **查看结构 3D 形状**（近似真实尺寸的 3D 模型，直观看大小/比例）
- 存档查询：打开含 `level.dat` 的存档，**只读取已加载区块**的真实方块

> 说明：本目录是一个**可编译工程 + 一键出包教程**，不是预编译 APK。原因是 `cubiomes` 原生库必须在你自己的电脑上用 Android NDK 交叉编译成手机架构，沙箱里直接编 APK 容易失败。按下面步骤在自己电脑上即可产出可安装的 `.apk`。

---

## 目录结构

```
android/
├── main.py                 # Kivy 界面与全部交互逻辑（安卓版入口）
├── engine.py / ores.py / saves.py / structures_3d.py   # 与桌面版同款引擎
├── cubiomespi/             # cubiomes 本地包（Python 加载器 + C 源码 + 预编译 lib_c.so）
│   ├── cubiomes.py         # 用 ctypes 加载 lib_c.so
│   ├── constants.py / util.py / __init__.py
│   └── lib/                # 原生 C 源码（newlib.c + lib/cubiomes/*.c|*.h|tables/）
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

## 二、交叉编译 cubiomes 原生库（关键步骤）

种子/结构/矿石的计算依赖 cubiomes 的 C 库。**必须**先用 NDK 把它编成手机的 `lib_c.so`：

```bash
# 指向你的 NDK 根目录
export ANDROID_NDK=$HOME/Android/Sdk/ndk/25.0.8775105

cd android
bash tools/build_cubiomes_android.sh
```

脚本会产出 `android/cubiomespi/lib_c.so`（arm64）。看到 “成功：.../lib_c.so” 即完成。

> 想支持 32 位旧手机（armeabi-v7a）？编辑脚本把 `TARGET` 改成 `armv7a-linux-androideabi`，并在 `buildozer.spec` 的 `android.archs` 加上 `armeabi-v7a`，重新编译即可。

---

## 三、打包 APK

```bash
cd android
buildozer android debug
```

- 首次会下载 SDK/NDK/build-tools（若未自动装），请耐心等待。
- 成功后在 `android/bin/`（或 `.buildozer/android/platform/build-*/outputs/apk/`）得到
  `Seedquery-1.0-arm64-v8a-debug.apk`（或类似名称）。
- 想出 release 包（可上架/分享）：`buildozer android release`，但 release 需要自有签名密钥（参考 buildozer 文档）。

---

## 四、安装到手机

```bash
# 手机开启“开发者选项 → USB 调试”，用数据线连接
adb install bin/Seedquery-1.0-arm64-v8a-debug.apk
```
或直接把 `.apk` 传到手机，在文件管理器里点开安装（需允许“未知来源”）。

---

## 五、权限说明

- 打开本地存档需要读取存储权限。Android 11+ 对“所有文件访问”限制较严：首次打开存档若提示，请在系统设置里给本应用“所有文件访问权限”（我们在 `buildozer.spec` 已声明 `MANAGE_EXTERNAL_STORAGE`）。
- 应用联网不是必须的（全部计算在本地），请勿授予不必要的权限。

---

## 六、常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| 启动后点“生成地图”闪退 / 报找不到 `lib_c` | 没跑第二步的 NDK 编译，或 `cubiomespi/lib_c.so` 不存在。重跑 `build_cubiomes_android.sh`。 |
| APK 很大（上百 MB） | matplotlib + numpy + kivy 体积较大，属正常；如需瘦身可改用纯 Kivy 自绘 3D（去掉 matplotlib）。 |
| 打开存档看不到区块 | 只有玩家**实际进入加载过**的区块才有数据；未加载区域不会凭空生成（符合设计）。 |
| 安卓版点“一键 3D 预览”黑屏 | 部分旧机型 matplotlib(KivyAgg) 兼容性差；可改用桌面版，或反馈机型我们优化。 |

---

## 七、与桌面版的差异

- 界面从 tkinter 换成 Kivy（触屏交互：拖拽平移、双指/按钮缩放、框选模式）。
- 引擎逻辑（版本、结构、矿石、存档读取、结构 3D 模型）**完全一致**，只是 UI 层不同。
- 版本下拉仍显示 **26.3** 作为最新（底层为 Cubiomes 最新可用生成引擎，详见仓库根目录 README 的“已知限制”）。

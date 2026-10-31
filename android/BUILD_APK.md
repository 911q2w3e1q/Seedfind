# APK 构建说明（arm64-v8a 单架构）

## 产物

| 项 | 值 |
|---|---|
| 文件 | `bin/seedquery-1.0-arm64-v8a-debug.apk`（仓库交付副本为 `android/seedquery-1.0-arm64-v8a.apk`） |
| 大小 | 43,561,462 字节（约 41.5 MB） |
| 包名 | `com.seedquery.seedquery` |
| 应用名 | Minecraft 种子查询器 |
| versionName / versionCode | 1.0 / 1024100 |
| minSdk / targetSdk | 24（Android 7.0）/ 33（Android 13） |
| 架构 | 仅 arm64-v8a（真机绝大多数机型） |
| 权限 | READ/WRITE_EXTERNAL_STORAGE、MANAGE_EXTERNAL_STORAGE |
| SHA256 | `319ac62a2e8c8a79530977fc5ba1211d6154e5a1eaec11e2b1c0988beb52a7ff` |

安装：把 apk 传到手机 → 用文件管理器点击安装 → 允许「安装未知来源应用」。

## 重新构建

```bash
cd android
bash build.sh
```

脚本已内置 JDK、pip 镜像、本地源码注入三项配置（见 `build.sh` 注释）。

## 离线依赖清单（工程内已自带）

| 目录 | 内容 | 版本 | 为何需要 |
|---|---|---|---|
| `.numpy_src/` | numpy 源码（含 `.git`，tag `v1.26.4`） | 1.26.4 | `setuptools_scm` 依赖 git tag 取版本，故保留 `.git` |
| `.kivy_src/` | kivy 源码（行尾已统一为 LF） | 2.3.1 | 需与 recipe 默认版本一致，否则 patch 上下文不匹配 |
| `.mpl_src/` | matplotlib 源码（meson-only） | 3.10.7 | 3.7.5 是 setuptools 构建，MesonRecipe 需要 meson 后端 |
| `.pillow_src/` | pillow 源码 | 11.3.0 | recipe 的 patch 针对 11.3.0 |
| `.pyjnius_src/` | pyjnius 源码 | 1.7.0 | Java 桥接 |
| `.kiwi_src/` | kiwisolver 源码 | 1.4.5 | matplotlib 依赖 |

注入方式为 p4a 的 `P4A_<RECIPE>_DIR` 环境变量：设置后该 recipe **完全跳过下载**，直接使用本地源码。

## 踩坑要点（供后续维护参考）

1. **版本必须与 recipe 默认版本对齐**：p4a 的 kivy / pillow / matplotlib recipe 自带 patch，
   版本不一致时 patch 报 `Hunk #N FAILED` 而构建失败。
2. **PyPI sdist 是 CRLF 行尾**，而 patch 基于 git 源码（LF）编写，会报
   `different line endings`；需对源码树做 CRLF→LF 转换。
3. **matplotlib 3.9+ 依赖 contourpy**（C 扩展），3.10.7 走 meson 后端。
4. **p4a 把 pip 的 HOME 设为 `/tmp`**，用户级 `~/.config/pip/pip.conf` 失效，
   必须用 `PIP_INDEX_URL` 环境变量指定镜像；同时 pip ≥23.1 需要 `PIP_BREAK_SYSTEM_PACKAGES=1`。
5. **SDL2_image 的 8 个 external 依赖**（jpeg/libpng/libwebp/libtiff/zlib/libjxl/libavif/dav1d）
   由 p4a 在构建时 `git clone`；p4a 判定「目录非空即跳过 clone」，
   故可预置目录绕过（仅 jpeg/libpng/libwebp 会被真正编译，其余开关默认关闭）。
6. **gradle 发行版**从 `services.gradle.org` 下载极慢，改用
   `https://mirrors.cloud.tencent.com/gradle/gradle-8.14.3-all.zip`
   预置到 `~/.gradle/wrapper/dists/gradle-8.14.3-all/<hash>/`。
7. **版本号「26.3」**：由 `main.py` 顶部常量显示，与 apk 的 versionName（1.0）无关。

## MIUI / 国产 ROM 启动闪退修复（重要）

早期版本在 MIUI 14 等严格 SELinux 的国产 ROM 上，打开后停在加载界面即闪退。
根因：`cubiomespi/lib_c.so` 仅随 Python 包（`assets/private.tar`）解压到 App 私有目录，
而这类 ROM 会拒绝从该目录 `dlopen` 原生库（与 `libmain.so` / `libpython` 由系统安装到
`/data/app/<pkg>/lib/arm64/` 后被允许形成对比）。

修复：
- 新增**本地 p4a recipe**（`p4a_recipes/cubiomeslib/`），把 `lib_c.so` 打进 APK 的
  `lib/arm64-v8a/`，由系统安装到 App 原生库目录（与 `libpython` 同处，MIUI 允许加载）。
- `cubiomespi/cubiomes.py` 改为**优先按文件名 `lib_c.so` 加载**（p4a 的 SDL `start.c` 已把
  App 原生库目录写入 `LD_LIBRARY_PATH`，Android linker 可直接按名找到），包内路径仅作兜底。
- `buildozer.spec` 增加 `p4a.local_recipes = ./p4a_recipes` 并把 `cubiomeslib` 加入 `requirements`。

## 崩溃自报告

`main.py` 顶部注册了 `sys.excepthook`：任何未捕获异常都会
**写文件 + 弹红屏**。若仍闪退，红屏会显示 Python 完整 traceback，
同时在 App 私有目录生成 `seedquery_crash.txt`。把红屏文字或该文件内容发回即可快速定位。

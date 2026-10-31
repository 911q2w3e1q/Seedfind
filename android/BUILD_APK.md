# APK 构建说明（arm64-v8a 单架构）

## 产物

| 项 | 值 |
|---|---|
| 文件 | `bin/seedquery-1.0-arm64-v8a-debug.apk` |
| 大小 | 43,096,362 字节（约 41 MB） |
| 包名 | `com.seedquery.seedquery` |
| 应用名 | Minecraft 种子查询器 |
| versionName / versionCode | 1.0 / 1024100 |
| minSdk / targetSdk | 24（Android 7.0）/ 33（Android 13） |
| 架构 | 仅 arm64-v8a（真机绝大多数机型） |
| 权限 | READ/WRITE_EXTERNAL_STORAGE、MANAGE_EXTERNAL_STORAGE |
| SHA256 | `16e3cd8c79330e5f0dc2e1997dcdc436f4044fb8...`（见下方 `sha256sum`） |

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

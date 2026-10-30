#!/usr/bin/env bash
# ===================================================================
# 交叉编译 cubiomes 原生库 (lib_c.so) 为 Android 架构
#
# 为什么需要它：
#   种子/结构/矿石/生物群系的计算依赖 cubiomes 的 C 库。安卓上不能复用电脑的
#   .so，必须用 Android NDK 把它编译成手机架构。本脚本产出
#   <工程根>/cubiomespi/lib_c.so，之后 buildozer 会把 .so 一并打进 APK。
#
# 两种用法（二选一）：
#   用法 A（推荐，已默认接入）：什么都不用做。
#       buildozer 会在打包前自动调用本脚本（见 buildozer.spec 的
#       android.pre_build_cmd），并自动把 NDK 路径注入进来。
#   用法 B（手动 / 调试）：
#       export ANDROID_NDK=$HOME/Android/Sdk/ndk/25.0.8775105
#       bash tools/build_cubiomes_android.sh
#
# 默认按 arm64-v8a 编译（对应 buildozer.spec 的 android.archs）。
# 想编 32 位(armeabi-v7a)旧手机？把下面 TARGET/API 改成 armv7a-linux-androideabi，
# 并在 buildozer.spec 的 android.archs 加上 armeabi-v7a，再重跑即可。
# ===================================================================
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$HERE/cubiomespi"
SRC="$PKG/lib"            # 含 newlib.c
CB="$PKG/lib/cubiomes"    # 含 cubiomes 的 .c/.h 与 tables/

# ---- 自动定位 NDK（按优先级）----
NDK="${ANDROID_NDK:-${ANDROIDNDK:-}}"
if [ -z "$NDK" ]; then
  # buildozer / python-for-android 自动下载的 NDK 通常在这里
  CANDIDATE="$(ls -d "$HOME/.buildozer/android/packages/"*/android-ndk-* 2>/dev/null | sort -r | head -1)"
  if [ -n "$CANDIDATE" ]; then
    NDK="$CANDIDATE"
  fi
fi
if [ -z "$NDK" ]; then
  echo "错误：找不到 Android NDK。请任选其一："
  echo "  1) 设置环境变量： export ANDROID_NDK=/path/to/ndk"
  echo "  2) 先运行一次 buildozer android debug（它会自动下载 NDK），再重跑本脚本"
  exit 1
fi
echo "使用 NDK: $NDK"

# ---- 架构 / API ----
API=21
TARGET=aarch64-linux-android
CLANG="$NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/${TARGET}${API}-clang"
if [ ! -x "$CLANG" ]; then
  echo "错误：找不到 NDK clang：$CLANG"
  echo "请确认 NDK 版本含 api-$API 工具链（建议 NDK 25b，与 buildozer.spec 对应）。"
  exit 1
fi

OUT="$PKG/lib_c.so"
echo "正在用 $CLANG 编译 lib_c.so (aarch64) ..."
"$CLANG" -shared -fPIC -I "$CB" \
  "$CB"/*.c "$SRC"/newlib.c -o "$OUT" -lm

if [ -f "$OUT" ]; then
  echo "成功：$OUT"
else
  echo "编译失败，请检查上面的报错。"
  exit 1
fi

#!/usr/bin/env bash
# ===================================================================
# 交叉编译 cubiomes 原生库 (lib_c.so) 为 Android arm64 架构
#
# 为什么需要它：
#   种子/结构/矿石/生物群系的计算依赖 cubiomes 的 C 库。安卓上不能复用电脑的
#   .so，必须用 Android NDK 把它编译成手机架构(aarch64)。本脚本产出
#   ../cubiomespi/lib_c.so，之后 buildozer 会把 .so 一并打进 APK。
#
# 用法：
#   1) 安装 Android NDK（推荐 25b，与 buildozer.spec 中 android.ndk 对应）
#   2) 设置环境变量 ANDROID_NDK 指向 NDK 根目录，例如：
#        export ANDROID_NDK=$HOME/Android/Sdk/ndk/25.0.8775105
#   3) 运行：  bash tools/build_cubiomes_android.sh
#
# 想编 32 位(armeabi-v7a)旧手机？把下面 TARGET 改成 armv7a-linux-androideabi，
# API 与架构相应调整即可。
# ===================================================================
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
PKG="$HERE/cubiomespi"
SRC="$PKG/lib"            # 含 newlib.c
CB="$PKG/lib/cubiomes"    # 含 cubiomes 的 .c/.h 与 tables/

if [ -z "${ANDROID_NDK:-}" ]; then
  echo "错误：请先设置 ANDROID_NDK 环境变量，例如："
  echo '  export ANDROID_NDK=$HOME/Android/Sdk/ndk/25.0.8775105'
  exit 1
fi

API=21
TARGET=aarch64-linux-android
CLANG="$ANDROID_NDK/toolchains/llvm/prebuilt/linux-x86_64/bin/${TARGET}${API}-clang"
if [ ! -x "$CLANG" ]; then
  echo "错误：找不到 NDK clang：$CLANG"
  echo "请确认 ANDROID_NDK 指向正确的 NDK 根目录，且版本含 api-$API 工具链。"
  exit 1
fi

OUT="$PKG/lib_c.so"
echo "正在用 $CLANG 编译 lib_c.so (aarch64) ..."
"$CLANG" -shared -fPIC -I "$CB" \
  "$CB"/*.c "$SRC"/newlib.c -o "$OUT" -lm

if [ -f "$OUT" ]; then
  echo "成功：$OUT"
  echo "现在可以执行： buildozer android debug"
else
  echo "编译失败，请检查上面的报错。"
  exit 1
fi

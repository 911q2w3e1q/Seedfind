#!/usr/bin/env bash
# 一键出包：一条命令编译 cubiomes 原生库 + 打包，最终得到【单个】arm64-v8a 的 .apk
# 用法：  bash build.sh
set -e
cd "$(dirname "$0")"
# 若脚本不可执行，先补权限（pre_build_cmd 依赖它）
chmod +x tools/build_cubiomes_android.sh 2>/dev/null || true
buildozer android debug
echo ""
echo "完成。单个 apk 位于： bin/ 目录下（形如 Seedquery-1.0-arm64-v8a-debug.apk）"

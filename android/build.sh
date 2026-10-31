#!/usr/bin/env bash
# 一键出包：编译 cubiomes 原生库 + 打包，产出【单个】arm64-v8a 的 .apk
#
# 用法：
#   bash build.sh              # 完整构建
#
# 产物： bin/seedquery-1.0-arm64-v8a-debug.apk
set -e
cd "$(dirname "$0")"

# ---------- 1. JDK ----------
export JAVA_HOME="${JAVA_HOME:-/root/.sdkman/candidates/java/current}"
export PATH="$JAVA_HOME/bin:$PATH"

# ---------- 2. pip 网络策略 ----------
# p4a 在 hostpython 环境里执行 pip，且把 HOME 置为 /tmp（用户级 pip.conf 失效），
# 所以必须用环境变量显式指定可用的 PyPI 镜像；PEP 668 需要 break-system-packages。
export PIP_INDEX_URL="${PIP_INDEX_URL:-https://mirrors.tencent.com/pypi/simple/}"
export PIP_FIND_LINKS="${PIP_FIND_LINKS:-/tmp/wheels}"
export PIP_BREAK_SYSTEM_PACKAGES=1
export PIP_DEFAULT_TIMEOUT=30
export PIP_RETRIES=3
export PIP_DISABLE_PIP_VERSION_CHECK=1

# ---------- 3. 本地源码注入（绕过 github / PyPI 直连） ----------
# p4a 支持 P4A_<RECIPE>_DIR：设置后跳过该 recipe 的下载，直接使用本地源码目录。
# 重要：这些目录里的版本必须与 p4a 内置 recipe 的默认版本一致，否则 recipe 自带的
#       patch 会因上下文不匹配而失败（hunk failed）。
#   numpy 1.26.4 / matplotlib 3.10.7 / kivy 2.3.1 / pillow 11.3.0 / pyjnius 1.7.0 / kiwisolver 1.4.5
for pair in numpy:.numpy_src kivy:.kivy_src matplotlib:.mpl_src \
            pillow:.pillow_src pyjnius:.pyjnius_src kiwisolver:.kiwi_src; do
  name="${pair%%:*}"; dir="${pair##*:}"
  if [ -d "$dir" ]; then
    export "P4A_${name}_DIR=$PWD/$dir"
  else
    echo "[warn] 缺少本地源码目录 $dir —— 该 recipe 将尝试联网下载（可能因网络受限而失败）"
  fi
done

# ---------- 4. 构建 ----------
chmod +x tools/build_cubiomes_android.sh 2>/dev/null || true
yes | buildozer android debug

echo ""
echo "完成。单个 apk 位于： bin/ 目录下（seedquery-1.0-arm64-v8a-debug.apk）"

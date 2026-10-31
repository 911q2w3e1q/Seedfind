"""
本地 p4a recipe：把预编译的原生库 lib_c.so 打进 APK 的 lib/arm64-v8a/ 目录。

背景：Seedquery 通过 ctypes 加载 cubiomes 的原生库。若 .so 仅随 Python 包
（private.tar）解压到 App 私有目录，部分国产 ROM（如 MIUI）更严格的 SELinux
策略会拒绝从该目录 dlopen，导致启动即闪退。把 .so 放进 APK 的原生库目录后，
它由系统安装到 /data/app/<pkg>/lib/arm64/，与 libmain.so / libpython 同处，
MIUI 也允许加载。
"""
from os.path import join

import sh

from pythonforandroid.logger import shprint
from pythonforandroid.recipe import Recipe


class CubiomeslibRecipe(Recipe):
    version = "1.0"

    def download_if_necessary(self):
        # 预编译库，无需下载
        pass

    def should_build(self, arch):
        # 始终确保复制（轻量操作）
        return True

    def build_arch(self, arch):
        src = join(self.get_recipe_dir(), "lib_c.so")
        shprint(sh.cp, "-a", src, self.ctx.get_libs_dir(arch.arch))


recipe = CubiomeslibRecipe()

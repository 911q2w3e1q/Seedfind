[app]

# (str) 应用标题
title = Minecraft 种子查询器

# (str) 包名
package.name = seedquery

# (str) 包域名（反向，随便填但要唯一）
package.domain = com.seedquery

# (str) 源码目录（本安卓工程根目录）
source.dir = .

# (list) 需要打进 APK 的源码扩展名白名单
# 注意：cubiomes 的 C 源码(.c/.h)不打包，我们使用预编译好的 lib_c.so（见 tools/ 脚本）
source.include_exts = py,png,jpg,jpeg,kv,so,txt,md,json

# (list) 需要排除的目录
source.exclude_dirs = tests, bin, obj

# (list) 排除文件
source.exclude_patterns = *.pyc, __pycache__, .git*, build, dist

# (str) 主程序入口
source.main = main.py

# (list) 依赖：纯 Python 库直接写名字；cubiomespi 用本目录下的本地包（不写 PyPI 版）
requirements = python3==3.11.9, kivy==2.3.0, matplotlib==3.7.5, numpy==1.26.4, pillow==10.4.0, anvil-parser2, nbt

# (str) 应用版本
version = 1.0

# (str) 应用版本码
android.version_code = 1

# (str) 应用图标/启动图（可选，放 png 到本目录后改路径）
# presplash.filename = %(source.dir)s/presplash.png
# icon.filename = %(source.dir)s/icon.png

[buildozer]

# (int) 日志等级
log_level = 2

# (str) 目标平台
target = android

# (bool) 是否自动接受 SDK 许可
android.accept_sdk_license = True

# (str) Android API / 最低 API / NDK
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

# (str) 构建架构（手机几乎都是 arm64-v8a；如需旧机可加 armeabi-v7a）
# 只编一种架构 => 只产出一个 apk，不会出“两个”
android.archs = arm64-v8a

# (str) 打包前自动执行：用 NDK 把 cubiomes 编成手机的 lib_c.so
# 这样用户只需“一条命令” buildozer android debug，即可得到单个 apk，无需手动编 .so
android.pre_build_cmd = tools/build_cubiomes_android.sh

# (list) 权限：读取外部存档需要存储权限
android.permissions = READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE

# (bool) 关闭 AndroidX（kivy 2.x 一般保持默认）
android.enable_androidx = True

# (str) buildozer 缓存目录
build_dir = .buildozer

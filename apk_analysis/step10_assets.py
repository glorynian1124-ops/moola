# -*- coding: utf-8 -*-
"""Step 10: 把关键资源复制到 prototype/assets，并用有意义的名字命名"""
import os
import shutil
import logging
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass

from androguard.core.apk import APK

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prototype", "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

apk = APK(APK_PATH)

# 字体
font = apk.get_file("assets/DINCond-Bold.otf")
with open(os.path.join(ASSETS_DIR, "DINCond-Bold.otf"), "wb") as f:
    f.write(font)
print("字体已复制 -> assets/DINCond-Bold.otf")

# 关键图标映射：apk内混淆路径 -> 目标文件名
ICON_MAP = {
    "res/sk.png": "ic_book.png",        # 账本
    "res/0Z.png": "ic_back.png",        # 返回箭头
    "res/yU.png": "ic_dropdown.png",    # 下拉箭头
    "res/Rc.png": "ic_search.png",      # 搜索
    "res/yw.png": "ic_calendar.png",    # 日历
    "res/2b.png": "ic_add.png",         # 加号
    "res/Nn.png": "ic_chart.png",       # 图表
    "res/LO.png": "ic_forward.png",     # 前进箭头
    "res/aW.png": "ic_avatar.png",      # 头像
    "res/8e.png": "ic_empty.png",       # 空状态
    "res/B3.png": "ic_switch.png",      # 切换账本
    "res/qr.png": "ic_region.png",      # 区域
    "res/_F.png": "ic_photo.png",       # 图片
    "res/3G.png": "ic_delete.png",      # 删除
    "res/hA.xml": "drawable_roundrect.xml",  # 圆角背景
    "res/logo.png": "ic_logo.png",
}

for apk_path, target in ICON_MAP.items():
    try:
        data = apk.get_file(apk_path)
        # logo 的实际路径是 res/nm.png（前面解析过 logo=res/nm.png）
        out = os.path.join(ICONS_DIR if not target.endswith(".xml") else ASSETS_DIR, target)
        with open(out, "wb") as f:
            f.write(data)
        print(f"  {apk_path} -> assets/icons/{target} ({len(data)}B)")
    except Exception as e:
        print(f"  {apk_path} 失败: {e}")

# logo 特殊处理
try:
    data = apk.get_file("res/nm.png")
    with open(os.path.join(ICONS_DIR, "ic_logo.png"), "wb") as f:
        f.write(data)
    print("  res/nm.png -> assets/icons/ic_logo.png")
except Exception as e:
    print("logo:", e)

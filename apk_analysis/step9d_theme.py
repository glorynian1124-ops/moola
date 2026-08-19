# -*- coding: utf-8 -*-
"""Step 9d: 解析主题样式链，把 attr -> 颜色值解析到底"""
import os
import json
import logging
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass

from androguard.core.apk import APK
from androguard.core.axml import ARSCParser

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

apk = APK(APK_PATH)
arsc = ARSCParser(apk.get_file("resources.arsc"))
pkg = arsc.get_packages_names()[0]

resolver = ARSCParser.ResourceResolver(arsc, None)

# 解析主题 0x7F110007
print("=== 解析主题 0x7F110007 ===")
try:
    vals = resolver.resolve(0x7F110007)
    for cfg, v in vals:
        print(f"  {cfg.get_qualifier()}: {repr(v)[:300]}")
except Exception as e:
    print("err:", e)

# 解析 attr dark4clr 0x7F04010D 的完整链
print("\n=== 解析 attr dark4clr 0x7F04010D ===")
try:
    t, n, r = arsc.get_id(pkg, 0x7F04010D)
    print("meta:", t, n, hex(r))
    vals = resolver.resolve(0x7F04010D)
    for cfg, v in vals:
        print(f"  {cfg.get_qualifier()}: {repr(v)}")
except Exception as e:
    print("err:", e)

# 尝试直接查 style 条目
print("\n=== 主题相关 style 名称 ===")
for rid in [0x7F110007, 0x7F1100F2, 0x7F110001]:
    t, n, r = arsc.get_id(pkg, rid)
    print(f"  {hex(rid)} -> {t}:{n}")

# -*- coding: utf-8 -*-
"""Step 9c: 用 get_resolved_res_configs 解析布局中的所有引用，输出完整可读蓝本"""
import os
import re
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
BLUEPRINT_DIR = os.path.join(OUT_DIR, "blueprint_layouts")
os.makedirs(BLUEPRINT_DIR, exist_ok=True)

apk = APK(APK_PATH)
arsc = ARSCParser(apk.get_file("resources.arsc"))
pkg = arsc.get_packages_names()[0]

# 测试解析
def resolve_rid(rid_hex):
    """rid 十六进制字符串 -> 可读描述"""
    rid = int(rid_hex, 16)
    t, n, r = arsc.get_id(pkg, rid)
    try:
        vals = arsc.get_resolved_res_configs(rid)
        # 取默认 locale 的值
        val = None
        for cfg, v in vals:
            if cfg.get_qualifier() in ("", "DEFAULT") or v:
                val = v
                break
        if val is None and vals:
            val = vals[0][1]
        if val:
            return f"[{t}:{n}={val}]"
    except Exception as e:
        pass
    return f"[{t}:{n}]"

tests = [0x7F08006A, 0x7F0402DF, 0x7F04010D, 0x7F1100F2, 0x7F0800C2, 0x7F040277, 0x7F0400BA, 0x7F080077, 0x7F0800EF, 0x7F080087, 0x7F10001D]
for r in tests:
    print(f"{hex(r)} -> {resolve_rid(hex(r))}")

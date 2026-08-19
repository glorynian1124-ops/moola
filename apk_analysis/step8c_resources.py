# -*- coding: utf-8 -*-
"""Step 8c: 直接读取 ARSCParser.values 导出资源 + 建立 rid->名称 映射"""
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

res = {}
for locale, types in arsc.values[pkg].items():
    for tname, entries in types.items():
        if tname not in res:
            res[tname] = {}
        for e in entries:
            # e 结构: (name, value, ...)
            name = e[0]
            val = e[1] if len(e) > 1 else None
            res[tname][name] = str(val)

print("各类型资源数量:")
for t, v in sorted(res.items()):
    print(f"  {t}: {len(v)}")

# rid -> (type, name) 映射（public 类型里存有资源 ID）
rid_map = {}
public = res.get("public", {})
print("\npublic 样例:", list(public.items())[:5])

# 布局中的 @7F0901C1 等。用 get_id 建立映射
try:
    for tname in res:
        for name in res[tname]:
            # 尝试多个途径获取 rid
            pass
except Exception:
    pass

# 用 get_id(pkg, rid) 测试
sample_rids = [0x7F0901C1, 0x7F08006A, 0x7F0402DF, 0x7F04010D, 0x7F1100F2, 0x7F10001D, 0x7F0800C2]
print("\nrid 解析测试:")
for r in sample_rids:
    t, n, rid = arsc.get_id(pkg, r)
    print(f"  {hex(r)} -> type={t}, name={n}")

with open(os.path.join(OUT_DIR, "resources_full.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/resources_full.json")

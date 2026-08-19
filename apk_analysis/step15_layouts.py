# -*- coding: utf-8 -*-
"""Step 15: 导出 layout 资源名 -> 文件名映射（解决所有布局识别）"""
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
arsc.get_color_resources(pkg)

# layout 类型的 (name, rid) 从 public 表
layout_rids = {}
for loc, types in arsc.values[pkg].items():
    if "public" in types:
        for e in types["public"]:
            if len(e) >= 3 and e[0] == "layout":
                layout_rids[e[1]] = e[2]

print(f"layout 资源数: {len(layout_rids)}")

# rid -> 实际文件
mapping = {}
for name, rid in layout_rids.items():
    try:
        vals = arsc.get_resolved_res_configs(rid)
        for cfg, v in vals:
            if isinstance(v, str) and "res/" in v:
                mapping[name] = v
                break
    except Exception:
        pass

print(f"成功映射: {len(mapping)}\n")
for name, fn in sorted(mapping.items()):
    print(f"  {name:<48} {fn}")

with open(os.path.join(OUT_DIR, "layout_name_map.json"), "w", encoding="utf-8") as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/layout_name_map.json")

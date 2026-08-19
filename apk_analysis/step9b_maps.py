# -*- coding: utf-8 -*-
"""Step 9b: 从 values 结构导出 drawable 映射和 attr/style，并解析主题中的颜色"""
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
arsc.get_color_resources(pkg)  # 触发 _analyse

drawable_map = {}
attr_entries = {}
style_entries = {}
id_entries = {}

for loc, types in arsc.values[pkg].items():
    for tname in ("drawable", "attr", "style", "id"):
        if tname in types:
            for e in types[tname]:
                name = e[0]
                rest = list(e[1:]) if len(e) > 1 else []
                if tname == "drawable":
                    drawable_map[name] = rest
                elif tname == "attr":
                    attr_entries[name] = rest
                elif tname == "style":
                    style_entries[name] = rest
                elif tname == "id":
                    id_entries[name] = rest

print(f"drawable_map: {len(drawable_map)}")
print(f"attr: {len(attr_entries)}")
print(f"style: {len(style_entries)}")
print(f"id: {len(id_entries)}")

print("\n=== drawable 样例 ===")
for k, v in list(drawable_map.items())[:20]:
    print(f"  {k} -> {v}")

print("\n=== attr 样例 ===")
for k, v in list(attr_entries.items())[:10]:
    print(f"  {k} -> {v}")

print("\n=== style 样例（找主题） ===")
for k, v in list(style_entries.items())[:15]:
    print(f"  {k} -> {v}")

out = {
    "drawable_map": {k: v for k, v in drawable_map.items()},
    "attrs": {k: v for k, v in attr_entries.items()},
    "styles": {k: v for k, v in style_entries.items()},
}
with open(os.path.join(OUT_DIR, "resource_maps.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)
print("\n已保存 -> output/resource_maps.json")

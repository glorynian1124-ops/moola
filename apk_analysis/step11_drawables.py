# -*- coding: utf-8 -*-
"""Step 11: 导出全部 drawable 资源名 -> rid -> 文件路径"""
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
arsc.get_color_resources(pkg)  # trigger analyse

# public 条目：(type, name, rid)
drawables = []
for locale, types in arsc.values[pkg].items():
    if "public" not in types:
        continue
    for e in types["public"]:
        if len(e) >= 3 and e[0] == "drawable":
            drawables.append({"name": e[1], "rid": e[2]})

print(f"drawable 资源总数: {len(drawables)}")

# 解析每个 drawable 的实际文件路径
result = []
for d in drawables:
    try:
        vals = arsc.get_resolved_res_configs(d["rid"])
        path = None
        for cfg, v in vals:
            if isinstance(v, str) and "res/" in v:
                path = v
                break
        result.append({"name": d["name"], "rid": hex(d["rid"]), "file": path})
    except Exception:
        result.append({"name": d["name"], "rid": hex(d["rid"]), "file": None})

resolved = [r for r in result if r["file"]]
print(f"成功解析文件路径: {len(resolved)}")

# 按名称打印（找分类/菜单图标）
print("\n=== 全部 drawable 名称 ===")
for r in resolved:
    print(f"  {r['name']:<45} {r['file']}")

with open(os.path.join(OUT_DIR, "drawable_map_full.json"), "w", encoding="utf-8") as f:
    json.dump(resolved, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/drawable_map_full.json")

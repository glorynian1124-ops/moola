# -*- coding: utf-8 -*-
"""Step 14: 导出 array/plurals/integer/bool 资源 + 查找 widget 布局"""
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

out = {}
for tname in ("array", "plurals", "integer", "bool"):
    vals = {}
    try:
        for loc, types in arsc.values[pkg].items():
            if tname in types:
                for e in types[tname]:
                    name = e[0]
                    rest = [str(x) for x in e[1:]]
                    vals.setdefault(name, rest)
    except Exception as ex:
        print(tname, "err", ex)
    out[tname] = vals
    print(f"\n=== {tname} ({len(vals)} 个) ===")
    for k, v in list(vals.items()):
        print(f"  {k} = {v}")

# 找 widget 布局：搜所有 xml 里的 appwidget
print("\n=== 搜索 widget 布局 ===")
for fn in apk.get_files():
    if fn.endswith(".xml") and "res/" in fn:
        try:
            data = apk.get_file(fn)
            if b"appwidget" in data.lower() or b"widget" in fn.lower():
                from androguard.core.axml import AXMLPrinter
                try:
                    xml = AXMLPrinter(data).get_xml().decode("utf-8", errors="ignore")
                    print(f"--- {fn} ---")
                    print(xml[:800])
                except Exception:
                    print(fn, "(解码失败)")
        except Exception:
            pass

with open(os.path.join(OUT_DIR, "resources_extra.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/resources_extra.json")

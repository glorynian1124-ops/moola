# -*- coding: utf-8 -*-
"""Step 8: 探索 ARSCParser API，导出颜色/字符串/尺寸资源映射"""
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
raw = apk.get_file("resources.arsc")

arsc = ARSCParser(raw)
print("packages:", arsc.get_packages_names())

pkg = arsc.get_packages_names()[0]
print("locales:", arsc.get_locales(pkg)[:5])
locale = arsc.get_locales(pkg)[0]

types = arsc.get_types(pkg, locale)
print("types (%d):" % len(types))
for t in types:
    print("  ", t)

# 尝试获取一个类型下的资源
try:
    first_type = types[0]
    configs = arsc.get_res_configs(pkg, locale)
    print("res_configs count:", len(configs))
except Exception as e:
    print("get_res_configs err:", e)

# 导出颜色和字符串
out = {"colors": {}, "strings": {}, "dimens": {}}

def dump_type(type_name, out_key):
    try:
        entries = arsc.get_resource_names(pkg, locale, type_name)
        print(f"type {type_name}: {len(entries)} 个资源")
        for name in entries:
            try:
                val = arsc.get_resource(pkg, type_name, name, locale)
                out[out_key][name] = str(val)
            except Exception:
                pass
    except Exception as e:
        print(f"dump {type_name} 失败:", e)

for tn in ["color", "string", "dimen"]:
    dump_type(tn, {"color": "colors", "string": "strings", "dimen": "dimens"}[tn])

print("\n颜色示例:", list(out["colors"].items())[:5])
print("字符串示例:", list(out["strings"].items())[:5])

with open(os.path.join(OUT_DIR, "resources_dump.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/resources_dump.json")

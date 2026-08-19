# -*- coding: utf-8 -*-
"""Step 8b: 用正确 API 导出颜色/字符串/尺寸，并建立 资源ID -> 名称 映射"""
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

def to_dict(gen_or_dict):
    try:
        return dict(gen_or_dict)
    except Exception:
        return dict(list(gen_or_dict))

colors = to_dict(arsc.get_color_resources(pkg))
strings = to_dict(arsc.get_string_resources(pkg))
dimens = to_dict(arsc.get_dimen_resources(pkg))
bools = to_dict(arsc.get_bool_resources(pkg))

print(f"颜色: {len(colors)}, 字符串: {len(strings)}, 尺寸: {len(dimens)}, 布尔: {len(bools)}")

# 建立 name -> rid 映射（用于布局中的 @7Fxxxxxx 引用）
rid_by_name = {}
type_ids = {}
try:
    for tname in arsc.get_types(pkg, arsc.get_locales(pkg)[0]):
        try:
            items = arsc.get_res_configs(pkg, tname)
            for it in list(items):
                pass
        except Exception:
            pass
except Exception as e:
    print("types scan:", e)

# 尝试 get_id(package, type, name)
sample_names = list(colors.keys())[:3]
for n in sample_names:
    try:
        rid = arsc.get_id(pkg, "color", n)
        print("rid of", n, "=", hex(rid))
        print("  xml name:", arsc.get_resource_xml_name(rid))
    except Exception as e:
        print("get_id err:", e)

out = {
    "colors": colors,
    "strings": strings,
    "dimens": dimens,
    "bools": bools,
}
with open(os.path.join(OUT_DIR, "resources_dump.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/resources_dump.json")

# 打印关键颜色
print("\n=== 颜色样例（前 40） ===")
for k, v in list(colors.items())[:40]:
    print(f"  {k} = {v}")

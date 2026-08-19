# -*- coding: utf-8 -*-
"""Step 8d: 解析 get_*_resources 返回的 XML，导出资源并建立 rid 映射"""
import os
import json
import re
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

def parse_res_xml(xml_bytes, tag):
    """把 <color name=x>val</color> 形式的 XML 解析成 dict"""
    text = xml_bytes.decode("utf-8", errors="ignore")
    out = {}
    for m in re.finditer(r'<%s\s+name="([^"]+)"[^>]*>([^<]*)</%s>' % (tag, tag), text):
        out[m.group(1)] = m.group(2)
    return out

colors = parse_res_xml(arsc.get_color_resources(pkg), "color")
strings = parse_res_xml(arsc.get_string_resources(pkg), "string")
dimens = parse_res_xml(arsc.get_dimen_resources(pkg), "dimen")
bools = {}
try:
    bools = parse_res_xml(arsc.get_bool_resources(pkg), "bool")
except Exception as e:
    print("bool 资源解析跳过:", e)
try:
    integers = parse_res_xml(arsc.get_integer_resources(pkg), "integer")
except Exception:
    integers = {}
try:
    ids = parse_res_xml(arsc.get_id_resources(pkg), "item")
except Exception:
    ids = {}

print(f"color: {len(colors)}, string: {len(strings)}, dimen: {len(dimens)}, bool: {len(bools)}, integer: {len(integers)}, id: {len(ids)}")

# rid -> (type,name) 映射：get_id(pkg, rid)
def rid_meta(rid):
    try:
        t, n, r = arsc.get_id(pkg, rid)
        return {"type": t, "name": n, "rid": hex(r) if r else None}
    except Exception:
        return None

# 测试几个布局里的引用
tests = [0x7F0901C1, 0x7F08006A, 0x7F0402DF, 0x7F04010D, 0x7F1100F2, 0x7F10001D, 0x7F0800C2, 0x7F040277, 0x7F0400BA, 0x7F04010E, 0x7F040171, 0x7F0401F0, 0x7F1000CC, 0x7F1000CE, 0x7F100097, 0x7F100021, 0x7F1000BD, 0x7F130001]
print("\nrid 解析测试:")
for r in tests:
    m = rid_meta(r)
    print(f"  {hex(r)} -> {m}")

out = {
    "colors": colors, "strings": strings, "dimens": dimens,
    "bools": bools, "integers": integers, "ids": ids,
}
with open(os.path.join(OUT_DIR, "resources_full.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/resources_full.json")

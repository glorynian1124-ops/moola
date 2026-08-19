# -*- coding: utf-8 -*-
"""Step 9: 建立完整资源解析器，把布局中的 @7Fxxxxxx 引用替换为可读名称/值，输出复刻蓝本"""
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

# ---- 1. 资源值表 ----
def parse_res_xml(xml_bytes, tag):
    text = xml_bytes.decode("utf-8", errors="ignore")
    out = {}
    for m in re.finditer(r'<%s\s+name="([^"]+)"[^>]*>([^<]*)</%s>' % (tag, tag), text):
        out[m.group(1)] = m.group(2)
    return out

colors = parse_res_xml(arsc.get_color_resources(pkg), "color")
strings = parse_res_xml(arsc.get_string_resources(pkg), "string")
dimens = parse_res_xml(arsc.get_dimen_resources(pkg), "dimen")

# ---- 2. drawable name -> 实际文件路径（res 下混淆名） ----
drawable_map = {}
try:
    for locale, types in arsc.values[pkg].items():
        if "drawable" in types:
            for e in types["drawable"]:
                name, val = e[0], e[1] if len(e) > 1 else None
                drawable_map[name] = val
except Exception as ex:
    print("drawable 遍历失败:", ex)

# ---- 3. 主题 attr -> 值 映射（?7F04xxxx 引用需要解析到主题实际值） ----
# style/attr 较复杂，先直接按 name 找 colors/drawable 中的同名项

# ---- 4. rid -> 描述 解析器 ----
def attr_color(attr_name):
    """attr 名 -> 实际颜色值"""
    if attr_name in colors:
        return colors[attr_name]
    cands = []
    # dark4clr -> dark4txtclr / gray8clr -> gray8txtclr / lightfclr -> lightftxtclr
    if attr_name.endswith("clr"):
        cands.append(attr_name[:-3] + "txtclr")
    if attr_name == "sepcolor":
        cands.append("sepclr")
    if attr_name == "colorPrimaryDark":
        cands.append("colorPrimaryDark")
    for c in cands:
        if c in colors:
            return colors[c]
    return None

def rid_desc(rid_hex):
    try:
        rid = int(rid_hex, 16)
    except Exception:
        return rid_hex
    t, n, r = arsc.get_id(pkg, rid)
    if not t:
        return rid_hex
    val = None
    if t == "color":
        val = colors.get(n)
    elif t == "string":
        val = strings.get(n)
    elif t == "dimen":
        val = dimens.get(n)
    elif t == "drawable":
        val = drawable_map.get(n)
        if not val:
            try:
                vals = arsc.get_resolved_res_configs(rid)
                for cfg, v in vals:
                    if isinstance(v, str) and "res/" in v:
                        val = v
                        break
            except Exception:
                pass
    elif t == "attr":
        val = attr_color(n)
    elif t == "id":
        return f"@id/{n}" if n else rid_hex
    elif t == "style":
        val = None
    if val:
        return f"[{t}:{n}={val}]"
    return f"[{t}:{n}]"

def beautify(xml_text):
    # @7Fxxxxxx / ?7Fxxxxxx -> [type:name=value]
    out = re.sub(r"[@?](7[fF][0-9a-fA-F]{6})", lambda m: rid_desc(m.group(1)), xml_text)
    # 数值美化：-1/-2 尺寸
    out = out.replace('android:layout_width="-1"', 'android:layout_width="match_parent"')
    out = out.replace('android:layout_height="-1"', 'android:layout_height="match_parent"')
    out = out.replace('android:layout_width="-2"', 'android:layout_width="wrap_content"')
    out = out.replace('android:layout_height="-2"', 'android:layout_height="wrap_content"')
    return out

# ---- 5. 处理所有 UI 布局 ----
with open(os.path.join(OUT_DIR, "layout_classification.json"), "r", encoding="utf-8") as f:
    cls = json.load(f)

ui_files = [item["file"] for item in cls["ui_layouts"] if item["file"] != "AndroidManifest.xml.xml"]

report_lines = []
for fn in ui_files:
    path = os.path.join(OUT_DIR, "layouts", fn)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    pretty = beautify(content)
    out_path = os.path.join(BLUEPRINT_DIR, fn)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(pretty)
    report_lines.append(f"{fn}: {len(pretty)} bytes")

# ---- 6. 输出关键资源摘要 ----
summary = {
    "drawable_map": drawable_map,
    "key_colors": {k: colors.get(k) for k in
                   ["colorPrimary", "colorPrimaryDark", "colorAccent", "dark4clr", "dark5clr", "dark6clr",
                    "grayaclr", "lightfclr", "sepcolor", "primarydark", "primarylight", "expenseclr", "incomeclr"] if k in colors},
    "all_colors": colors,
    "all_dimens_sample": dict(list(dimens.items())[:80]),
}
with open(os.path.join(OUT_DIR, "resource_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"已生成 {len(report_lines)} 个复刻蓝本布局 -> blueprint_layouts/")
print(f"\n=== drawable 文件映射 ({len(drawable_map)} 个) 样例 ===")
for k, v in list(drawable_map.items())[:30]:
    print(f"  {k} -> {v}")
print("\n=== 关键颜色 ===")
for k, v in summary["key_colors"].items():
    print(f"  {k} = {v}")

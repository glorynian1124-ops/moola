# -*- coding: utf-8 -*-
"""Step 17: 壳 dex 字符串全提取 + Manifest 剩余组件 + 应用自有 drawable/style"""
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

apk = APK(APK_PATH)
arsc = ARSCParser(apk.get_file("resources.arsc"))
pkg = arsc.get_packages_names()[0]
arsc.get_color_resources(pkg)

# ---- 1. 壳 dex 字符串 ----
raw = apk.get_file("classes.dex")
strs = re.findall(rb"[\x20-\x7e]{4,}", raw)
texts = [s.decode(errors="ignore") for s in strs]
# 过滤纯数字/十六进制
interesting = []
for t in texts:
    if re.fullmatch(r"[0-9a-fA-FxX\s]+", t):
        continue
    interesting.append(t)

print("=== 壳 dex 字符串（过滤后 %d 条）===" % len(interesting))
for t in interesting[:150]:
    print("  ", t)

with open(os.path.join(OUT_DIR, "shell_dex_strings.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(interesting))

# ---- 2. Manifest 剩余组件 ----
try:
    from androguard.core.axml import AXMLPrinter
    xml = AXMLPrinter(apk.get_file("AndroidManifest.xml")).get_xml().decode("utf-8", errors="ignore")
    print("\n=== Manifest meta-data / provider / receiver / service ===")
    for line in xml.split("\n"):
        if re.search(r"<(meta-data|provider|receiver|service|uses-library)", line):
            print("  ", line.strip()[:160])
except Exception as e:
    print("manifest err:", e)

# ---- 3. 应用自有 drawable（非第三方） ----
print("\n=== 应用自有 drawable 列表（非 abc/mtrl/design/notification） ===")
third = ("abc_", "mtrl_", "design_", "notification_", "avd_", "btn_", "cv_", "select_", "test_", "tooltip_", "$")
with open(os.path.join(OUT_DIR, "drawable_map_full.json"), "r", encoding="utf-8") as f:
    drawables = json.load(f)
own = [d for d in drawables if d["name"] and not any(d["name"].startswith(t) for t in third)]
for d in own:
    print(f"  {d['name']:<30} {d['file']}")

with open(os.path.join(OUT_DIR, "own_drawables.json"), "w", encoding="utf-8") as f:
    json.dump(own, f, ensure_ascii=False, indent=2)

# ---- 4. style 资源名 ----
print("\n=== style 资源 ===")
styles = []
for loc, types in arsc.values[pkg].items():
    if "public" in types:
        for e in types["public"]:
            if len(e) >= 3 and e[0] == "style":
                styles.append(e[1])
for s in sorted(set(styles)):
    print("  ", s)

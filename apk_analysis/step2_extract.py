# -*- coding: utf-8 -*-
"""Step 2: 解码 AndroidManifest、提取图片资源、解码全部布局 XML"""
import os
import logging
import traceback

# 关闭 androguard 的 DEBUG 日志
logging.disable(logging.CRITICAL)

from androguard.core.apk import APK
from androguard.core.axml import AXMLPrinter

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
IMG_DIR = os.path.join(OUT_DIR, "images")
LAYOUT_DIR = os.path.join(OUT_DIR, "layouts")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(LAYOUT_DIR, exist_ok=True)

apk = APK(APK_PATH)

# 1) AndroidManifest
try:
    xml = apk.get_android_manifest_axml().get_xml()
    with open(os.path.join(OUT_DIR, "AndroidManifest.xml"), "wb") as f:
        f.write(xml.toprettyxml(indent="  ", encoding="utf-8"))
    print("AndroidManifest.xml 已保存")
except Exception as e:
    print("Manifest 解码失败:", e)
    traceback.print_exc()

# 2) 提取图片
png_files = [f for f in apk.get_files() if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))]
ok = 0
fail = 0
for fn in png_files:
    try:
        data = apk.get_file(fn)
        safe = fn.replace("/", "_").replace("\\", "_")
        with open(os.path.join(IMG_DIR, safe), "wb") as f:
            f.write(data)
        ok += 1
    except Exception:
        fail += 1
print(f"图片提取完成: 成功 {ok}, 失败 {fail} (共 {len(png_files)})")

# 3) 解码布局/资源 XML
xml_files = [f for f in apk.get_files() if f.lower().endswith(".xml")]
ok = 0
fail = 0
failed_names = []
for fn in xml_files:
    try:
        data = apk.get_file(fn)
        printer = AXMLPrinter(data)
        out = printer.get_xml()
        safe = fn.replace("/", "_").replace("\\", "_")
        with open(os.path.join(LAYOUT_DIR, safe + ".xml"), "wb") as f:
            f.write(out)
        ok += 1
    except Exception:
        fail += 1
        failed_names.append(fn)
print(f"XML 解码完成: 成功 {ok}, 失败 {fail} (共 {len(xml_files)})")
if failed_names:
    print("失败文件:")
    for n in failed_names[:30]:
        print("   ", n)

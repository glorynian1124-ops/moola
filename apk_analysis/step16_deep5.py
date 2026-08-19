# -*- coding: utf-8 -*-
"""Step 16: 解码所有尚未细读的布局（activity_setmobile 等）"""
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
from androguard.core.axml import AXMLPrinter

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

apk = APK(APK_PATH)

TARGETS = [
    "activity_setmobile", "activity_setpwd", "activity_wxpayresult", "activity_wxentry",
    "item_purchase", "item_upgrade", "item_statistic", "item_balance", "item_dateitem",
    "item_pic", "item_theme", "item_selbook", "item_importtype", "item_app",
    "item_managetype", "item_managebooktype", "item_typeimg", "item_account2",
    "dialog_downloading", "dialog_loading", "dialog_message", "dialog_setmainbook",
    "dialog_widget", "dialog_choosepic", "custom_dialog",
    "cv_layout_calendar_view", "cv_week_bar",
]

# 从映射文件找文件名
with open(os.path.join(OUT_DIR, "layout_name_map.json"), "r", encoding="utf-8") as f:
    name_map = json.load(f)

out = {}
for name in TARGETS:
    fn = name_map.get(name)
    if not fn:
        print(f"[缺失] {name}")
        continue
    try:
        xml = AXMLPrinter(apk.get_file(fn)).get_xml().decode("utf-8", errors="ignore")
        out[name] = {"file": fn, "xml": xml}
        # 摘要
        texts = re.findall(r'android:text="([^"]+)"', xml)
        texts = [t for t in texts if not t.startswith("@")][:12]
        ids = re.findall(r'android:id="@id/(\w+)"', xml)
        customs = re.findall(r'<(com\.[\w\.]+|com\.github\.[\w\.]+)', xml)
        print(f"\n{'='*20} {name} ({fn}) {'='*20}")
        print("  文本:", " | ".join(texts) if texts else "(无)")
        print("  ids:", ", ".join(dict.fromkeys(ids))[:120] if ids else "(无)")
        if customs:
            print("  组件:", ", ".join(dict.fromkeys(customs))[:120])
    except Exception as e:
        print(f"[错误] {name}: {e}")

with open(os.path.join(OUT_DIR, "deep_layouts_5.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/deep_layouts_5.json")

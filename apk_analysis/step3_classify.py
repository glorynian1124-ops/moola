# -*- coding: utf-8 -*-
"""Step 3: 分析布局 XML，区分界面布局 / drawable / values，并输出界面布局清单"""
import os
import re
import json

LAYOUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "layouts")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

WIDGET_TAGS = re.compile(r"<(android\.widget\.|android\.view\.|androidx\.|com\.)([\w\.]+)")
VIEW_ROOT = re.compile(r"<(\w[\w\.]*)")

ui_layouts = []      # 含控件的布局（界面）
drawables = []       # selector / shape / layer-list 等
values_xml = []      # strings / colors / dimens 等
others = []

for fn in os.listdir(LAYOUT_DIR):
    path = os.path.join(LAYOUT_DIR, fn)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(20000)
    except Exception:
        continue
    if "android.widget" in content or "android.view" in content or "<fragment" in content or "androidx" in content:
        ui_layouts.append((fn, os.path.getsize(path)))
    elif re.search(r"<(selector|shape|layer-list|ripple|vector|inset|clip|rotate|scale|item)\b", content):
        drawables.append((fn, os.path.getsize(path)))
    elif re.search(r"<resources>|<string\b|<color\b|<dimen\b|<style\b|<array\b|<plurals\b", content):
        values_xml.append((fn, os.path.getsize(path)))
    else:
        others.append((fn, os.path.getsize(path)))

ui_layouts.sort(key=lambda x: -x[1])

print(f"界面布局(UI): {len(ui_layouts)} 个")
print(f"drawable: {len(drawables)} 个")
print(f"values资源: {len(values_xml)} 个")
print(f"其他: {len(others)} 个")
print("\n=== 最大的 20 个界面布局 ===")
for fn, size in ui_layouts[:20]:
    print(f"  {size:>8}  {fn}")

# 保存分类清单
with open(os.path.join(OUT_DIR, "layout_classification.json"), "w", encoding="utf-8") as f:
    json.dump({
        "ui_layouts": [{"file": a, "size": b} for a, b in ui_layouts],
        "drawables": [a for a, _ in drawables],
        "values_xml": [a for a, _ in values_xml],
        "others": [a for a, _ in others],
    }, f, ensure_ascii=False, indent=2)

print("\n分类清单已保存 -> output/layout_classification.json")

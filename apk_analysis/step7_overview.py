# -*- coding: utf-8 -*-
"""Step 7: 生成布局概览 —— 提取每个 UI 布局的根视图、控件统计和文本内容"""
import os
import re
import json

LAYOUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "layouts")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

def summarize(fn):
    path = os.path.join(LAYOUT_DIR, fn)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # 根元素
    m = re.search(r"<(/?)(\w[\w\.]*)[ >]", content)
    root = m.group(2) if m else "?"
    # 所有元素
    tags = re.findall(r"<(\w[\w\.]*)[\s>]", content)
    # 控件统计
    from collections import Counter
    cnt = Counter(tags)
    controls = {k: v for k, v in cnt.most_common(12) if not k.startswith("Linear")}
    # 文本内容
    texts = re.findall(r'android:text="([^"]+)"', content)
    hint = re.findall(r'android:hint="([^"]+)"', content)
    return {
        "file": fn,
        "size": os.path.getsize(path),
        "root": root,
        "controls": controls,
        "texts": texts[:15],
        "hints": hint[:5],
    }

# 从分类清单读取 UI 布局
with open(os.path.join(OUT_DIR, "layout_classification.json"), "r", encoding="utf-8") as f:
    cls = json.load(f)

summaries = []
for item in cls["ui_layouts"]:
    fn = item["file"]
    if fn == "AndroidManifest.xml.xml":
        continue
    try:
        summaries.append(summarize(fn))
    except Exception as e:
        summaries.append({"file": fn, "error": str(e)})

# 打印
for s in summaries:
    print("=" * 70)
    print(f"{s['file']}  ({s['size']}B)  根元素: {s.get('root')}")
    if "controls" in s:
        ctrl = ", ".join(f"{k}:{v}" for k, v in s["controls"].items() if k != s.get("root"))
        if ctrl:
            print("  控件:", ctrl[:200])
        if s.get("texts"):
            print("  文本:", " | ".join(s["texts"])[:250])
        if s.get("hints"):
            print("  提示:", " | ".join(s["hints"])[:150])
    else:
        print("  错误:", s.get("error"))

with open(os.path.join(OUT_DIR, "layout_overview.json"), "w", encoding="utf-8") as f:
    json.dump(summaries, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/layout_overview.json")

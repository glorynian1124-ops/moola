# -*- coding: utf-8 -*-
"""Step 13: 深度分析所有被遗漏的布局（others 分类）+ id 命名提取交互线索"""
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

LAYOUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "layouts")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# 所有布局文件
results = []
for fn in sorted(os.listdir(LAYOUT_DIR)):
    path = os.path.join(LAYOUT_DIR, fn)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # 提取所有 id
    ids = re.findall(r'android:id="@id/(\w+)"', content)
    # 提取自定义组件
    customs = re.findall(r'<(com\.yhqx\.[\w\.]+)', content)
    # 文本
    texts = re.findall(r'android:text="([^"]+)"', content)[:8]
    # 根元素
    m = re.search(r"<(\w[\w\.]*)[\s/>]", content)
    root = m.group(1) if m else "?"
    # 大小
    size = os.path.getsize(path)
    # 是否属于已知 UI 布局（从分类清单）
    results.append({
        "file": fn, "size": size, "root": root,
        "ids": list(dict.fromkeys(ids)),
        "customs": list(dict.fromkeys(customs)),
        "texts": texts,
    })

# 读取已知 UI 清单
with open(os.path.join(OUT_DIR, "layout_classification.json"), "r", encoding="utf-8") as f:
    cls = json.load(f)
known_ui = set(item["file"] for item in cls["ui_layouts"])
known_drawable = set(cls["drawables"])

# 输出：未分类布局中含 id 的（可能是遗漏的界面组件）
print("=" * 70)
print("未分类布局中含 @id 的（可能是遗漏的页面/组件）:")
print("=" * 70)
for r in results:
    if r["file"] in known_ui or r["file"] in known_drawable:
        continue
    if r["ids"] or r["customs"]:
        print(f"\n{r['file']} ({r['size']}B) 根={r['root']}")
        if r["customs"]:
            print("  自定义组件:", ", ".join(r["customs"]))
        if r["ids"]:
            print("  ids:", ", ".join(r["ids"][:20]))
        if r["texts"]:
            print("  文本:", " | ".join(t for t in r["texts"] if not t.startswith("@"))[:150])

# 自定义组件全量统计
print("\n" + "=" * 70)
print("全部自定义组件 (com.yhqx) 统计:")
custom_set = {}
for r in results:
    for c in r["customs"]:
        custom_set[c] = custom_set.get(c, 0) + 1
for c, n in sorted(custom_set.items()):
    print(f"  {c}: {n} 处")

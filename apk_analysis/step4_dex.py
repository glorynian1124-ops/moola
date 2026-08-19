# -*- coding: utf-8 -*-
"""Step 4: 分析 classes.dex —— 列出类，尝试反编译核心 Activity"""
import os
import logging
logging.disable(logging.CRITICAL)

from androguard.core.apk import APK
from androguard.core.dex import DEX

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

apk = APK(APK_PATH)

# 获取 classes.dex 原始字节
raw = apk.get_file("classes.dex")
print(f"classes.dex 大小: {len(raw)} bytes")

try:
    d = DEX(raw)
    classes = d.get_classes()
    print(f"类数量: {len(classes)}")

    # 统计包分布
    from collections import Counter
    pkgs = Counter()
    app_classes = []
    for c in classes:
        name = c.get_name()
        pkg = ".".join(name.split("/")[0].split(".")[:2]) if "/" in name else name
        pkgs[pkg] += 1
        if "yhqx" in name.lower():
            app_classes.append(name)

    print("\n=== 类所在的包分布 (Top 15) ===")
    for pkg, cnt in pkgs.most_common(15):
        print(f"  {cnt:>5}  {pkg}")

    print(f"\n=== 应用自身类 (com.yhqx) 数量: {len(app_classes)} ===")
    # 打印所有 com.yhqx 的类（去重后）
    seen = set()
    for c in app_classes:
        if c not in seen:
            seen.add(c)
            print("  ", c)

    # 保存类清单
    with open(os.path.join(OUT_DIR, "dex_classes.txt"), "w", encoding="utf-8") as f:
        for c in classes:
            f.write(c.get_name() + "\n")

    # 检查 MainActivity 是否存在
    main_activities = [c for c in classes if "MainActivity" in c.get_name()]
    print(f"\n=== 含 MainActivity 的类: {len(main_activities)} ===")
    for c in main_activities:
        print("  ", c.get_name())
except Exception as e:
    print("DEX 解析失败:", type(e).__name__, e)

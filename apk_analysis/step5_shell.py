# -*- coding: utf-8 -*-
"""Step 5: 检查 assets 与 dex 文件头，识别加固特征与加密 dex 位置"""
import os
import logging
logging.disable(logging.CRITICAL)
from androguard.core.apk import APK

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

apk = APK(APK_PATH)

def hexdump(data, n=16):
    return data[:n].hex(" ")

# 检查所有 assets 文件和 dex
targets = ["classes.dex", "AndroidManifest.xml", "resources.arsc"]
targets += [f for f in apk.get_files() if f.startswith("assets/")]

print(f"{'文件':<45} {'大小':>10}  文件头")
print("-" * 80)
for fn in targets:
    try:
        data = apk.get_file(fn)
        print(f"{fn:<45} {len(data):>10}  {hexdump(data)}")
    except Exception as e:
        print(f"{fn:<45} 读取失败: {e}")

# 用熵/关键词进一步判断哪些文件可能是加密 dex 或 so
print("\n=== 在可读字符串中查找加固厂商关键词 ===")
import re
keywords = ["bangcle", "jiagu", "ijiami", "qihoo", "360", "tengxun", "seclite", "libjiagu", "secneo", "shell", "dex", "unpack", "protect"]
for fn in targets:
    try:
        data = apk.get_file(fn)
    except Exception:
        continue
    # 找 ASCII 字符串
    strs = re.findall(rb"[\x20-\x7e]{5,}", data)
    hits = [s.decode(errors="ignore") for s in strs if any(k.lower().encode() in s.lower() for k in keywords)]
    if hits:
        print(f"\n--- {fn} 关键词命中 ---")
        for h in hits[:10]:
            print("   ", h)

# -*- coding: utf-8 -*-
"""Step 5b: 检查 assets 与 dex 文件头，识别加固特征（结果写入文件）"""
import os
import re
import json
import logging

# 彻底禁用 androguard 日志（含 loguru）
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass

from androguard.core.apk import APK

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

apk = APK(APK_PATH)

def hexdump(data, n=16):
    return data[:n].hex(" ")

targets = ["classes.dex", "AndroidManifest.xml", "resources.arsc"]
targets += [f for f in apk.get_files() if f.startswith("assets/")]

result = {"file_headers": [], "keywords": {}}
for fn in targets:
    try:
        data = apk.get_file(fn)
        result["file_headers"].append({"file": fn, "size": len(data), "header": hexdump(data)})
    except Exception as e:
        result["file_headers"].append({"file": fn, "error": str(e)})

keywords = ["bangcle", "jiagu", "ijiami", "qihoo", "360", "tencent", "tengxun",
            "seclite", "libjiagu", "secneo", "unpack", "protect", "dex", "shell",
            "netease", "navicat", "yunzhong", "dptshell", "baidu"]
for fn in targets:
    try:
        data = apk.get_file(fn)
    except Exception:
        continue
    strs = re.findall(rb"[\x20-\x7e]{4,}", data)
    hits = []
    for s in strs:
        low = s.lower()
        if any(k.encode() in low for k in keywords):
            hits.append(s.decode(errors="ignore"))
    if hits:
        result["keywords"][fn] = hits[:15]

# 判断哪些 assets 文件可能是加密 dex（检查常见加密特征或接近 dex 的大小）
print(json.dumps(result, ensure_ascii=False, indent=2))

with open(os.path.join(OUT_DIR, "shell_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\n已保存 -> output/shell_analysis.json")

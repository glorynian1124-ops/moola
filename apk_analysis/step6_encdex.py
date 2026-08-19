# -*- coding: utf-8 -*-
"""Step 6: 分析加密 dex (assets/0OO00l111l1l)，尝试找 dex 头特征或简单解密"""
import os
import json
import logging
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
data = apk.get_file("assets/0OO00l111l1l")
print(f"加密文件大小: {len(data)}")

result = {"size": len(data), "searches": {}}

# 1) 搜索 dex 魔数
dex_magic = b"dex\n035\x00"
idx = data.find(dex_magic)
result["searches"]["dex_magic_plain"] = idx
print(f"明文 dex 头位置: {idx}")

# 2) 搜索 0x78 0x56 0x34 0x12 (dex 035 的 endian tag 后) 或 'dex\n037'
for ver in (b"dex\n036\x00", b"dex\n037\x00", b"dex\n038\x00", b"dex\n039\x00"):
    i = data.find(ver)
    if i != -1:
        result["searches"][ver.decode()] = i
        print(f"找到 {ver.decode()} @ {i}")

# 3) 简单的单字节 XOR 探测：尝试所有 256 个 XOR key，看哪个能在开头附近产生 'dex'
found_key = None
for key in range(256):
    # 检查文件前 8 字节 XOR key 后是否等于 dex 魔数
    head = bytes(b ^ key for b in data[:8])
    if head == dex_magic or head.startswith(b"dex\n"):
        found_key = key
        result["searches"]["xor_key"] = key
        print(f"发现单字节 XOR key: 0x{key:02x}")
        break

# 4) 文件前 256 字节 hex 供人工分析
result["head_hex"] = data[:256].hex(" ")
with open(os.path.join(OUT_DIR, "enc_dex_analysis.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\n分析已保存 -> output/enc_dex_analysis.json")
